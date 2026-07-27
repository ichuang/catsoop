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
"""Validate a CAS callback and finish the CAT-SOOP login."""

import html
import logging


LOGGER = logging.getLogger("cs")


# Reload the course context saved before redirecting to CAS. Authentication
# settings may be defined by the course rather than in global config.py.
ctx = {}
load_error = csm_loader.load_global_data(ctx)
saved_path = list(cs_session_data.get("_cas_path", []))
saved_course = cs_session_data.get("_cas_course")
if load_error is None and saved_course is not None:
    if not saved_path or saved_path[0] != saved_course:
        saved_path.insert(0, saved_course)
    ctx["cs_course"] = saved_course
    ctx["cs_path_info"] = saved_path
    content_file = csm_dispatch.content_file_location(ctx, saved_path)
    csm_loader.do_preload(
        ctx,
        saved_course,
        saved_path[1:],
        ctx,
        content_file,
    )

try:
    if load_error is not None:
        raise RuntimeError(load_error)
    cas_auth = csm_auth.get_auth_type_by_name(ctx, "cas")
    result = cas_auth["complete_login"](ctx, cs_session_data, cs_form)
except Exception:
    LOGGER.exception("Unexpected error while completing a CAS login")
    for key in ("_cas_state", "_cas_course", "_cas_path", "cs_query_string"):
        cs_session_data.pop(key, None)
    result = {
        "error": "An unexpected error occurred while completing the CAS login.",
        "redirect": csm_base_context.cs_url_root,
        "user": None,
    }

csm_session.set_session_data(globals(), cs_sid, cs_session_data)

if result["error"] is None:
    user = result["user"]
    csm_cslog.overwrite_log("_extra_info", [], user["username"], user)
    redirect_location = result["redirect"]
    cs_handler = "redirect"
else:
    retry_separator = "&" if "?" in result["redirect"] else "?"
    retry_url = "%s%sloginaction=login" % (
        result["redirect"],
        retry_separator,
    )
    cs_handler = "passthrough"
    cs_content_header = "Could Not Log You In"
    cs_content = (
        "<p>CAT-SOOP could not complete the CAS login:</p>"
        '<p><font color="red">%s</font></p>'
        '<p><a href="%s">Try logging in again</a>.</p>'
        % (
            html.escape(result["error"]),
            html.escape(retry_url, quote=True),
        )
    )
    cs_footer = cs_footer.replace(cs_base_logo_text, csm_errors.error_500_logo)
