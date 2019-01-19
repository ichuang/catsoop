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

import ast
import logging
import traceback
import collections.abc

LOGGER = logging.getLogger(__name__)

tutor.qtype_inherit("smallbox")
base1, _ = tutor.question("pythoncode")

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


def handle_submission(submissions, **info):
    sub = submissions[info["csq_name"]].strip()
    LOGGER.error("[qtypes.pythonic] submission: %r" % sub)

    inp = info["csq_input_check"](sub)
    if inp is not None:
        return {"score": 0.0, "msg": '<font color="red">%s</font>' % inp}

    base1["get_sandbox"](info)
    if info["csq_mode"] == "raw":
        soln = info["csq_soln"]
    else:
        code = info["csq_code_pre"]
        s = info["csq_soln"]
        code += "\n_catsoop_answer = %s" % s
        opts = info.get("csq_options", {})
        soln = info["sandbox_run_code"](info, code, opts)["info"]["result"]
    try:
        if sub == "":
            LOGGER.debug("[qtypes.pythonic] invalid submission, empty submission")
            return {"score": 0.0, "msg": INVALID_SUBMISSION_MSG}
        ast.parse(sub, mode="eval")
        code = info["csq_code_pre"]
        code += "\n_catsoop_answer = %s" % sub
        opts = info.get("csq_options", {})
        LOGGER.debug("[qtypes.pythonic] code to run:\n%s" % code)
        sub = info["sandbox_run_code"](info, code, opts)["info"]["result"]
    except Exception as err:
        LOGGER.error("[qtypes.pythonic] invalid submission: %r" % sub)
        LOGGER.error("[qtypes.pythonic] invalid submission exception=%s" % str(err))
        LOGGER.error("[qtypes.pythonic] traceback: %s" % traceback.format_exc())
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
            response = '<img src="%s" /><br/>' % info["cs_check_image"]
        elif percent == 0.0:
            response = '<img src="%s" /><br/>' % info["cs_cross_image"]

    response += msg

    return {"score": percent, "msg": response}


def answer_display(**info):
    if info["csq_mode"] == "raw":
        out = "<p>Solution: <tt>%r</tt><p>" % (info["csq_soln"],)
    else:
        out = "<p>Solution: <tt>%s</tt><p>" % (info["csq_soln"],)
    return out
