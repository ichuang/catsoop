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

import json
import collections.abc


def default_checkbox_checker(submission, solution):
    if sum(solution) < len(solution) / 2:
        solution = [not i for i in solution]
        submission = [not i for i in submission]
    credit_per_correct = 1 / sum(solution)
    correct = (
        sum(i == j == True for i, j in zip(submission, solution)) * credit_per_correct
    )
    incorrect = (
        sum(i == True and j == False for i, j in zip(submission, solution))
        * credit_per_correct
    )
    return max(0, correct - incorrect)


question_info_fields = [
    "csq_options",
    "csq_renderer",
]

default_regular_checker = lambda x, y: (x == y) * 1.0

defaults = {
    "csq_soln": "--",
    "csq_npoints": 1,
    "csq_check_function": default_regular_checker,
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
    sub = submissions[info["csq_name"]]["data"]
    if info["csq_renderer"] == "checkbox":
        try:
            sub = json.loads(sub)
        except:
            sub = {}
        _sub = []
        for ix in range(len(info["csq_options"])):
            n = "%s_opt%d" % (info["csq_name"], ix)
            _sub.append(sub.get(n, False))
        sub = _sub
        if check is default_regular_checker:
            check = defaults["csq_checkbox_check_function"]
    else:
        if len(sub) == 0:
            sub = -1
        else:
            sub = int(sub)
        if info["csq_soln_mode"] == "value":
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
            response = '<img src="%s" alt="Correct" />' % info["cs_check_image"]
        elif percent == 0.0:
            response = '<img src="%s" alt="Incorrect" />' % info["cs_cross_image"]
        else:
            response = ""
    else:
        response = ""
    response += msg
    return {"score": percent, "msg": response}


def render_html(last_log, **info):
    r = info["csq_renderer"]
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
    ll = last_log.get(info["csq_name"], {"data": "-1"})["data"]
    aria_label = info.get("csq_aria_label", f'catsoop_prompt_{info["csq_name"]}')
    out = '\n<select id="%s" name="%s" aria-labelledby="%s">' % (
        info["csq_name"],
        info["csq_name"],
        aria_label,
    )
    for ix, i in enumerate(["--"] + info["csq_options"]):
        out += '\n<option value="%s" ' % (ix - 1)
        if ll == str(ix - 1):
            out += "selected "
        out += ">%s</option>" % i
    out += "</select>"
    return out


def render_html_checkbox(last_log, **info):
    if last_log is None:
        last_log = {}
    aria_label = info.get("csq_aria_label", f'catsoop_prompt_{info["csq_name"]}')
    out = "<fieldset aria-labelledby='%s'>" % aria_label
    name = info["csq_name"]
    last = last_log.get(info["csq_name"], None)
    if last is None:
        last = {}
    else:
        try:
            last = json.loads(last["data"])
        except:
            last = {}
        if not isinstance(last, dict):
            try:
                last = {("%s_opt%d" % (name, last)): True}
            except:
                last = {}
    checked = set()
    for ix, i in enumerate(info["csq_options"]):
        out += "\n"
        _n = "%s_opt%d" % (name, ix)
        if last.get(_n, False):
            _s = " checked"
            checked.add(_n)
        else:
            _s = ""
        out += '<div style="margin-bottom: 10px;">'
        out += '<input type="checkbox" name="%s" id="%s" value="%s"%s />' % (
            _n,
            _n,
            ix,
            _s,
        )
        text = csm_language.source_transform_string(info, i)
        out += "<label for='%s'>%s</label>" % (
            _n,
            text,
        )
        out += "</div>"
    out += "\n</fieldset>"
    out += '<input type="hidden" name="%s" id="%s" value="%s">' % (
        name,
        name,
        last or "",
    )
    checked_str = ",".join(("%r: true" % i) for i in checked)
    out += (
        '\n<script type="text/javascript">'
        "\n// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3"
        "\nvar %s_selected = {%s};"
        '\ndocument.getElementById("%s").value = JSON.stringify(%s_selected);'
        '\ndocument.querySelectorAll("input[type=checkbox][name^=%s_opt]").forEach(function(r){'
        '\n    r.addEventListener("click", function(){'
        '\n        %s_selected[this.getAttribute("name")] = this.checked;'
        '\n    document.getElementById("%s").value = JSON.stringify(%s_selected);'
        "\n    });"
        "\n});"
        "\n// @license-end"
        "\n</script>"
    ) % ((info["csq_name"], checked_str) + (info["csq_name"],) * 6)
    return out


def render_html_radio(last_log, **info):
    if last_log is None:
        last_log = {}
    aria_label = info.get("csq_aria_label", f'catsoop_prompt_{info["csq_name"]}')
    out = "<div role='radiogroup' aria-labelledby='%s'>" % aria_label
    name = info["csq_name"]
    last = last_log.get(info["csq_name"], {"data": None})["data"]
    for ix, i in enumerate(info["csq_options"]):
        out += "\n"
        if last == str(ix):
            _s = " checked"
        else:
            _s = ""
        out += '<div style="margin-bottom: 10px;">'
        out += '<input type="radio" name="%s_opts" id="%s_opts_%s" value="%s"%s />' % (
            name,
            name,
            ix,
            ix,
            _s,
        )
        text = csm_language.source_transform_string(info, i)
        out += '<label for="%s_opts_%s">%s</label>' % (
            name,
            ix,
            text,
        )
        out += "</div>"
    out += "\n</div>"
    out += '<input type="hidden" name="%s" id="%s" value="%s">' % (
        name,
        name,
        last or "",
    )
    out += (
        '\n<script type="text/javascript">'
        "\n// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3"
        '\ndocument.querySelectorAll("input[type=radio][name=%s_opts]").forEach(function(r){'
        '\n    r.addEventListener("click", function(){'
        '\n        document.getElementById("%s").value = this.value;'
        "\n    });"
        "\n});"
        "\n// @license-end"
        "\n</script>"
    ) % (info["csq_name"], info["csq_name"])
    return out


_renderers = {
    "dropdown": render_html_dropdown,
    "radio": render_html_radio,
    "checkbox": render_html_checkbox,
}


def answer_display(**info):
    if info["csq_renderer"] == "checkbox":
        out = "<b>Solution:</b> \n\n<ul style='display:table; list-style: none; padding-left: 10px;'>"
        for c, i in zip(info["csq_soln"], info["csq_options"]):
            out += '<li style="display: table-row;"><span style="display:table-cell; padding-bottom:20px;">'
            "<label style='display: table-cell; padding-left: 10px;'>"
            text = csm_language.source_transform_string(info, i)
            out += '<input type="checkbox" disabled %s /> ' % ("checked" if c else "")
            out += text
            out += "</label></li>"
        out += "</ul>"
    else:
        soln = info["csq_soln"]
        out = "<b>Solution:</b> %s" % (soln,)
    return out
