# This file is part of CAT-SOOP
# Copyright (c) 2011-2026 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Unit tests for the CAS authentication backend."""

import importlib.util
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

import pytest


CAS_DIRECTORY = Path(__file__).resolve().parents[1] / "__AUTH__" / "cas"


def load_cas():
    spec = importlib.util.spec_from_file_location(
        "catsoop_test_auth_cas",
        CAS_DIRECTORY / "cas.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cas = load_cas()


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def read(self):
        return self.payload

    def close(self):
        self.closed = True


class RecordingOpener:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []
        self.response = None

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        self.response = FakeResponse(self.payload)
        return self.response


class FakeAuth:
    def get_auth_type_by_name(self, context, auth_type):
        assert auth_type == "login"
        return {"_get_base_url": lambda ctx: "https://catsoop.example.edu/course/page"}


def context(**updates):
    out = {
        "cs_auth_type": "cas",
        "cs_cas_server": "https://login.example.edu/cas/",
        "cs_cas_timeout": 3,
        "cs_url_root": "https://catsoop.example.edu",
        "cs_course": "course",
        "cs_path_info": ["course", "page"],
        "cs_session_data": {},
        "cs_form": {},
        "cs_view_without_auth": True,
        "csm_auth": FakeAuth(),
    }
    out.update(updates)
    return out


SUCCESS_XML = b"""\
<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
  <cas:authenticationSuccess>
    <cas:user>alice</cas:user>
    <cas:attributes>
      <cas:mail>alice@example.edu</cas:mail>
      <cas:givenName>Alice</cas:givenName>
      <cas:sn>Example</cas:sn>
    </cas:attributes>
  </cas:authenticationSuccess>
</cas:serviceResponse>
"""


def test_login_redirect_records_state_and_original_page():
    ctx = context(cs_form={"loginaction": "login"})

    result = cas.get_logged_in_user(ctx)

    session = ctx["cs_session_data"]
    assert session["_cas_course"] == "course"
    assert session["_cas_path"] == ["course", "page"]
    assert session["_cas_state"]

    login_url = urllib.parse.urlsplit(result["cs_redirect"])
    assert login_url.scheme == "https"
    assert login_url.netloc == "login.example.edu"
    assert login_url.path == "/cas/login"
    login_query = urllib.parse.parse_qs(login_url.query)
    service = urllib.parse.urlsplit(login_query["service"][0])
    assert service.path == "/_auth/cas/callback"
    assert urllib.parse.parse_qs(service.query) == {"state": [session["_cas_state"]]}


def test_logged_in_user_is_returned_without_network_access():
    ctx = context(
        cs_session_data={
            "username": "alice",
            "name": "Alice Example",
            "email": "alice@example.edu",
        }
    )

    assert cas.get_logged_in_user(ctx) == {
        "username": "alice",
        "name": "Alice Example",
        "email": "alice@example.edu",
    }


def test_logout_clears_local_session_and_redirects_to_cas():
    ctx = context(
        cs_form={"loginaction": "logout"},
        cs_session_data={"username": "alice"},
    )

    result = cas.get_logged_in_user(ctx)

    assert ctx["cs_session_data"] == {}
    logout_url = urllib.parse.urlsplit(result["cs_redirect"])
    assert logout_url.path == "/cas/logout"
    assert urllib.parse.parse_qs(logout_url.query) == {
        "service": ["https://catsoop.example.edu"]
    }


def test_logged_out_page_and_login_box_modes():
    required_context = context(cs_view_without_auth=False)
    result = cas.get_logged_in_user(required_context)
    assert result == {"cs_render_now": True}
    assert required_context["cs_handler"] == "passthrough"
    assert "Log In" in required_context["cs_content"]

    optional_context = context()
    assert cas.get_logged_in_user(optional_context) == {}
    loaded_context = dict(optional_context)
    loaded_context["cs_content"] = "COURSE CONTENT"
    optional_context["cs_post_load"](loaded_context)
    assert "Log In" in loaded_context["cs_content"]
    assert "COURSE CONTENT" in loaded_context["cs_content"]


def test_validate_ticket_sends_exact_service_and_parses_attributes():
    opener = RecordingOpener(SUCCESS_XML)
    ctx = context()

    user = cas.validate_ticket(ctx, "ST-1-secret", "state-value", opener=opener)

    assert user == {
        "username": "alice",
        "email": "alice@example.edu",
        "name": "Alice Example",
    }
    assert len(opener.calls) == 1
    request, timeout = opener.calls[0]
    assert timeout == 3
    assert request.headers["Accept"] == "application/xml, text/xml"
    validation_url = urllib.parse.urlsplit(request.full_url)
    assert validation_url.path == "/cas/serviceValidate"
    assert urllib.parse.parse_qs(validation_url.query) == {
        "service": ["https://catsoop.example.edu/_auth/cas/callback?state=state-value"],
        "ticket": ["ST-1-secret"],
    }
    assert opener.response.closed


def test_validate_ticket_accepts_display_name():
    response = b"""\
    <serviceResponse>
      <authenticationSuccess>
        <user>bob</user>
        <attributes><displayName>Bob Example</displayName></attributes>
      </authenticationSuccess>
    </serviceResponse>
    """
    assert cas.validate_ticket(
        context(),
        "ST-2",
        "state",
        opener=RecordingOpener(response),
    ) == {"username": "bob", "name": "Bob Example"}


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            b"""\
            <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
              <cas:authenticationFailure code="INVALID_TICKET">
                Ticket not recognized
              </cas:authenticationFailure>
            </cas:serviceResponse>
            """,
            "CAS rejected the login ticket.",
        ),
        (b"<not-xml", "The CAS server returned an invalid validation response."),
        (
            b"<serviceResponse></serviceResponse>",
            "The CAS server did not return an authentication result.",
        ),
        (
            b"""\
            <serviceResponse>
              <authenticationSuccess></authenticationSuccess>
            </serviceResponse>
            """,
            "The CAS response did not include a username.",
        ),
    ],
)
def test_validate_ticket_rejects_bad_responses(payload, expected):
    with pytest.raises(cas.CASAuthenticationError, match=expected):
        cas.validate_ticket(
            context(),
            "ST-sensitive-ticket",
            "state",
            opener=RecordingOpener(payload),
        )


