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

import json
import base64
import urllib.request, urllib.parse, urllib.error

import jose.jwk
import jose.utils

stored_state = cs_session_data.get("_openid_state", None)
state = cs_form.get("state", None)
stored_nonce = cs_session_data.get("_openid_nonce", None)

error = None
if stored_state is None:
    error = "No state stored in session."
elif state is None:
    error = "No state provided by server."
elif stored_state != state:
    error = "Suspected tampering! " "State from server does not match local state."


if error is None:
    # we should have course information in the session data, so we can see if
    # we need to do a preload.
    ctx = {}
    csm_loader.load_global_data(ctx)

    session = cs_session_data

    if "_openid_course" in session:
        ctx["cs_course"] = cs_session_data["_openid_course"]
        ctx["cs_path_info"] = [ctx["cs_course"]]
        cfile = csm_dispatch.content_file_location(ctx, [ctx["cs_course"]])
        csm_loader.do_early_load(ctx, ctx["cs_course"], [], ctx, cfile)

    # if we're here, we know we got back something reasonable.
    # now, need to send POST request

    id = ctx.get("cs_openid_client_id", "")
    secret = ctx.get("cs_openid_client_secret", "")

    redir_url = "%s/_auth/openid_connect/callback" % ctx["cs_url_root"]
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": cs_form["code"],
            "redirect_uri": redir_url,
            "client_id": id,
            "client_secret": secret,
        }
    ).encode()
    request = urllib.request.Request("%s/token" % ctx["cs_openid_server"], data)
    try:
        resp = urllib.request.urlopen(request, data).read()
    except:
        error = "Server rejected Token request."

    if error is None:
        try:
            resp = json.loads(resp.decode())
        except:
            error = "Token request response was not valid JSON."

    if error is None:
        # make sure we have been given authorization to access the proper
        # information
        desired_scope = ctx.get("cs_openid_scope", "openid profile email")
        desired_scope = desired_scope.split()
        scope_error = (
            "You must provide CAT-SOOP access " "to the following scopes: %r"
        ) % desired_scope
        if "id_token" not in resp or any(
            i not in resp.get("scope", "").split() for i in desired_scope
        ):
            error = scope_error

    if error is None:
        # verify JWT signature
        id_token, sig = resp["id_token"].rsplit(".", 1)

        if error is None:
            # get JWK from the web
            url = "%s/jwk" % ctx.get("cs_openid_server", "")
            try:
                key = json.loads(urllib.request.urlopen(url).read().decode())["keys"][0]
            except:
                error = "Server rejected request for JWK"
            if "alg" not in key:
                key["alg"] = ctx.get("cs_openid_default_algorithm", "RS256")
            key = jose.jwk.construct(key)
            decoded_sig = jose.utils.base64url_decode(sig.encode())
            if not key.verify(id_token.encode(), decoded_sig):
                error = "Invalid signature on JWS."

    if error is None:
        # check information from ID Token
        def _b64_pad(s, char="="):
            missing = len(s) % 4
            if not missing:
                return s
            return s + char * (4 - missing)

        header, body = id_token.split(".")
        header = _b64_pad(header)
        body = _b64_pad(body)
        try:
            header = json.loads(base64.b64decode(header).decode())
            body = json.loads(base64.b64decode(body).decode())
        except:
            error = "Malformed header and/or body of ID token"

        if error is None:
            now = time.time.time()
            if body["iss"].rstrip("/") != ctx.get("cs_openid_server", None):
                error = "Invalid ID Token issuer."
            elif body["nonce"] != stored_nonce:
                error = (
                    "Suspected tampering!"
                    "Nonce from server does not match local nonce."
                )
            elif body["iat"] > now + 60:
                error = "ID Token is from the future. %r" % ((body["iat"], now),)
            elif now > body["exp"] + 60:
                error = "ID Token has expired."
            elif ctx.get("cs_openid_client_id", None) not in body["aud"]:
                error = "ID Token is not intended for CAT-SOOP."

if error is None:
    # get user information from server
    access_tok = resp["access_token"]
    redir = "%s/userinfo" % ctx.get("cs_openid_server", "")
    headers = {"Authorization": "Bearer %s" % access_tok}
    request2 = urllib.request.Request(redir, headers=headers)
    try:
        resp = json.loads(urllib.request.urlopen(request2).read().decode())
    except:
        error = "Server rejected request for User Information"

if error is None:
    # try to set usert information in session
    def get_username(idtoken, userinfo):
        return userinfo["preferred_username"]

    def get_email(idtoken, userinfo):
        return userinfo["email"]

    try:
        get_username = ctx.get("cs_openid_username_generator", get_username)
        get_email = ctx.get("cs_openid_email_generator", get_email)
        openid_info = {
            "username": get_username(body, resp),
            "email": get_email(body, resp),
            "name": resp["name"],
        }
        session.update(openid_info)
        session["course"] = cs_session_data["_openid_course"]
    except:
        error = "Error setting user information."

path = [csm_base_context.cs_url_root] + cs_session_data.get("_openid_path", ["/"])
redirect_location = "/".join(path)
if cs_session_data.get("cs_query_string", ""):
    redirect_location += "?" + cs_session_data["cs_query_string"]
if error is None:
    # we made it! set session data and redirect to original page
    csm_session.set_session_data(globals(), cs_sid, session)
    csm_cslog.overwrite_log("_extra_info", [], session["username"], openid_info)
    cs_handler = "redirect"
else:
    cs_handler = "passthrough"
    cs_content_header = "Could Not Log You In"
    cs_content = (
        'You could not be logged in to the system because of the following error:<br/><font color="red">%s</font><p>Click <a href="%s?loginaction=login">here</a> to try again.'
        % (error, redirect_location)
    )
    cs_footer = cs_footer.replace(cs_base_logo_text, csm_errors.error_500_logo)
