import os
import ast
import time
import uuid
import fcntl
import base64
import shutil
import signal
import string
import random
import tempfile
import threading
import traceback
import subprocess

always_rerender = True

# inherit things from the pythoncode qtype
tutor.qtype_inherit("pythoncode")

time = time.time

defaults["csq_show_skeleton"] = False
defaults["csq_extra_tests"] = []
defaults["csq_submission_filename"] = "lab.py"
defaults["csq_npoints"] = 0

# we don't want the "Run Code" button from pythoncode
del checktext
del handle_check


def total_points(**info):
    return info["csq_npoints"]


# stupid little helper to safely close a file descriptor
def safe_close(fd):
    try:
        os.close(fd)
    except:
        pass


def render_html(last_log, **info):
    name = info["csq_name"]
    init = last_log.get(name, (None, info["csq_initial"]))
    if isinstance(init, str):
        fname = ""
    else:
        fname, init = init
    params = {
        "name": name,
        "init": str(init),
        "safeinit": (init or "").replace("<", "&lt;"),
        "b64init": base64.b64encode(make_initial_display(info).encode()).decode(),
        "dl": (' download="%s"' % info["csq_skeleton_name"])
        if "csq_skeleton_name" in info
        else "download",
        "dl2": (' download="%s"' % fname)
        if "csq_skeleton_name" in info
        else "download",
    }
    out = ""
    if last_log.get(name, None) is not None:
        try:
            fname, loc = last_log[name]
            loc = os.path.basename(loc)
            qstring = urlencode(
                {"path": json.dumps(info["cs_path_info"]), "fname": loc}
            )
            out += "<br/>"
            safe_fname = (
                fname.replace("<", "")
                .replace(">", "")
                .replace('"', "")
                .replace("'", "")
            )
            out += (
                '<a href="%s/cs_util/get_upload?%s" '
                'download="%s">Download Your '
                "Last Submission</a><br/>"
            ) % (info["cs_url_root"], qstring, safe_fname)
        except:
            pass
        out += (
            """<a href="%s/%s/lab_viewer?lab=%s&name=%s&as=%s" target="_blank"> """
            """Click to View Your Last Submission</a><br />"""
        ) % (
            info["cs_url_root"],
            info["cs_course"],
            "/".join(info["cs_path_info"][1:]),
            name,
            info["cs_username"],
        )
    out += (
        """<input type="file" style="display: none" id=%(name)s name="%(name)s" />"""
        % params
    )
    out += (
        """<button class="btn btn-catsoop" id="%s_select_button">Select File</button>&nbsp;"""
        """<tt><span id="%s_selected_file">No file selected</span></tt>"""
    ) % (name, name)
    out += (
        """<script type="text/javascript">"""
        """$('#%s_select_button').click(function (){$("#%s").click();});"""
        """$('#%s').change(function (){$('#%s_selected_file').text($('#%s').val());});"""
        """</script>"""
    ) % (name, name, name, name, name)
    return out


# helper to correctly write our strings
def pluralize(things):
    l = len(things)
    leader = "s " if l > 1 else " "
    if l == 1:
        rest = str(things[0])
    elif l == 2:
        rest = "%s and %s" % tuple(things)
    else:
        rest = "%s, and %s" % (", ".join(map(str, things[:-1])), things[-1])
    return leader + rest


GET_TESTS_CODE = """
def get_tests(x):
    if isinstance(x, unittest.suite.TestSuite):
        out = []
        for i in x._tests:
            out.extend(get_tests(i))
        return out
    elif isinstance(x, list):
        out = []
        for i in x:
            out.extend(get_tests(i))
        return out
    else:
        return [x.id().split()[0]]
"""


