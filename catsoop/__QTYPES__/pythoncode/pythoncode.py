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
import ast
import html
import json
import base64
import mimetypes
import traceback

import collections.abc

from base64 import b64encode
from urllib.parse import urlencode


def _execfile(*args):
    fn = args[0]
    with open(fn) as f:
        c = compile(f.read(), fn, "exec")
    exec(c, *args[1:])


def get_sandbox(context):
    base = os.path.join(
        context["cs_fs_root"], "__QTYPES__", "pythoncode", "__SANDBOXES__", "base.py"
    )
    _execfile(base, context)


SCRIPTS = """
<script type="text/javascript" src="BASE/js/codemirror/codemirror.bundle.min.js"></script>
"""


def extra_headers(info):
    if info["csq_interface"] == "codemirror":
        return SCRIPTS
    else:
        return None


def html_format(string):
    s = (
        string.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\t", "    ")
        .splitlines(False)
    )
    jx = 0
    for ix, line in enumerate(s):
        for jx, char in enumerate(line):
            if char != " ":
                break
        s[ix] = "&nbsp;" * jx + line[jx:]

    return "<br/>".join(s)


defaults = {
    "csq_input_check": lambda x: None,
    "csq_code_pre": "",
    "csq_code_post": "",
    "csq_initial": "pass  # Your code here",
    "csq_soln": 'print("Hello, World!")',
    "csq_tests": [],
    "csq_hint": lambda score, code, info: "",  # post-test hint generator
    "csq_interface": "codemirror",
    "csq_rows": 14,
    "csq_font_size": 16,
    "csq_always_show_tests": False,
    "csq_test_defaults": {},
    "csq_use_simple_checker": False,
    "csq_result_as_string": False,
    "csq_show_check": False,
}


class NoResult:
    pass


def _default_check_function(sub, soln):
    sub = sub.get("result", NoResult)
    soln = soln.get("result", NoResult)
    return sub == soln and sub is not NoResult


def _default_simple_check_function(sub, soln):
    return sub == soln


def _default_string_check_function(sub, soln):
    return ast.literal_eval(sub) == ast.literal_eval(soln)


test_defaults = {
    "npoints": 1,
    "code": "",
    "code_pre": "",
    "variable": "ans",
    "description": "",
    "include": False,
    "include_soln": False,
    "include_description": False,
    "grade": True,
    "show_description": True,
    "show_code": True,
    "show_stderr": True,
    "transform_output": lambda x: '<tt style="white-space: pre-wrap">%s</tt>'
    % (html_format(repr(x)),),
    "sandbox_options": {},
    "count_opcodes": False,
    "opcode_limit": None,
    "show_timing": False,
    "show_opcode_count": False,
}


def init(info):
    if info["csq_interface"] == "upload":
        info["csq_rerender"] = True


def total_points(**info):
    if "csq_npoints" in info:
        return info["csq_npoints"]
    return total_test_points(**info)


def total_test_points(**info):
    bak = info["csq_tests"]
    info["csq_tests"] = []
    for i in bak:
        info["csq_tests"].append(dict(test_defaults))
        info["csq_tests"][-1].update(info["csq_test_defaults"])
        info["csq_tests"][-1].update(i)
    return sum(i["npoints"] for i in info["csq_tests"])


checktext = "Run Code"


def get_code(sub, info):
    try:
        code = sub.get("data", None)
        if code is None:
            code = info["csm_cslog"].retrieve_upload(sub["id"])[1]
        if isinstance(code, bytes):
            code = code.decode("utf-8-sig")
        return code.replace("\r\n", "\n")
    except:
        return {
            "score": 0,
            "msg": '<div class="bs-callout bs-callout-danger"><span class="text-danger"><b>Error:</b> Unable to decode the specified file.  Is this the file you intended to upload?</span></div>',
        }


