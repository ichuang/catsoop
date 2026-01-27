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
import json
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


def handle_check(submissions, **info):
    pythoncode["get_sandbox"](info)
    code = info["csq_code_pre"]
    subbed = submissions[info["csq_name"]]["data"].strip()
    code += "\n%s" % subbed
    error = None
    try:
        assert isinstance(ast.parse(subbed).body[0], ast.Expr)
    except:
        error = '<font color="red">Your submission is not properly formatted.</font>'
    if error is None:
        sub = info["sandbox_run_code"](
            info, code, info.get("csq_options", {}), result_as_string=True
        )
        if sub["err"].strip():
            error = (
                '<font color="red">Your submission is not properly formatted.</font>'
            )

    return error or "Your submission is properly formatted."


def handle_submission(submissions, **info):
    '''
    Parse input and grade.
    Properly handle csq_rows (multi-row input) and csq_prompts (multiple input boxes)
    '''
    if 'csq_rows' in info:			# multi-row input via textarea
        sub = submissions[info["csq_name"]].strip()
        sub = {'0': sub}
        sub = json.dumps(sub)
    elif not 'csq_prompts' in info:		# no prompts specified: use single input submission
        sub = submissions[info["csq_name"]].strip()
    else:
        sub = {}				# multiple submission boxes: gather in dict and jsonify for python checker
        LOGGER.error("[qtypes.pythonic] info['csq_name']: %r" % info['csq_name'])
        for ix in range(len(info['csq_prompts'])):
            qbox_name = "__%s_%04d" % (info["csq_name"], ix)
            # sub[ix] = submissions[qbox_name].strip()
            sub[ix] = submissions[qbox_name] 
        sub = json.dumps(sub)
    LOGGER.debug("[qtypes.pythonic] submission: %r" % sub)

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
            sub = eval(sub, info)
    except Exception as err:
        LOGGER.error("[qtypes.pythonic] traceback: %s" % traceback.format_exc())
        LOGGER.error("[qtypes.pythonic] invalid submission: %r" % sub)
        LOGGER.error("[qtypes.pythonic] invalid submission exception=%s" % str(err))
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
    '''
    Generate HTML for the pythonic problem.
    If csq_rows is defined, then produce a multi-row code box using a routine in pythoncode.
    if csq_prompts is defined, then produce a table of one or more rows of input fields.
    '''
    last_log = last_log or {}
    if 'csq_rows' in info:			# if csq_nrows is present then display a textarea instead of a one line box
        info['csq_interface'] = 'ace'
        return tutor.question("pythoncode")[0]["render_html"](last_log, **info)

    if not 'csq_prompts' in info:		# no prompts specified: use default single-input-box aka smallbox
        if info.get("csq_renderer", "smallbox") == "bigbox":
            return bigbox["render_html"](last_log, **info)
        else:
            return smallbox["render_html"](last_log, **info)

    # allow for multiple input boxes, each with its own prompt, as specified by csq_prompts
    prompts = info["csq_prompts"]
    if not isinstance(prompts, list):
        msg = "[qtypes.pythonic] csq_prompts expected to be a list, but got instead: %r" % prompts
        LOGGER.error(msg)
        raise Exception(msg)
        
    out = '<table border="0">'
    for (ix, prompt) in enumerate(prompts):
        qbox_name = "__%s_%04d" % (info["csq_name"], ix)
        out += '<tr><td align="right">'
        out += csm_language.source_transform_string(info, prompt)
        out += "</td><td>"
        out += '<input type="text"'
        if info.get("csq_size", None) is not None:
            out += ' size="%s"' % info["csq_size"]

        last_response_dict = last_log.get(qbox_name, {})
        LOGGER.error("[qtypes.pythonic.render_heml] last_response for %s = %s" % (qbox_name, last_response_dict))
        out += ' value="%s"' % escape(last_response_dict.get("data", ""))
        out += ' name="%s"' % qbox_name
        out += ' id="%s"' % qbox_name
        out += " /></td></tr>"
    return out + "</table>"


def answer_display(**info):
    '''
    Display answer.  Properly handle csq_prompts (multi-row inputs)
    '''
    fmt = "%s"
    if info["csq_mode"] == "raw" and not info.get("csq_output_mode") == "formatted":
        fmt = "%r"

    if not 'csq_solns' in info:	# default single answer display
        out = ("<p>Solution: <tt>{}</tt><p>".format(fmt)) % (info["csq_soln"],)
    else:		# use table with multiple respones if csq_solns specified and is list
        solns = info["csq_solns"]
        prompts = info['csq_prompts']
        if not isinstance(solns, list) and  isinstance(prompts, list) and len(solns)==len(prompts):
            msg = "[qtypes.pythonic] csq_solns expected to be a list, but got instead: %r" % solns
            LOGGER.error(msg)
            raise Exception(msg)
        out = '<table border="0">'
        for (ix, (prompt, soln)) in enumerate(zip(prompts, solns)):
            out += '<tr><td align="right">'
            out += csm_language.source_transform_string(info, prompt)
            out += "</td><td>"
            out += ("<tt>{}</tt>".format(fmt)) % soln
            out += "</td></tr>"
        out += "</table>"
    return out