# this is a little bit involved, but so much better with the new supporting
# infrastructure!
def handle_submission(submissions, **info):
    try:
        code = info["csm_loader"].get_file_data(info, submissions, info["csq_name"])
        code = code.decode().replace("\r\n", "\n")
    except:
        return {
            "score": 0,
            "msg": '<div class="bs-callout bs-callout-danger"><span class="text-danger"><b>Error:</b> Unable to decode the specified file.  Is this the file you intended to upload?</span></div>',
        }

    # okay... here we go...
    # first grab the safe interpreter to use during checking
    # and the location of the sandbox
    sandbox_interpreter = info["csq_python_interpreter"]
    id_ = uuid.uuid4().hex
    this_sandbox_location = os.path.join(
        info.get("csq_sandbox_dir", "/tmp/sandbox"), "009checks", id_
    )

    # make sure the sandbox exists
    shutil.rmtree(this_sandbox_location, True)
    # now dump the files there.
    # first, copy the regular files over (test cases, etc)
    shutil.copytree(
        os.path.join(info["cs_data_root"], "courses", *info["cs_path_info"], "_files"),
        this_sandbox_location,
    )

    # then save the user's code with the appropriate name
    with open(
        os.path.join(this_sandbox_location, info["csq_submission_filename"]), "w"
    ) as f:
        f.write(code)

    # and put our modified test.py in place
    magic = None
    while magic is None or magic in code:
        magic = "".join(random.choice(string.ascii_letters) for _ in range(50))
    test_filename = os.path.join(this_sandbox_location, "test.py")
    with open(test_filename) as f:
        labtest = f.read()
    labtest = (
        labtest
        + "\n\nimport unittest.suite\n%s\nprint(%r, flush=True)\nr = res.result\nres.createTests()"
        % (GET_TESTS_CODE, magic)
    )
    labtest += "\n_tests = get_tests(res.test)\nprint(_tests, flush=True)"
    names = ("errors", "failures", "skipped", "unexpectedSuccesses")
    labtest += (
        "\n_failed = {i[0].id().split()[0] for i in sum([getattr(r, i, []) for i in %r], [])}"
        % (names,)
    )
    labtest += "\nprint([i for i in _tests if i not in _failed], flush=True)"
    with open(os.path.join(this_sandbox_location, "test.py"), "w") as f:
        f.write(labtest)

    # at this point, everything should be in place.  time to actually run the check.
    if "csq_tests_to_run" in info:
        tests_to_run = info["csq_tests_to_run"]
    else:
        tests_to_run = [
            {"args": [], "timeout": info.get("csq_timeout", 2)}
        ]  # each test is a 2-tuple: arguments to be given to test.py, and the timeout for this test.

    response = ""
    overall_passed = []
    overall_tests = []
    for count, test in enumerate(tests_to_run):
        test["args"] = list(map(str, test["args"]))

        # set up stdout and stderr
        _o, outfname = tempfile.mkstemp()
        _e, errfname = tempfile.mkstemp()

        def _prep():
            os.setpgrp()
            info["csm_process"].set_pdeathsig()()

        # run the test, keeping track of time
        start = time.time()
        proc = subprocess.Popen(
            [sandbox_interpreter, "test.py"] + test["args"],
            cwd=this_sandbox_location,
            bufsize=0,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            preexec_fn=_prep,
        )
        out = ""
        err = ""
        try:
            out, err = proc.communicate(timeout=test["timeout"])
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            out, err = proc.communicate()
        out = out.decode()
        err = err.decode()

        stop = time.time()

        # hide a little bit of information in stack traces, just in case
        out = out.replace(this_sandbox_location, "TESTING_SANDBOX")
        err = err.replace(this_sandbox_location, "TESTING_SANDBOX")

        # try to separate our logging output from regular output from the program
        sout = out.rsplit(magic, 1)
        failmsg = None
        if len(sout) == 1:
            # magic number didn't show up.  we didn't reach the print.
            # infinite loop / timeout?
            alltests = []
            passed = []
            overall_tests = None
            numtests = None
            info["cs_debug"](
                "FAILED2", info.get("cs_username", None), repr(out), repr(err)
            )
        elif len(sout) > 2:
            # wtf?  more than one magic number should not happen.
            failmsg = "There was an unidentified error when running this test."
            alltests = []
            passed = []
            overall_tests = None
            numtests = None
        else:
            # this is where we hope to be.
            # compute the effect of this test on the overall score
            out, log = sout
            res = log.strip().splitlines()
            try:
                alltests, passed = [ast.literal_eval(i) for i in res]
            except:
                failmsg = "There was an unidentified error when running this test."
                alltests = []
                passed = []
                overall_tests = None
            if overall_tests is not None:
                overall_tests += alltests
            numtests = len(alltests)

        overall_passed += passed

        # truncate the stdout if it is really long.
        outlines = out.strip().splitlines()
        out = "\n".join(outlines)

        if len(outlines) > 1000:
            outlines = outlines[:1000] + ["...OUTPUT TRUNCATED..."]
            out = "\n".join(outlines)
        if len(out) > 10000:
            out = out[:10000] + "\n...OUTPUT TRUNCATED..."

        # how should the response be colored?
        # green if everything passed; red otherwise
        color = "success" if alltests and set(alltests) == set(passed) else "danger"

        # now construct the HTML for this one test.
        response += '<div class="bs-callout bs-callout-%s">' % color
        response += (
            "<p><b>Testing:</b> <code>python3 test.py%s</code> with a timeout of %.1f seconds</p>"
            % ((" " if test["args"] else "") + " ".join(test["args"]), test["timeout"])
        )
        if color == "danger":
            response += (
                '<b class="text-danger">Your code did not pass all test cases.</b><br/>'
            )
            if failmsg is not None:
                response += failmsg
            elif numtests is not None:
                response += "Your code passed %s of %s tests.<br/>" % (
                    len(passed),
                    len(alltests),
                )
            else:
                response += "Your code passed 0 tests.<br/>"
        else:
            if numtests == 1:
                response += (
                    '<b class="text-success">Your code passed this test case.</b>'
                )
            else:
                response += (
                    '<b class="text-success">Your code passed all %s test cases.</b>'
                    % len(alltests)
                )
        response += "<p>Your code ran for %f seconds." % (stop - start)
        if proc.returncode == -9:
            response += (
                "  The process running your code did not run to completion.  It was killed because it would have taken longer than %s second%s to run."
                % (test["timeout"], "" if test["timeout"] == 1 else "s")
            )
        response += "</p>"

        if out.strip() or err.strip():
            response += (
                "<p><button onclick=\"$('#%s_%d_results_showhide').toggle()\">Show/Hide Output</button>"
                % (magic, count)
            )
            response += '<div id="%s_%d_results_showhide" style="display:none">' % (
                magic,
                count,
            )
            if out.strip():
                response += "<p>Your code produced the following output:</p>"
                response += "<p><pre>%s</pre></p>" % out.replace("<", "&lt;")

            if err.strip():
                response += "<p>This test produced the following output:</p>"
                response += "<p><pre>%s</pre></p>" % err.replace("<", "&lt;")
            response += "</div>"
        response += "</div>"

    # all tests are done!
    # clean up (delete all the files associated with this request)
    shutil.rmtree(this_sandbox_location, True)

    if overall_tests is not None:
        response = "<h3>Test Results:</h3><p>Your code passed %d of %d tests.</p>%s" % (
            len(overall_passed),
            len(overall_tests),
            response,
        )
    else:
        response = "<h3>Test Results:</h3><p>Your code passed %d tests.</p>%s" % (
            len(overall_passed),
            response,
        )
    return {
        "score": overall_passed,
        "msg": response,
        "extra_data": {"passed": overall_passed, "run": overall_tests},
    }
