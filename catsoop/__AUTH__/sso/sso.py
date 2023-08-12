# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

# This file implements a single-sign-on solution inspired by Discourse's SSO
# model: https://meta.discourse.org/t/official-single-sign-on-for-discourse-sso/13045

import os
import hmac
import time
import base64
import hashlib

import urllib.parse


def get_logged_in_user(context):
    logintype = context["csm_auth"].get_auth_type_by_name(context, "login")
    session = context["cs_session_data"]
    _get_base_url = logintype["_get_base_url"]

    action = context["cs_form"].get("loginaction", None)
    if action == "logout":
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
        # not logged in, no attempted action.  show login info
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
                        context["cs_sso_location"],
                    )
                context["cs_content"] = "%s\n\n%s" % (lbox, context["cs_content"])

            context["cs_post_load"] = new_postload
            return {}
        else:
            context["cs_handler"] = "passthrough"
            context["cs_content_header"] = "Please Log In"
            context["cs_content"] = LOGIN_PAGE % (
                _get_base_url(context),
                context["cs_sso_location"],
            )
            return {"cs_render_now": True}
    elif action == "login":
        # here we go, time to actually log in
        # we'll generate the relevant info here, and send the request off to
        # the proper endpoint.  that page should redirect back to the callback
        # page, which will take that information and log the user in, before
        # redirecting them back to whatever page they came from
        nonce = base64.urlsafe_b64encode(os.urandom(64))

        # also, store some relevant stuff in the session so that we can recover
        # some information when we get back here
        session["_sso_path"] = context["cs_path_info"]
        session["_sso_nonce"] = nonce
        session["_sso_expire"] = (
            getattr(context["csm_base_context"], "cs_sso_timeout", 600) + time.time()
        )

        data = {
            "nonce": nonce,
            "return_sso_url": "%s/_auth/sso/callback" % context["cs_url_root"],
        }
        payload = base64.urlsafe_b64encode(urllib.parse.urlencode(data).encode("utf-8"))
        sig = hmac.new(
            context["csm_base_context"].cs_sso_shared_secret, payload, hashlib.sha256
        ).hexdigest()
        redirect_location = "%s?%s" % (
            context["csm_base_context"].cs_sso_location,
            urllib.parse.urlencode({"sso": payload.decode("utf-8"), "sig": sig}),
        )
        return {"cs_redirect": redirect_location}
    else:
        raise Exception("Unknown action: %r" % action)


LOGIN_PAGE = """
<div id="catsoop_login_box">
Access to this page requires logging in.  Please <a
href="%s?loginaction=login">Log In</a> to continue.<br/>Note that this link
will take you to an external site (<tt>%s</tt>) to authenticate, and then you
will be redirected back to this page.
</div>
"""

LOGIN_BOX = """
<div class="response" id="catsoop_login_box">
<b><center>You are not logged in.</center></b><br/>
Please <a href="%s?loginaction=login">log
in</a> for full access to the web site.<br/>Note that this link will take you to
an external site (<tt>%s</tt>) to authenticate, and then you will be redirected
back to this page.
</div>
"""
