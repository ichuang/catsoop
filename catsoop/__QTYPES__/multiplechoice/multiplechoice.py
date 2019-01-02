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
import collections.abc


def default_checkbox_checker(submission, solution):
    credit_per_correct = 1 / sum(solution)
    correct = (
        sum(i == j == True for i, j in zip(submission, solution)) * credit_per_correct
    )
    incorrect = (
        sum(i == True and j == False for i, j in zip(submission, solution))
        * credit_per_correct
    )
    return max(0, correct - incorrect)


defaults = {
    "csq_soln": "--",
    "csq_npoints": 1,
    "csq_check_function": lambda x, y: (x == y) * 1.0,
    "csq_checkbox_check_function": default_checkbox_checker,
    "csq_msg_function": lambda sub: "",
    "csq_options": [],
    "csq_show_check": False,
    "csq_renderer": "dropdown",
    "csq_soln_mode": "value",
}


def total_points(**info):
    return info["csq_npoints"]


def handle_submission(submissions, **info):
    check = info["csq_check_function"]
    soln = info["csq_soln"]
    sub = submissions[info["csq_name"]]
    if info.get("csq_multiplechoice_renderer", info["csq_renderer"]) == "checkbox":
        try:
            sub = json.loads(sub)
        except:
            sub = {}
        _sub = []
        for ix in range(len(info["csq_options"])):
            n = "%s_opt%d" % (info["csq_name"], ix)
            _sub.append(sub.get(n, False))
        sub = _sub
        if check is defaults["csq_check_function"]:
            check = defaults["csq_checkbox_check_function"]
    else:
        sub = int(sub)
        if info.get("csq_multiplechoice_soln_mode", info["csq_soln_mode"]) == "value":
            sub = info["csq_options"][sub] if sub >= 0 else "--"
    check_result = check(sub, soln)
    if isinstance(check_result, collections.abc.Mapping):
        score = check_result["score"]
        msg = check_result["msg"]
    elif isinstance(check_result, collections.abc.Sequence):
        score, msg = check_result
    else:
        score = check_result
        mfunc = info["csq_msg_function"]
        try:
            msg = mfunc(sub, soln)
        except:
            try:
                msg = mfunc(sub)
            except:
                msg = ""
    percent = float(score)
    if info["csq_show_check"]:
        if percent == 1.0:
            response = '<img src="%s" />' % info["cs_check_image"]
        elif percent == 0.0:
            response = '<img src="%s" />' % info["cs_cross_image"]
        else:
            response = ""
    else:
        response = ""
    response += msg
    return {"score": percent, "msg": response}


def render_html(last_log, **info):
    r = info.get("csq_multiplechoice_renderer", info["csq_renderer"])
    if r in _renderers:
        return _renderers[r](last_log, **info)
    else:
        return (
            "<font color='red'>"
            "Invalid <tt>multiplechoice</tt> renderer: %s"
            "</font>"
        ) % r


def render_html_dropdown(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '\n<select id="%s" name="%s" >' % (info["csq_name"], info["csq_name"])
    for (ix, i) in enumerate(["--"] + info["csq_options"]):
        out += '\n<option value="%s" ' % (ix - 1)
        if last_log.get(info["csq_name"], "-1") == str(ix - 1):
            out += "selected "
        out += ">%s</option>" % i
    out += "</select>"
    return out


def render_html_checkbox(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '<table border="0">'
    name = info["csq_name"]
    last = last_log.get(info["csq_name"], None)
    if last is None:
        last = {}
    else:
        try:
            last = json.loads(last)
        except:
            last = {}
        if not isinstance(last, dict):
            try:
                last = {("%s_opt%d" % (name, last)): True}
            except:
                last = {}
    checked = set()
    for (ix, i) in enumerate(info["csq_options"]):
        out += '\n<tr><td align="center">'
        _n = "%s_opt%d" % (name, ix)
        if last.get(_n, False):
            _s = " checked"
            checked.add(_n)
        else:
            _s = ""
        out += '<input type="checkbox" name="%s" value="%s"%s />' % (_n, ix, _s)
        text = csm_language.source_transform_string(info, i)
        out += "</td><td>%s</td></tr>" % text
    out += "\n</table>"
    out += '<input type="hidden" name="%s" id="%s" value="%s">' % (
        name,
        name,
        last or "",
    )
    checked_str = ",".join(("%r: true" % i) for i in checked)
    out += (
        '\n<script type="text/javascript">'
        "\nvar %s_selected = {%s};"
        '\ndocument.getElementById("%s").value = JSON.stringify(%s_selected);'
        '\ndocument.querySelectorAll("input[type=checkbox][name^=%s_opt]").forEach(function(r){'
        '\n    r.addEventListener("click", function(){'
        '\n        %s_selected[this.getAttribute("name")] = this.checked;'
        '\n    document.getElementById("%s").value = JSON.stringify(%s_selected);'
        "\n    });"
        "\n});"
        "\n</script>"
    ) % ((info["csq_name"], checked_str) + (info["csq_name"],) * 6)
    return out


def render_html_radio(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '<table border="0">'
    name = info["csq_name"]
    last = last_log.get(info["csq_name"], None)
    for (ix, i) in enumerate(info["csq_options"]):
        out += '\n<tr><td align="center">'
        if last == str(ix):
            _s = " checked"
        else:
            _s = ""
        out += '<input type="radio" name="%s_opts" value="%s"%s />' % (name, ix, _s)
        text = csm_language.source_transform_string(info, i)
        out += "</td><td>%s</td></tr>" % text
    out += "\n</table>"
    out += '<input type="hidden" name="%s" id="%s" value="%s">' % (
        name,
        name,
        last or "",
    )
    out += (
        '\n<script type="text/javascript">'
        '\ndocument.querySelectorAll("input[type=radio][name=%s_opts]").forEach(function(r){'
        '\n    r.addEventListener("click", function(){'
        '\n        document.getElementById("%s").value = this.value;'
        "\n    });"
        "\n});"
        "\n</script>"
    ) % (info["csq_name"], info["csq_name"])
    return out


_renderers = {
    "dropdown": render_html_dropdown,
    "radio": render_html_radio,
    "checkbox": render_html_checkbox,
}


def answer_display(**info):
    if info.get("csq_multiplechoice_renderer", info["csq_renderer"]) == "checkbox":
        out = "Solution: <table>"
        for c, i in zip(info["csq_soln"], info["csq_options"]):
            out += '<tr style="height:30px;"></tr>'
            out += '<tr><td align="center">'
            _im = "check" if c else "cross"
            out += '<img src="BASE/images/%s.png" />' % _im
            out += "</td><td>"
            text = csm_language.source_transform_string(info, i)
            out += text
            out += "</td></tr>"
        out += "</table>"
    else:
        soln = info["csq_soln"]
        out = "Solution: %s" % (soln,)
    return out