def test_network_errors_are_bounded_and_do_not_disclose_details():
    opener = RecordingOpener(error=urllib.error.URLError("private network diagnostic"))

    with pytest.raises(cas.CASAuthenticationError) as caught:
        cas.validate_ticket(
            context(),
            "ST-sensitive-ticket",
            "state",
            opener=opener,
        )

    assert str(caught.value) == "CAT-SOOP could not contact the CAS server."
    assert "private network diagnostic" not in str(caught.value)
    assert opener.calls[0][1] == 3


@pytest.mark.parametrize(
    "updates,expected",
    [
        ({"cs_cas_server": None}, "The CAS server is not configured."),
        (
            {"cs_cas_server": "not a URL"},
            "The configured CAS server URL is invalid.",
        ),
        (
            {"cs_cas_server": "https://login.example.edu/cas?tenant=private"},
            "The configured CAS server URL is invalid.",
        ),
        (
            {"cs_cas_timeout": 0},
            "The configured CAS network timeout is invalid.",
        ),
    ],
)
def test_invalid_configuration_is_reported_cleanly(updates, expected):
    with pytest.raises(cas.CASConfigurationError, match=expected):
        cas.validate_ticket(
            context(**updates),
            "ST-1",
            "state",
            opener=RecordingOpener(SUCCESS_XML),
        )


def test_complete_login_updates_session_and_preserves_return_url():
    session = {
        "_cas_state": "expected-state",
        "_cas_course": "course",
        "_cas_path": ["course", "unit 1"],
        "cs_query_string": "section=2",
    }

    result = cas.complete_login(
        context(),
        session,
        {"state": "expected-state", "ticket": "ST-1"},
        opener=RecordingOpener(SUCCESS_XML),
    )

    assert result == {
        "error": None,
        "redirect": "https://catsoop.example.edu/course/unit%201?section=2",
        "user": {
            "username": "alice",
            "email": "alice@example.edu",
            "name": "Alice Example",
        },
    }
    assert session == {
        "username": "alice",
        "email": "alice@example.edu",
        "name": "Alice Example",
        "course": "course",
    }


