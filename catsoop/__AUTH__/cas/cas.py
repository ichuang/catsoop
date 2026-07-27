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
"""Authenticate users with the Central Authentication Service (CAS)."""

import html
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as etree


LOGGER = logging.getLogger("cs")


class CASError(Exception):
    """An expected CAS failure whose message is safe to show to a user."""


class CASConfigurationError(CASError):
    """The CAT-SOOP CAS configuration is incomplete or invalid."""


class CASAuthenticationError(CASError):
    """The CAS server did not authenticate the supplied ticket."""


def _setting(context, name, default=None):
    """Read a setting from a request context or its base-context module."""

    if name in context:
        return context[name]
    base_context = context.get("csm_base_context")
    return getattr(base_context, name, default)


def _cas_server(context):
    """Return the normalized, validated CAS server root."""

    server = _setting(context, "cs_cas_server")
    if not isinstance(server, str) or not server.strip():
        raise CASConfigurationError("The CAS server is not configured.")
    server = server.rstrip("/")
    parsed = urllib.parse.urlsplit(server)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise CASConfigurationError("The configured CAS server URL is invalid.")
    return server


def _url_root(context):
    """Return CAT-SOOP's normalized public URL root."""

    root = _setting(context, "cs_url_root")
    if not isinstance(root, str) or not root.strip():
        raise CASConfigurationError("CAT-SOOP's public URL root is not configured.")
    return root.rstrip("/")


def _endpoint_url(context, endpoint, parameters):
    """Build a CAS endpoint URL without interpolating query-string values."""

    query = urllib.parse.urlencode(parameters)
    return "%s/%s?%s" % (_cas_server(context), endpoint.lstrip("/"), query)


def service_url(context, state):
    """Return the callback URL registered as the CAS service for this login."""

    callback = "%s/_auth/cas/callback" % _url_root(context)
    return "%s?%s" % (callback, urllib.parse.urlencode({"state": state}))


def return_url(context, session):
    """Return the local page to visit after the CAS callback."""

    root = _url_root(context)
    path = session.get("_cas_path", [])
    if not path:
        course = session.get("_cas_course")
        path = [] if course is None else [course]
    encoded_path = "/".join(
        urllib.parse.quote(str(part), safe="") for part in path if str(part)
    )
    out = root if not encoded_path else "%s/%s" % (root, encoded_path)
    query = session.get("cs_query_string", "")
    if query:
        out = "%s?%s" % (out, query)
    return out


def _local_name(element):
    """Return an XML element name without its namespace."""

    return element.tag.rsplit("}", 1)[-1]


def _first_text(element, *names):
    """Return the first non-empty text from elements with any given name."""

    wanted = {name.casefold() for name in names}
    for child in element.iter():
        if _local_name(child).casefold() in wanted and child.text:
            value = child.text.strip()
            if value:
                return value
    return None


def _attributes(success):
    """Flatten the scalar attributes in a CAS authentication-success element."""

    out = {}
    for element in success.iter():
        if len(element) or not element.text:
            continue
        name = _local_name(element)
        if name in {"authenticationSuccess", "user"}:
            continue
        value = element.text.strip()
        if value:
            out.setdefault(name.casefold(), value)
    return out


def _attribute(attributes, *names):
    """Return the first non-empty value for a case-insensitive attribute name."""

    for name in names:
        value = attributes.get(name.casefold())
        if value:
            return value
    return None


def _parse_validation_response(payload):
    """Convert a CAS serviceValidate XML response to CAT-SOOP user data."""

    try:
        root = etree.fromstring(payload)
    except (etree.ParseError, ValueError):
        raise CASAuthenticationError(
            "The CAS server returned an invalid validation response."
        ) from None

    failure = next(
        (
            element
            for element in root.iter()
            if _local_name(element) == "authenticationFailure"
        ),
        None,
    )
    if failure is not None:
        code = failure.attrib.get("code", "unknown")
        LOGGER.warning("CAS rejected a login ticket (code=%r)", code)
        raise CASAuthenticationError("CAS rejected the login ticket.")

    success = next(
        (
            element
            for element in root.iter()
            if _local_name(element) == "authenticationSuccess"
        ),
        None,
    )
    if success is None:
        raise CASAuthenticationError(
            "The CAS server did not return an authentication result."
        )

    attributes = _attributes(success)
    username = _first_text(success, "user") or _attribute(attributes, "username", "uid")
    if not username:
        raise CASAuthenticationError("The CAS response did not include a username.")

    email = _attribute(attributes, "email", "mail")
    name = _attribute(attributes, "displayName", "cn", "name")
    if not name:
        first_name = _attribute(attributes, "givenName", "firstname")
        last_name = _attribute(attributes, "sn", "surname", "lastname")
        name = " ".join(part for part in (first_name, last_name) if part)

    user = {"username": username}
    if email:
        user["email"] = email
    if name:
        user["name"] = name
    return user


