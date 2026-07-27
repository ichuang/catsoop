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

import ast
import html
import logging
import traceback
import collections.abc

LOGGER = logging.getLogger("cs")

tutor.qtype_inherit("smallbox")
bigbox, _ = tutor.question("bigbox")
smallbox, _ = tutor.question("smallbox")
pythoncode, _ = tutor.question("pythoncode")

defaults.update(
    {
        "csq_soln": "",
        "csq_check_function": lambda sub, soln: (
            (type(sub) == type(soln)) and (sub == soln)
        ),
        "csq_input_check": lambda sub: None,
        "csq_npoints": 1,
        "csq_msg_function": lambda sub, soln: "",
        "csq_show_check": False,
        "csq_code_pre": "",
        "csq_mode": "raw",
        "csq_size": 50,
        "csq_renderer": "smallbox",
        "csq_output_mode": "default",
        "csq_initial": "",
    }
)


def gensym(code=""):
    pre = n = "___"
    count = 0
    while n in code:
        n = "%s%s" % (pre, count)
        count += 1
    return n


INVALID_SUBMISSION_MSG = (
    '<font color="red">Your submission could not be '
    "evaluated.  Please check that you have entered a "
    "valid Python expression.</font>  "
)

checktext = "Check Formatting"


def _multi_prompt_config(info):
    prompts = info.get("csq_prompts")
    solutions = info.get("csq_solns")
    if prompts is None:
        if solutions is not None:
            raise ValueError("csq_solns requires csq_prompts")
        return None, None
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("csq_prompts must be a non-empty list of strings")
    if not all(isinstance(prompt, str) for prompt in prompts):
        raise ValueError("csq_prompts must be a non-empty list of strings")
    if solutions is not None:
        if not isinstance(solutions, list):
            raise ValueError("csq_solns must be a list")
        if len(solutions) != len(prompts):
            raise ValueError("csq_solns must have the same length as csq_prompts")
    return prompts, solutions


def _multi_prompt_field_name(info, index):
    return "__%s_%04d" % (info["csq_name"], index)


def _submission_data(submissions, name, strip=True):
    entry = submissions.get(name, {"data": ""})
    if isinstance(entry, collections.abc.Mapping):
        value = entry.get("data", "")
    else:
        value = entry
    value = "" if value is None else str(value)
    return value.strip() if strip else value


def _submission_expression(submissions, info):
    prompts, _ = _multi_prompt_config(info)
    if prompts is None:
        return _submission_data(submissions, info["csq_name"])
    values = {
        str(index): _submission_data(
            submissions,
            _multi_prompt_field_name(info, index),
        )
        for index in range(len(prompts))
    }
    if any(value == "" for value in values.values()):
        return ""
    return repr(values)


def handle_check(submissions, **info):
    subbed = _submission_expression(submissions, info)
    if subbed == "":
        return '<font color="red">Your submission is not properly formatted.</font>'
    pythoncode["get_sandbox"](info)
    code = info["csq_code_pre"]
    code += "\n%s" % subbed
    error = None
    try:
        ast.parse(subbed, mode="eval")
    except Exception:
        error = '<font color="red">Your submission is not properly formatted.</font>'
    if error is None:
        sub = info["sandbox_run_code"](
            info, code, info.get("csq_options", {}), result_as_string=True
        )
        if sub.get("err", "").strip():
            error = (
                '<font color="red">Your submission is not properly formatted.</font>'
            )

    return error or "Your submission is properly formatted."


