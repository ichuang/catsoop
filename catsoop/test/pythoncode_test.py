import sys
import logging
import catsoop
import catsoop.loader as loader
import catsoop.base_context as base_context
from catsoop.check import evaled

from ..test import CATSOOPTest

LOGGER = logging.getLogger("cs")

# uncomment the following to debug
# LOGGER.disabled = False
# LOGGER.setLevel(0)


def gd_test(submission, solution):
    if isinstance(submission, dict):
        submission = submission.get("result")
    if isinstance(solution, dict):
        solution = solution.get("result")
    print("submission=%s, solution=%s" % (submission, solution))
    return submission == solution


def sgd_hint(test_results, code, info):
    """
    Hint function: this is run after tests, and can return a string to be added
    to the message shown to the student.  For example, this could check for common
    wrong answers and provide a corresponding hint.
    """
    if all(test_results):  # no hints if all correct
        return ""
    test = info["csq_tests"][2]
    out, err, log = info["sandbox_run_test"](info, code, test)
    test_bad1_sgd_function = """def sgd(x):
    return x > 3
    """
    out_s, err_s, log_s = info["sandbox_run_test"](info, test_bad1_sgd_function, test)
    if test["check_function"](log, log_s):
        msg = "<font color='blue'>"
        msg += "Hint: your function has its comparison threshold set too low"
        msg += "</font>"
        return msg
    return ""


csq_name = "test_question"

sgd_function = """def sgd(x):
    return x > 5
"""

test_good_sgd_function = """def sgd(x):
    return x > 4.5
"""

qkw = dict(
    csq_npoints=2,
    csq_code_pre="",
    csq_initial="""def sgd(x):
    pass
""",
    csq_soln=sgd_function,
    csq_tests=[
        {"code": "ans=sgd(10)", "check_function": gd_test},
        {"code": "ans=sgd(1)", "check_function": gd_test},
        {"code": "ans=sgd(4)", "check_function": gd_test},
    ],
)

# -----------------------------------------------------------------------------


class Test_Pythoncode(CATSOOPTest):
    """
    pythoncode question type
    """

    def setUp(self):
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context
        self.cname = context["cs_unit_test_course"]
        context["csq_python_interpreter"] = "/usr/local/bin/python"
        self.context = context

        (csq, info) = context["tutor"].question(context, "pythoncode", **qkw)
        info["csm_loader"] = context["csm_loader"]
        info["csm_process"] = context["csm_process"]
        info["csm_util"] = context["csm_util"]
        info["csq_name"] = csq_name
        info["cs_version"] = context["cs_version"]
        info["cs_upload_management"] = ""
        info["cs_fs_root"] = context["cs_fs_root"]
        info["cs_cross_image"] = "FILE_CROSS_IMAGE"
        info["cs_check_image"] = "FILE_CHECK_IMAGE"
        info["cs_python_interpreter"] = sys.executable
        info["csq_python_interpreter"] = sys.executable
        info["csq_python_sandbox"] = "python"
        self.csq = csq
        self.info = info
        # uncomment the following to debug
        # LOGGER.setLevel(0)

    def test_submit(self):
        # test code submission (and evaluation using local sandbox)
        context = self.context
        csq = self.csq
        info = self.info
        form = {csq_name: test_good_sgd_function}
        ret = csq["handle_submission"](form, **info)
        print("ret=", ret)

        assert "Our solution did not produce a value for" not in str(ret)
        assert "FILE_CHECK_IMAGE" in str(ret)

    def test_hints1(self):
        # test code hint
        context = self.context
        csq = self.csq
        info = self.info
        info["csq_hint"] = sgd_hint
        test_bad1_sgd_function = """def sgd(x):
            return x > 3
        """

        form = {csq_name: test_bad1_sgd_function}
        ret = csq["handle_submission"](form, **info)

        assert "Our solution did not produce a value for" not in str(ret)
        assert "comparison threshold set too" in str(ret)

    def test_hints2(self):
        # test code hint (should not appear when answer is correct)
        context = self.context
        csq = self.csq
        info = self.info
        info["csq_hint"] = sgd_hint
        form = {csq_name: test_good_sgd_function}
        ret = csq["handle_submission"](form, **info)

        assert "Our solution did not produce a value for" not in str(ret)
        assert "comparison threshold set too" not in str(ret)
