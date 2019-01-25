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

defaults = {"csq_npoints": 1}

allow_viewanswer = False
allow_self_submit = False
allow_save = False


def total_points(**info):
    return info["csq_npoints"]


def handle_submission(submissions, **info):
    tok, un = submissions[info["csq_name"]].split(",")
    i = csm_api.userinfo_from_token(info, tok)
    new = dict(info)
    uinfo = info["csm_auth"]._get_user_information(
        new, new, info["cs_course"], (i or {}).get("username", "None"), True
    )
    if "impersonate" not in uinfo.get("permissions", []):
        percent = 0
        msg = "You must receive this checkoff from a staff member."
        l = False
    else:
        new = dict(info)
        new["cs_form"] = {}
        uinfo = info["csm_auth"]._get_user_information(
            new, new, info["cs_course"], un, True
        )
        if "checkoff" not in uinfo.get("permissions", []):
            percent = 0
            msg = "%s is not allowed to give checkoffs." % un
            l = False
        else:
            percent = 1
            now = info["csm_time"].from_detailed_timestamp(info["cs_timestamp"])
            now = info["csm_time"].long_timestamp(now).replace("; ", " at ")
            msg = "You received this checkoff from %s on %s." % (un, now)
            l = True
    return {"score": percent, "msg": msg, "lock": l}


def render_html(last_log, **info):
    if info["csq_description"] == info["csq_display_name"] == "":
        return ""
    info["csq_description"] = info["csm_language"].html_from_source(
        info, info["csq_description"]
    )
    return "<b>%s</b>:<br/>%s" % (info["csq_display_name"], info["csq_description"])


def answer_display(**info):
    return ""