def handle_submission(submissions, **info):
    sub = _submission_expression(submissions, info)
    inp = info["csq_input_check"](sub)
    if inp is not None:
        return {"score": 0.0, "msg": '<font color="red">%s</font>' % inp}

    test_result = None
    pythoncode["get_sandbox"](info)
    if info["csq_mode"] == "raw":
        soln = info["csq_soln"]
    else:
        code = info["csq_code_pre"]
        s = info["csq_soln"]
        code += "\n_catsoop_answer = %s" % s
        opts = info.get("csq_options", {})
        test_result_soln = info["sandbox_run_code"](
            info, code, opts, result_as_string=True
        )
        if test_result_soln.get("remote_unavailable", False):
            return {
                "score": 0.0,
                "msg": '<font color="red">%s</font>' % test_result_soln["err"],
            }
        soln = test_result_soln["info"]["result"]
        soln = eval(soln, info)
    try:
        if sub == "":
            return {"score": 0.0, "msg": INVALID_SUBMISSION_MSG}
        ast.parse(sub, mode="eval")
        code = info["csq_code_pre"]
        code += "\n_catsoop_answer = %s" % sub
        opts = info.get("csq_options", {})
        test_result_sub = info["sandbox_run_code"](
            info, code, opts, result_as_string=info["csq_mode"] != "raw"
        )
        if test_result_sub.get("remote_unavailable", False):
            return {
                "score": 0.0,
                "msg": '<font color="red">%s</font>' % test_result_sub["err"],
            }
        sub = test_result_sub["info"]["result"]
        if info["csq_mode"] != "raw":
            sub = ast.literal_eval(sub)
    except Exception as err:
        LOGGER.info(
            "[qtypes.pythonic] could not evaluate submission for question %r (%s)",
            info.get("csq_name"),
            type(err).__name__,
        )
        msg = ""
        mfunc = info["csq_msg_function"]
        try:
            msg += mfunc(sub, soln)
        except:
            try:
                msg += mfunc(sub)
            except:
                pass
        if msg == "":
            msg = INVALID_SUBMISSION_MSG
        if info["csq_show_check"]:
            msg += '<img src="%s" /><br/>' % info["cs_cross_image"]
        return {"score": 0.0, "msg": msg}

    check = info["csq_check_function"]
    try:
        check_result = check(sub, soln)
    except:
        err = info["csm_errors"]
        e = err.html_format(err.clear_info(info, traceback.format_exc()))
        check_result = (
            0.0,
            '<font color="red">An error occurred in the checker: <pre>%s</pre></font>'
            % e,
        )

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
    response = ""
    if info["csq_show_check"]:
        if percent == 1.0:
            response = '<img src="%s" alt="Correct" /><br/>' % info["cs_check_image"]
        elif percent == 0.0:
            response = '<img src="%s" alt="Incorrect" /><br/>' % info["cs_cross_image"]

    response += msg

    return {"score": percent, "msg": response}


def render_html(last_log, **info):
    prompts, _ = _multi_prompt_config(info)
    if prompts is not None:
        last_log = last_log or {}
        out = ["<fieldset>"]
        overall_label = info.get(
            "csq_aria_label",
            "catsoop_prompt_%s" % info["csq_name"],
        )
        for index, prompt in enumerate(prompts):
            field_name = _multi_prompt_field_name(info, index)
            prompt_id = "%s_prompt" % field_name
            escaped_field_name = html.escape(field_name, quote=True)
            escaped_prompt_id = html.escape(prompt_id, quote=True)
            aria_labelledby = html.escape(
                "%s %s" % (overall_label, prompt_id),
                quote=True,
            )
            value = html.escape(
                _submission_data(last_log, field_name, strip=False),
                quote=True,
            )
            out.append('<div class="pythonic_prompt">')
            out.append(
                '<label id="%s" for="%s">%s</label>&nbsp;&nbsp;'
                % (
                    escaped_prompt_id,
                    escaped_field_name,
                    csm_language.source_transform_string(info, prompt),
                )
            )
            size = info.get("csq_size")
            size_attribute = (
                ""
                if size is None
                else ' size="%s"' % html.escape(str(size), quote=True)
            )
            out.append(
                '<input type="text"%s aria-labelledby="%s" '
                'value="%s" name="%s" id="%s" />'
                % (
                    size_attribute,
                    aria_labelledby,
                    value,
                    escaped_field_name,
                    escaped_field_name,
                )
            )
            out.append("</div>")
        out.append("</fieldset>")
        return "\n".join(out)

    renderer = info["csq_renderer"]
    if renderer == "smallbox":
        return smallbox["render_html"](last_log, **info)
    if renderer == "bigbox":
        return bigbox["render_html"](last_log, **info)
    if renderer in {"ace", "textarea"}:
        multiline_info = dict(info)
        multiline_info["csq_interface"] = renderer
        return pythoncode["render_html"](last_log, **multiline_info)
    return (
        "<font color='red'>Invalid <tt>pythonic</tt> renderer: %s</font>"
        % html.escape(str(renderer))
    )


def _format_solution(solution, info):
    output_mode = info["csq_output_mode"]
    if output_mode not in {"default", "formatted"}:
        raise ValueError("Invalid csq_output_mode: %r" % output_mode)
    use_repr = info["csq_mode"] == "raw" and output_mode == "default"
    return repr(solution) if use_repr else str(solution)


def answer_display(**info):
    prompts, solutions = _multi_prompt_config(info)
    if solutions is None:
        solution = _format_solution(info["csq_soln"], info)
        return "<p><b>Solution:</b> <tt>%s</tt><p>" % solution

    out = ["<p><b>Solution:</b></p>", '<table class="pythonic_solutions">']
    for prompt, solution in zip(prompts, solutions):
        out.append(
            '<tr><th scope="row">%s</th><td><tt>%s</tt></td></tr>'
            % (
                csm_language.source_transform_string(info, prompt),
                _format_solution(solution, info),
            )
        )
    out.append("</table>")
    return "\n".join(out)
