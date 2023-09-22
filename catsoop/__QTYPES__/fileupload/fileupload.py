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

import os
import html
import json
import base64
import mimetypes
from urllib.parse import urlencode

tutor.qtype_inherit("smallbox")
base, _ = tutor.question("smallbox")

always_rerender = True

defaults.update(
    {
        "csq_soln_filename": "solution.txt",
        "csq_allow_save": False,
        "csq_soln_type": "string",
    }
)


def handle_submission(submissions, **info):
    o = {"score": 0.0, "msg": "", "rerender": True}
    name = info["csq_name"]
    ll = submissions.get(name, None)
    if ll is not None:
        if "data" not in ll:
            ll["data"] = info["csm_cslog"].retrieve_upload(ll["id"])[1]
        o.update(base["handle_submission"](submissions, **info))
    return o


def render_html(last_log, **info):
    name = info["csq_name"]
    aria_label = info.get("csq_aria_label", f'catsoop_prompt_{info["csq_name"]}')
    out = (
        """<input type="file" style="display: none" id=%s name="%s" aria-labelledby="%s"/>"""
        % (
            name,
            name,
            aria_label,
        )
    )
    out += (
        """<button class="btn btn-catsoop" id="%s_select_button">Select File</button>&nbsp;"""
        """<tt><span id="%s_selected_file">No file selected</span></tt>"""
    ) % (name, name)
    out += (
        """<script type="text/javascript">"""
        "\n// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3"
        """\ndocument.getElementById('%(name)s_select_button').addEventListener('click', function (){"""
        """\n    document.getElementById("%(name)s").click();"""
        """\n});"""
        """\ndocument.getElementById('%(name)s').onchange = function (){"""
        """\n    document.getElementById('%(name)s_selected_file').innerText = document.getElementById('%(name)s').value;"""
        """\n};"""
        """\ndnd_%(name)s = document.getElementById('cs_qdiv_%(name)s');"""
        """\ndnd_%(name)s.ondragover = dnd_%(name)s.ondragenter = function(e){e.preventDefault();};"""
        """\ndnd_%(name)s.ondrop = function(e){"""
        """\n    document.getElementById("%(name)s").files = e.dataTransfer.files;"""
        """\n    document.getElementById('%(name)s').onchange();"""
        """\n    e.preventDefault();"""
        """\n};"""
        "\n// @license-end"
        """</script>"""
    ) % {"name": name}
    ll = last_log.get(name, None)
    if ll is not None:
        link = None
        try:
            if "id" in ll:
                qstring = urlencode({"id": ll["id"]})
                link = "%s/_util/get_upload?%s" % (info["cs_url_root"], qstring)
            else:
                mtype = (
                    mimetypes.guess_type(ll["name"])[0] or "application/octet-stream"
                )
                link = "data:%s;base64,%s" % (
                    mtype,
                    base64.b64encode(ll["data"]).decode("utf-8"),
                )
        except:
            pass
        if link is not None:
            out += "<br/>"
            out += (
                '<a href="%s" '
                'download="%s">Download Most '
                "Recent Submission</a><br/>"
            ) % (
                link,
                html.escape(ll["name"]),
            )
    return out


def answer_display(**info):
    name = info["csq_soln_filename"]
    if info["csq_soln_type"] == "string":
        data = csm_thirdparty.data_uri.DataURI.make(
            info.get("cs_content_type", "text/plain"), None, True, info["csq_soln"]
        )
    elif info["csq_soln_type"] == "markdown":
        return "<b>Solution:</b><br/>&nbsp;<br/>%s" % info["csm_language"]._md(
            info["csq_soln"]
        )
    else:
        data = csm_thirdparty.data_uri.DataURI.from_file(info["csq_soln"])
        ext = mimetypes.guess_extension(data.mimetype) or ".txt"
        name = name.rsplit(".", 1)[0] + ext
    return ('<a href="%s" ' 'download="%s">Download Solution</a>') % (data, name)
