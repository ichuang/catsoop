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

tutor.qtype_inherit("bigbox")

_base_render_html = render_html
_base_handle_submit = handle_submission

defaults.update({"csq_soln": "", "csq_npoints": 1, "csq_show_check": False})


def markdownify(context, text):
    return context["csm_language"]._md(text)


def richtext_format(context, text, msg="Preview:"):
    out = "</br>%s<br/>" % msg
    out += (
        '<div style="background-color: #eeeeee;' 'padding:10px; border-radius:10px;">'
    )
    out += markdownify(context, text)
    out = out.replace("<script", "&lt;script")
    out = out.replace("</script", "&lt;script")
    out += (
        '<script type="text/javascript">'
        'catsoop.render_all_math(document.getElementById("cs_qdiv_%s"), true);'
        "</script>"
    ) % context["csq_name"]
    out += "</div>"
    return out


checktext = "Preview"


def handle_check(submission, **info):
    last = submission.get(info["csq_name"])
    return richtext_format(info, last)


def handle_submission(submissions, **info):
    o = _base_handle_submit(submissions, **info)
    o["msg"] = o.get("msg", "") + richtext_format(
        info, submissions[info["csq_name"]], msg="Submitted:"
    )
    return o


def render_html(last_log, **info):
    out = _base_render_html(last_log, **info)
    help_url = "/".join([info["cs_url_root"], "_qtype", "richtext", "formatting.html"])
    out += (
        """<a onClick="window.open('%s', '_blank', """
        """'');" """
        """style="cursor:pointer; cursor:hand;">"""
        """Formatting Help</a>"""
    ) % help_url
    return out


def answer_display(**info):
    out = "<b>Solution:</b><br/>&nbsp;<br/> %s" % (info["csq_soln"])
    return out