def handle_check(submissions, **info):
    code = get_code(submissions[info["csq_name"]], info)
    if not isinstance(code, str):
        return code

    code = "\n\n".join(["import os\nos.unlink(__file__)", info["csq_code_pre"], code])

    get_sandbox(info)
    results = info["sandbox_run_code"](info, code, info.get("csq_sandbox_options", {}))

    err = info["fix_error_msg"](
        results["fname"], results["err"], info["csq_code_pre"].count("\n") + 2, code
    )

    complete = results.get("info", {}).get("complete", False)

    trunc = False
    outlines = results["out"].split("\n")
    if len(outlines) > 10:
        trunc = True
        outlines = outlines[:10]
    out = "\n".join(outlines)
    if len(out) >= 5000:
        trunc = True
        out = out[:5000]
    if trunc:
        out += "\n\n...OUTPUT TRUNCATED..."

    timeout = False
    if (not complete) and ("SIGTERM" in err):
        timeout = True
        err = (
            "Your code did not run to completion, "
            "but no error message was returned."
            "\nThis normally means that your code contains an "
            "infinite loop or otherwise took too long to run."
        )

    msg = '<div class="response">'
    if not timeout:
        msg += "<p><b>"
        if complete:
            msg += '<font color="darkgreen">' "Your code ran to completion." "</font>"
        else:
            msg += '<font color="red">' "Your code did not run to completion." "</font>"
        msg += "</b></p>"
    if out != "":
        msg += "\n<p><b>Your code produced the following output:</b>"
        msg += "<br/><pre>%s</pre></p>" % html_format(out)
    if err != "":
        if not timeout:
            msg += "\n<p><b>Your code produced an error:</b>"
        msg += "\n<br/><font color='red'><tt>%s</tt></font></p>" % html_format(err)
    msg += "</div>"

    return msg