def test_complete_login_rejects_mismatched_and_replayed_state_without_network():
    opener = RecordingOpener(SUCCESS_XML)
    session = {
        "_cas_state": "expected-state",
        "_cas_course": "course",
        "_cas_path": ["course"],
    }

    first = cas.complete_login(
        context(),
        session,
        {"state": "different-state", "ticket": "ST-1"},
        opener=opener,
    )
    second = cas.complete_login(
        context(),
        session,
        {"state": "expected-state", "ticket": "ST-1"},
        opener=opener,
    )

    assert first["error"] == "The CAS login state did not match."
    assert second["error"] == "No CAS login is pending in this session."
    assert opener.calls == []
    assert session == {}


class FakeLoader:
    def __init__(self, auth):
        self.auth = auth
        self.preload_calls = []

    def load_global_data(self, target):
        target.update(
            {
                "csm_base_context": object(),
                "csm_auth": self.auth,
                "cs_url_root": "https://catsoop.example.edu",
                "cs_cas_server": "https://login.example.edu/cas",
                "cs_cas_timeout": 3,
            }
        )
        return None

    def do_preload(self, context, course, path, target, content_file):
        self.preload_calls.append((course, path, content_file))


class FakeCallbackAuth:
    def get_auth_type_by_name(self, context, auth_type):
        assert auth_type == "cas"
        return vars(cas)


class FakeDispatch:
    def content_file_location(self, context, path):
        return "/courses/%s/content.catsoop" % "/".join(path)


class FakeSession:
    def __init__(self):
        self.saved = None

    def set_session_data(self, context, sid, session):
        self.saved = (sid, dict(session))


class FakeLog:
    def __init__(self):
        self.writes = []

    def overwrite_log(self, *args):
        self.writes.append(args)


class FakeErrors:
    error_500_logo = "ERROR LOGO"


class FakeBaseContext:
    cs_url_root = "https://catsoop.example.edu"


def callback_environment(form, session):
    auth = FakeCallbackAuth()
    loader = FakeLoader(auth)
    session_store = FakeSession()
    log = FakeLog()
    environment = {
        "csm_loader": loader,
        "csm_dispatch": FakeDispatch(),
        "csm_auth": auth,
        "csm_session": session_store,
        "csm_cslog": log,
        "csm_errors": FakeErrors(),
        "csm_base_context": FakeBaseContext(),
        "cs_session_data": session,
        "cs_form": form,
        "cs_sid": "session-id",
        "cs_footer": "FOOTER CAT-SOOP",
        "cs_base_logo_text": "CAT-SOOP",
    }
    return environment, loader, session_store, log


def run_callback(environment):
    filename = CAS_DIRECTORY / "callback" / "content.py"
    source = filename.read_text()
    exec(compile(source, str(filename), "exec"), environment)


def test_callback_page_reloads_course_and_redirects_after_success():
    session = {
        "_cas_state": "expected-state",
        "_cas_course": "course",
        "_cas_path": ["course", "unit"],
    }
    environment, loader, session_store, log = callback_environment(
        {"state": "expected-state", "ticket": "ST-1"},
        session,
    )

    with mock.patch.object(
        cas.urllib.request,
        "urlopen",
        RecordingOpener(SUCCESS_XML),
    ):
        run_callback(environment)

    assert loader.preload_calls == [
        ("course", ["unit"], "/courses/course/unit/content.catsoop")
    ]
    assert environment["cs_handler"] == "redirect"
    assert environment["redirect_location"] == (
        "https://catsoop.example.edu/course/unit"
    )
    assert session_store.saved == (
        "session-id",
        {
            "username": "alice",
            "email": "alice@example.edu",
            "name": "Alice Example",
            "course": "course",
        },
    )
    assert log.writes[0][2] == "alice"
    assert "ticket" not in log.writes[0][3]


def test_callback_page_renders_error_without_logging_user():
    environment, _, session_store, log = callback_environment(
        {"state": "wrong-state", "ticket": "ST-1"},
        {
            "_cas_state": "expected-state",
            "_cas_course": "course",
            "_cas_path": ["course"],
        },
    )

    run_callback(environment)

    assert environment["cs_handler"] == "passthrough"
    assert "CAS login state did not match" in environment["cs_content"]
    assert "Try logging in again" in environment["cs_content"]
    assert session_store.saved == ("session-id", {})
    assert log.writes == []
