# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
"""
Authenticate using CAS (https://en.wikipedia.org/wiki/Central_Authentication_Service)
"""

import urllib.parse
import urllib.request

from catsoop import debug_log

LOGGER = debug_log.LOGGER

# -----------------------------------------------------------------------------


def get_logged_in_user(context):
    """
    Authenticate using CAS
    """
    session = context["cs_session_data"]
    logintype = context["csm_auth"].get_auth_type_by_name(context, "login")
    _get_base_url = logintype["_get_base_url"]
    cas_url = context["cs_cas_server"]
    redir_url = "%s/_auth/cas/callback" % context["cs_url_root"]

    # if the session tells us someone is logged in, return their
    # information
    action = context["cs_form"].get("loginaction", None)
    LOGGER.info("[auth.cas] login action=%s" % action)

    if action == "logout":
        ticket = context["cs_session_data"].get("cas_ticket", "")
        logout_url = (
            cas_url
            + "/logout"
            + "?service="
            + urllib.parse.quote(redir_url)
            + "&ticket="
            + urllib.parse.quote(ticket)
        )
        try:
            if cs_cas_proxy:
                logout_url = (
                    cs_cas_proxy
                    + "?service="
                    + urllib.parse.quote(redir_url)
                    + "&ticket="
                    + urllib.parse.quote(ticket)
                    + "&action=logout"
                )
                LOGGER.error("[auth.cas.logout] using proxy %s" % cs_cas_proxy)
        except:
            pass
        try:
            ret = urllib.request.urlopen(logout_url).read()
            LOGGER.info("[auth.cas] CAS server logout returnd ret=%s" % ret)
        except Exception as err:
            LOGGER.error(
                "[auth.cas] CAS server rejected logout request, err=%s" % str(err)
            )

        context["cs_session_data"] = {}
        return {"cs_reload": True}

    elif "username" in session:
        uname = session["username"]
        return {
            "username": uname,
            "name": session.get("name", uname),
            "email": session.get("email", uname),
        }

    elif action is None:
        if context.get("cs_view_without_auth", True):
            old_postload = context.get("cs_post_load", None)

            def new_postload(context):
                if old_postload is not None:
                    old_postload(context)
                if "cs_login_box" in context:
                    lbox = context["cs_login_box"](context)

                else:

                    lbox = LOGIN_BOX % (
                        _get_base_url(context),
                        context["cs_cas_server"],
                    )
                if not type(context["cs_content"])==tuple:
                    context["cs_content"] = lbox + context["cs_content"]

            context["cs_post_load"] = new_postload
            return {}
        else:
            context["cs_handler"] = "passthrough"
            context["cs_content_header"] = "Please Log In"
            context["cs_content"] = LOGIN_PAGE % (_get_base_url(context), cas_url)
            return {"cs_render_now": True}

    elif action == "login":
        login_url = cas_url + "/login" + "?service=" + urllib.parse.quote(redir_url)
        LOGGER.info("no auth, reditecting to %s" % login_url)
        session["_cas_course"] = context["cs_course"]
        session["_cas_path"] = context["cs_path_info"]
        return {"cs_redirect": login_url}

    else:
        raise Exception("Unknown action: %r" % action)


LOGIN_PAGE = """
<div id="catsoop_login_box">
Access to this page requires logging in via CAS.  Please <a
href="%s?loginaction=login">Log In</a> to continue.<br/>Note that this link
will take you to an external site (<tt>%s</tt>) to authenticate, and then you
will be redirected back to this page.
</div>
"""

LOGIN_BOX = """
<div class="response" id="catsoop_login_box">
<b><center>You are not logged in.</center></b><br/>
If you are a current student, please <a href="%s?loginaction=login">Log
In</a> for full access to the web site.<br/>Note that this link will take you to
an external site (<tt>%s</tt>) to authenticate, and then you will be redirected
back to this page.
</div>
"""