def handle_submission(submissions, **info):
    code = get_code(submissions[info["csq_name"]], info)
    if not isinstance(code, str):
        return code
    if info["csq_use_simple_checker"]:
        if info["csq_result_as_string"]:
            default_checker = _default_string_check_function
        else:
            default_checker = _default_simple_check_function
    else:
        default_checker = _default_check_function
    default_checker = info.get("csq_check_function", default_checker)
    tests = [dict(test_defaults) for i in info["csq_tests"]]
    for i, j in zip(tests, info["csq_tests"]):
        i.update(info["csq_test_defaults"])
        i.update(j)
    show_tests = [i for i in tests if i["include"]]
    if len(show_tests) > 0:
        code = code.rsplit("### Test Cases")[0]

    inp = info["csq_input_check"](code)
    if inp is not None:
        msg = ('<div class="response">' '<font color="red">%s</font>' "</div>") % inp
        return {"score": 0, "msg": msg}

    bak = info["csq_tests"]
    info["csq_tests"] = []
    for i in bak:
        new = dict(test_defaults)
        i.update(info["csq_test_defaults"])
        new.update(i)
        if new["grade"]:
            info["csq_tests"].append(new)

    get_sandbox(info)

    score = 0
    msg = (
        '\n<br/><details%s><summary class="btn btn-catsoop">Show/Hide Detailed Results</summary>'
        % (" open" if info["csq_always_show_tests"] else "")
    )
    msg += (
        '<div class="response" id="%s_result_showhide">' "<h2>Test Results:</h2>"
    ) % (info["csq_name"],)
    test_results = []
    count = 1
    for test in info["csq_tests"]:
        test["result_as_string"] = test.get(
            "result_as_string", info.get("csq_result_as_string", False)
        )
        out, err, log = info["sandbox_run_test"](info, code, test)
        if "cached_result" in test:
            log_s = {
                "result": test["cached_result"],
                "complete": True,
                "duration": 0.0,
                "opcode_count": 0,
                "opcode_limit_reached": False,
            }
            err_s = ""
            out_s = ""
        else:
            out_s, err_s, log_s = info["sandbox_run_test"](info, info["csq_soln"], test)
        if count != 1:
            msg += "\n<p></p><hr/><p></p>"
        msg += "\n<center><h3>Test %02d</h3>" % count
        if test["show_description"]:
            msg += "\n<i>%s</i>" % test["description"]
        msg += "</center><p></p>"
        if test["show_code"]:
            html_code_pieces = [
                i for i in map(lambda x: html_format(test[x]), ["code_pre", "code"])
            ]
            html_code_pieces.insert(1, "#Your Code Here")
            html_code = "<br/>".join(i for i in html_code_pieces if i)
            msg += "\nThe test case was:<br/>\n<p><tt>%s</tt></p>" % html_code
            msg += "<p>&nbsp;</p>"

        result = {"details": log, "out": out, "err": err}
        result_s = {"details": log_s, "out": out_s, "err": err_s}
        if test["variable"] is not None:
            if "result" in log:
                result["result"] = log["result"]
                del log["result"]
            if "result" in log_s:
                result_s["result"] = log_s["result"]
                del log_s["result"]

        checker = test.get("check_function", default_checker)
        try:
            if info["csq_use_simple_checker"]:
                # legacy checker
                check_result = checker(result["result"], result_s["result"])
            else:
                check_result = checker(result, result_s)
        except:
            check_result = 0.0

        if isinstance(check_result, collections.abc.Mapping):
            percentage = check_result["score"]
            extra_msg = check_result["msg"]
        elif isinstance(check_result, collections.abc.Sequence):
            percentage, extra_msg = check_result
        else:
            percentage = check_result
            extra_msg = ""

        test_results.append(percentage)

        imfile = None
        if percentage == 1.0:
            imfile = info["cs_check_image"]
        elif percentage == 0.0:
            imfile = info["cs_cross_image"]

        score += percentage * test["npoints"]

        expected_variable = test["variable"] is not None
        solution_ran = result_s != {}
        submission_ran = result != {}
        show_code = test["show_code"]
        error_in_solution = result_s["err"] != ""
        error_in_submission = result["err"] != ""
        solution_produced_output = result_s["out"] != ""
        submission_produced_output = result["out"] != ""
        got_submission_result = "result" in result
        got_solution_result = "result" in result_s
        if imfile is None:
            image = ""
        else:
            image = "<img src='%s' />" % imfile

        # report timing and/or opcode count
        if test["show_timing"] == True:
            test["show_timing"] = "%.06f"
        do_timing = test["show_timing"] and "duration" in result_s["details"]
        do_opcount = test["show_opcode_count"] and "opcode_count" in result_s["details"]
        if do_timing or do_opcount:
            msg += "\n<p>"
        if do_timing:
            _timing = result_s["details"]["duration"]
            msg += (
                "\nOur solution ran for %s seconds." % test["show_timing"]
            ) % _timing
        if do_timing and do_opcount:
            msg += "\n<br/>"
        if do_opcount:
            _opcount = result_s["details"]["opcode_count"]
            msg += "\nOur solution executed %s Python opcodes.<br/>" % _opcount
        if do_timing or do_opcount:
            msg += "\n</p>"

        if expected_variable and show_code:
            if got_solution_result:
                msg += (
                    "\n<p>Our solution produced the following value for <tt>%s</tt>:"
                ) % test["variable"]
                m = test["transform_output"](result_s["result"])
                msg += "\n<br/><font color='blue'>%s</font></p>" % m
            else:
                msg += (
                    "\n<p>Our solution did not produce a value for <tt>%s</tt>.</p>"
                ) % test["variable"]

        if solution_produced_output and show_code:
            msg += "\n<p>Our code produced the following output:"
            msg += "<br/><pre>%s</pre></p>" % html_format(result_s["out"])

        if error_in_solution and test["show_stderr"]:
            msg += "\n<p><b>OOPS!</b> Our code produced an error:"
            e = html_format(result_s["err"])
            msg += "\n<br/><font color='red'><tt>%s</tt></font></p>" % e

        if show_code:
            msg += "<p>&nbsp;</p>"

        # report timing and/or opcode count
        do_timing = test["show_timing"] and "duration" in result["details"]
        do_opcount = test["show_opcode_count"] and "opcode_count" in result["details"]
        if do_timing or do_opcount:
            msg += "\n<p>"
        if do_timing:
            _timing = result["details"]["duration"]
            msg += (
                "\nYour solution ran for %s seconds." % test["show_timing"]
            ) % _timing
        if do_timing and do_opcount:
            msg += "\n<br/>"
        if do_opcount:
            _opcount = result["details"]["opcode_count"]
            msg += "\nYour code executed %d Python opcodes.<br/>" % _opcount
        if do_timing or do_opcount:
            msg += "\n</p>"

        if expected_variable and show_code:
            if got_submission_result:
                msg += (
                    "\n<p>Your submission produced the following value for <tt>%s</tt>:"
                ) % test["variable"]
                m = test["transform_output"](result["result"])
                msg += "\n<br/><font color='blue'>%s</font>%s</p>" % (m, image)
            else:
                msg += (
                    "\n<p>Your submission did not produce a value for <tt>%s</tt>.</p>"
                ) % test["variable"]
        else:
            msg += "\n<center>%s</center>" % (image)

        if submission_produced_output and show_code:
            msg += "\n<p>Your code produced the following output:"
            msg += "<br/><pre>%s</pre></p>" % html_format(result["out"])

        if error_in_submission and test["show_stderr"]:
            msg += "\n<p>Your submission produced an error:"
            e = html_format(result["err"])
            msg += "\n<br/><font color='red'><tt>%s</tt></font></p>" % e
            msg += "\n<br/><center>%s</center>" % (image)

        if extra_msg:
            msg += "\n<p>%s</p>" % extra_msg

        count += 1

    msg += "\n</div></details>"
    tp = total_test_points(**info)
    overall = float(score) / tp if tp != 0 else 0
    hint_func = info.get("csq_hint")
    if hint_func:
        try:
            hint = hint_func(test_results, code, info)
            msg += hint or ""
        except Exception as err:
            pass
    if info["csq_show_check"]:
        if overall == 1.0:
            checkimg = '<img src="%s" />' % info["cs_check_image"]
        elif overall == 0.0:
            checkimg = '<img src="%s" />' % info["cs_cross_image"]
        else:
            checkimg = ""
    else:
        checkimg = ""
    msg = (
        (
            ("\n<br/>&nbsp;Your score on your most recent " "submission was: %01.02f%%")
            % (overall * 100)
        )
        + checkimg
        + msg
    )
    out = {"score": overall, "msg": msg}
    return out