def validate_ticket(context, ticket, state, opener=None):
    """Validate one CAS service ticket and return normalized user information."""

    if not isinstance(ticket, str) or not ticket:
        raise CASAuthenticationError("No CAS login ticket was provided.")
    if not isinstance(state, str) or not state:
        raise CASAuthenticationError("The CAS login state is missing.")

    timeout = _setting(context, "cs_cas_timeout", 10)
    try:
        timeout = float(timeout)
        if timeout <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise CASConfigurationError(
            "The configured CAS network timeout is invalid."
        ) from None

    url = _endpoint_url(
        context,
        "serviceValidate",
        {"service": service_url(context, state), "ticket": ticket},
    )
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/xml, text/xml"},
    )
    opener = opener or urllib.request.urlopen
    response = None
    try:
        response = opener(request, timeout=timeout)
        payload = response.read()
    except (OSError, TimeoutError, urllib.error.URLError):
        LOGGER.warning("Unable to contact the CAS server while validating a ticket")
        raise CASAuthenticationError(
            "CAT-SOOP could not contact the CAS server."
        ) from None
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()

    return _parse_validation_response(payload)


def _clear_login_state(session):
    """Remove the one-use CAS login state from a session."""

    for key in ("_cas_state", "_cas_course", "_cas_path", "cs_query_string"):
        session.pop(key, None)


def complete_login(context, session, form, opener=None):
    """Validate a callback, update its session, and describe the next response."""

    redirect = return_url(context, session)
    expected_state = session.get("_cas_state")
    received_state = form.get("state")
    ticket = form.get("ticket")
    course = session.get("_cas_course")

    try:
        if not isinstance(expected_state, str) or not expected_state:
            raise CASAuthenticationError("No CAS login is pending in this session.")
        if not isinstance(received_state, str) or not received_state:
            raise CASAuthenticationError("The CAS login state is missing.")
        if not secrets.compare_digest(expected_state, received_state):
            raise CASAuthenticationError("The CAS login state did not match.")
        user = validate_ticket(context, ticket, expected_state, opener=opener)
    except CASError as error:
        _clear_login_state(session)
        return {"error": str(error), "redirect": redirect, "user": None}

    _clear_login_state(session)
    session.update(user)
    if course is not None:
        session["course"] = course
    return {"error": None, "redirect": redirect, "user": user}


def get_logged_in_user(context):
    """Return the current CAS user or initiate a CAS login/logout."""

    session = context["cs_session_data"]
    action = context["cs_form"].get("loginaction")
    login_auth = context["csm_auth"].get_auth_type_by_name(context, "login")
    get_base_url = login_auth["_get_base_url"]

    if action == "logout":
        context["cs_session_data"] = {}
        destination = _setting(context, "cs_cas_logout_redirect") or _url_root(context)
        return {
            "cs_redirect": _endpoint_url(
                context,
                "logout",
                {"service": destination},
            )
        }

    if "username" in session:
        username = session["username"]
        return {
            "username": username,
            "name": session.get("name", username),
            "email": session.get("email", username),
        }

    if action is None:
        server = html.escape(_cas_server(context))
        if context.get("cs_view_without_auth", True):
            old_post_load = context.get("cs_post_load")

            def new_post_load(loaded_context):
                if old_post_load is not None:
                    old_post_load(loaded_context)
                if "cs_login_box" in loaded_context:
                    login_box = loaded_context["cs_login_box"](loaded_context)
                else:
                    login_box = LOGIN_BOX % (
                        html.escape(get_base_url(loaded_context), quote=True),
                        server,
                    )
                content = loaded_context.get("cs_content", "")
                if not isinstance(content, tuple):
                    loaded_context["cs_content"] = "%s\n\n%s" % (login_box, content)

            context["cs_post_load"] = new_post_load
            return {}

        context["cs_handler"] = "passthrough"
        context["cs_content_header"] = "Please Log In"
        context["cs_content"] = LOGIN_PAGE % (
            html.escape(get_base_url(context), quote=True),
            server,
        )
        return {"cs_render_now": True}

    if action == "login":
        state = secrets.token_urlsafe(32)
        session["_cas_state"] = state
        session["_cas_course"] = context.get("cs_course")
        session["_cas_path"] = list(context.get("cs_path_info", []))
        return {
            "cs_redirect": _endpoint_url(
                context,
                "login",
                {"service": service_url(context, state)},
            )
        }

    raise ValueError("Unknown CAS login action: %r" % action)


LOGIN_PAGE = """
<div id="catsoop_login_box">
Access to this page requires logging in via CAS. Please
<a href="%s?loginaction=login">Log In</a> to continue.<br/>
This link will take you to the external CAS server (<tt>%s</tt>) and return
you to this page after authentication.
</div>
"""


LOGIN_BOX = """
<div class="response" id="catsoop_login_box">
<b><center>You are not logged in.</center></b><br/>
Please <a href="%s?loginaction=login">Log In</a> for full access.<br/>
This link will take you to the external CAS server (<tt>%s</tt>) and return
you to this page after authentication.
</div>
"""
