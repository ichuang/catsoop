# This file is part of CAT-SOOP
# Copyright (c) 2011-2025 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

import hmac
import time
import base64
import hashlib

import urllib.parse


error = None

# check that we received all the right stuff
stored_nonce = cs_session_data.get("_sso_nonce", None)
stored_expire = cs_session_data.get("_sso_expire", None)
sent_payload = cs_form.get("sso", None)
sent_sig = cs_form.get("sig", None)
if stored_nonce is None:
    error = "No nonce stored in session data"
elif stored_expire is None:
    error = "No SSO expiration time specified in session data"
elif sent_payload is None:
    error = "No payload received"
elif sent_sig is None:
    error = "No signature received"


# verify payload signature
if error is None:
    computed_sig = hmac.new(
        cs_sso_shared_secret, sent_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if sent_sig != computed_sig:
        error = "Invalid signature received"


# pull data out of payload
if error is None:
    try:
        data = urllib.parse.parse_qs(
            base64.urlsafe_b64decode(sent_payload).decode("utf-8")
        )
    except:
        error = "Unable to decode received payload"


# verify nonce and expiry time
if error is None:
    nonce = data.get("nonce", None)
    if nonce[0].encode("utf-8") != stored_nonce:
        error = "Invalid nonce received %s %s" % (nonce[0], stored_nonce)
    elif time.time() > stored_expire:
        error = "Nonce has expired, please try logging in again"


# make sure that a username was specified (this is the only mandatory field)
if error is None:
    uname = data.get("username", [])
    email = data.get("email", [])
    if not uname:
        error = "No username specified in SSO data"
    elif not email:
        error = "No e-mail address specified in SSO data"


# if we're here, we should be happily logged in; let's record that, and
# redirect
path = cs_session_data.get("_sso_path", [])
redirect_location = "/".join([csm_base_context.cs_url_root, *path])
if cs_session_data.get("cs_query_string", ""):
    redirect_location += "?" + cs_session_data["cs_query_string"]

if error is None:
    sso_data = {
        "username": uname[0],
        "email": email[0],
    }
    fullname = data.get("name", [])
    if fullname:
        sso_data["name"] = fullname[0]

    cs_session_data.update(sso_data)

    for key in ("_sso_path", "_sso_nonce", "_sso_expire"):
        del cs_session_data[key]

    csm_session.set_session_data(globals(), cs_sid, cs_session_data)

    cs_handler = "redirect"
else:
    cs_handler = "passthrough"
    cs_content_header = "Could Not Log You In"
    cs_content = (
        'You could not be logged in to the system because of the following error:<br/><font color="red">%s</font><p>Click <a href="%s?loginaction=login">here</a> to try again.'
        % (error, redirect_location)
    )
    cs_footer = cs_footer.replace(cs_base_logo_text, csm_errors.error_500_logo)