def make_initial_display(info):
    init = info["csq_initial"]
    tests = [dict(test_defaults) for i in info["csq_tests"]]
    for i, j in zip(tests, info["csq_tests"]):
        i.update(j)
    show_tests = [i for i in tests if i["include"]]
    l = len(show_tests) - 1
    if l > -1:
        init += "\n\n\n### Test Cases:\n"
    get_sandbox(info)
    for ix, i in enumerate(show_tests):
        i["result_as_string"] = i.get(
            "result_as_string", info.get("csq_result_as_string", False)
        )
        init += "\n# Test Case %d" % (ix + 1)
        if i["include_soln"]:
            if "cached_result" in i:
                log_s = i["cached_result"]
            else:
                out_s, err_s, log_s = info["sandbox_run_test"](
                    info, info["csq_soln"], i
                )
            init += " (Should print: %s)" % log_s
        init += "\n"
        if i["include_description"]:
            init += "# %s\n" % i["description"]
        init += i["code"]
        if info.get("csq_python3", True):
            init += '\nprint("Test Case %d:", %s)' % (ix + 1, i["variable"])
            if i["include_soln"]:
                init += '\nprint("Expected:", %s)' % (log_s,)
        else:
            init += '\nprint "Test Case %d:", %s' % (ix + 1, i["variable"])
            if i["include_soln"]:
                init += '\nprint "Expected:", %s' % (log_s,)
        if ix != l:
            init += "\n"
    return init


