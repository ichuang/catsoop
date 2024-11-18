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
Store ticket, validate ticket, and then return user info if all ok
"""

import ssl
import time
import urllib.parse
import urllib.request

from lxml import etree
from catsoop import debug_log

LOGGER = debug_log.LOGGER
errors = []


def validate_ticket(ticket):
    redir_url = "%s/_auth/cas/callback" % cs_url_root
    val_url = (
        cs_cas_server
        + "/serviceValidate"
        + "?service="
        + urllib.parse.quote(redir_url)
        + "&ticket="
        + urllib.parse.quote(ticket)
    )
    nretries = 10
    ret = None

    if 0:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('ALL:!aNULL:!eNULL')

    for k in range(nretries):
        try:
            if 0:
                ret = urllib.request.urlopen(val_url, context=ctx).read()
            else:
                ret = urllib.request.urlopen(val_url).read()
            if k > 0:
                LOGGER.error("[auth.cas.validate] Succeeded on try number k=%s" % k)
            break
        except Exception as err:
            errors.append("CAS server rejected token request on try number %s" % k)
            errors.append(str(err))
            LOGGER.error(
                "[auth.cas.validate] failed to send validation request to cas server val_url=%s"
                % val_url
            )
            LOGGER.error("[auth.cas.validate] FAILED ON TRY %s: err=%s" % (k, str(err)))
        time.sleep(0.1 * (k+1))

    if ret is None:
        LOGGER.error("[auth.cas.validate] GIVING UP after %s retries" % k)
        return None

    ret = ret.decode("utf8")
    LOGGER.debug("[auth.cas.validate] cas server returned %s" % ret)
    if "cas:serviceResponse" not in ret:
        return None
    try:
        xml = etree.fromstring(ret)
    except Exception as err:
        LOGGER.error(
            "[auth.cas.validate] Failed to parse XML response from CAS server, err=%s"
            % str(err)
        )
        xml = None
    if not xml:
        return None
    LOGGER.debug("xml=%s" % xml)
    cas_info = {}

    def fillin(xpath, field):
        elem = xml.find(xpath)
        if elem is not None:
            cas_info[field] = elem.text

    fillin(".//{http://www.yale.edu/tp/cas}user", "username")
    fillin(".//{http://www.yale.edu/tp/cas}email", "email")
    fillin(".//{http://www.yale.edu/tp/cas}mail", "email")
    fillin(".//{http://www.yale.edu/tp/cas}givenName", "firstname")
    fillin(".//{http://www.yale.edu/tp/cas}sn", "lastname")
    if not ('username' in cas_info):
        if 'email' in cas_info:
            cas_info['username'] = cas_info['email'].split("@")[0]
            LOGGER.debug("[auth.cas] missing user in XML, using %s from email %s" % (cas_info['username'],
                                                                                     cas_info['email']))
        else:
            LOGGER.error("[auth_cas] missing user in XML!  cas_info=%s" % str(cas_info))

    cas_info["cas_ticket"] = ticket
    if cas_info.get("firstname"):
        cas_info["name"] = " ".join([cas_info[x] for x in ["firstname", "lastname"]])

    return cas_info


ticket = cs_form.get("ticket", None)
cas_info = validate_ticket(ticket)
if cas_info:
    LOGGER.info("[auth.cas.validate] cas server validated cas_info=%s" % cas_info)
    cs_session_data.update(cas_info)
else:
    LOGGER.info("[auth.cas.validate] cas server did not validate ticket")

path = [csm_base_context.cs_url_root] + cs_session_data.get("_cas_path", ["/"])
redirect_location = "/".join(path)

if cs_session_data.get("cs_query_string", ""):
    redirect_location += "?" + cs_session_data["cs_query_string"]

if not cas_info:
    cs_handler = "passthrough"
    cs_content_header = "Could Not Log You In"
    cs_content = (
        'You could not be logged in to the system because of the following error:<br/><font color="red">%s</font><p>Click <a href="%s?loginaction=login">here</a> to try again.'
        % ("\n".join(errors), redirect_location)
    )
    cs_footer = cs_footer.replace(cs_base_logo_text, csm_errors.error_500_logo)

# we made it! set session data and redirect to original page

csm_session.set_session_data(globals(), cs_sid, cs_session_data)
csm_cslog.overwrite_log("_extra_info", [], cs_session_data["username"], cas_info)
LOGGER.info("[auth.cas.validate] redirecting to %s" % redirect_location)
cs_handler = "redirect"