def render_html_textarea(last_log, **info):
    return tutor.question("bigbox")[0]["render_html"](last_log, **info)


def render_html_upload(last_log, **info):
    name = info["csq_name"]
    init = last_log.get(
        name, {"type": "file", "data": info["csq_initial"], "name": "", "init": True}
    )
    fname = init.get("name", "")
    init_code = get_code(init, info)
    if isinstance(init_code, dict):
        init_code = None
    params = {
        "name": name,
        "aria_label": info.get("csq_aria_label", f'catsoop_prompt_{info["csq_name"]}'),
        "init": str(init_code),
        "safeinit": html.escape(init_code or ""),
        "b64init": b64encode(make_initial_display(info).encode()).decode(),
        "dl": (
            (' download="%s"' % info["csq_skeleton_name"])
            if "csq_skeleton_name" in info
            else "download"
        ),
    }
    out = ""
    if info.get("csq_show_skeleton", True):
        out += (
            """\n<a href="data:text/plain;base64,%(b64init)s" """
            """target="_blank"%(dl)s>Code Skeleton</a><br />"""
        ) % params
    link = None
    try:
        if "id" in init:
            qstring = urlencode({"id": init["id"]})
            link = "%s/_util/get_upload?%s" % (info["cs_url_root"], qstring)
        elif "init" not in init:
            mtype = mimetypes.guess_type(init["name"])[0] or "application/octet-stream"
            link = "data:%s;base64,%s" % (
                mtype,
                base64.b64encode(init["data"]).decode("utf-8"),
            )
    except:
        pass
    if link is not None:
        out += "<br/>"
        out += (
            '<a href="%s" ' 'download="%s">Download Most ' "Recent Submission</a><br/>"
        ) % (
            link,
            html.escape(init["name"]),
        )
    out += (
        '\n<input type="file" style="display: none" id="%(name)s" name="%(name)s" aria-labelledby="%(aria_label)s"/>'
    ) % params
    out += (
        """\n<button class="btn btn-catsoop" id="%s_select_button">Select File</button>&nbsp;"""
        """\n<tt><span id="%s_selected_file">No file selected</span></tt>"""
    ) % (name, name)
    out += (
        """\n<script type="text/javascript">"""
        "\n// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3"
        """\ndocument.getElementById('%(name)s').value = '';"""
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
        """\n</script>"""
    ) % params
    return out


def render_html_codemirror(last_log, **info):
    name = info["csq_name"]
    init = last_log.get(name, None)
    if init is None:
        init = make_initial_display(info)
    else:
        init = html.escape(get_code(init, info))
    return (
        f'\n<textarea name="{name}" id="{name}">{init}</textarea>'
        '\n<script type="text/javascript">'
        f"\nvar cs_codemirror_{name} = catsoop.codemirror.editorFromTextArea(document.getElementById('{name}'), 'python');"
        "\n</script>"
    )


RENDERERS = {
    "textarea": render_html_textarea,
    "codemirror": render_html_codemirror,
    "upload": render_html_upload,
}


def render_html(last_log, **info):
    renderer = info["csq_interface"]
    if renderer in RENDERERS:
        return RENDERERS[renderer](last_log or {}, **info)
    return (
        "<font color='red'>" "Invalid <tt>pythoncode</tt> interface: %s" "</font>"
    ) % renderer


def answer_display(**info):
    out = (
        "Here is the solution we wrote:<br/>"
        '\n<pre><code id="%s_soln_highlight" class="lang-python">%s</code></pre>'
        '\n<script type="text/javascript">'
        "\n// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3"
        '\nhljs.highlightBlock(document.getElementById("%s_soln_highlight"));'
        "\n// @license-end"
        "\n</script>"
    ) % (info["csq_name"], info["csq_soln"].replace("<", "&lt;"), info["csq_name"])
    return out
