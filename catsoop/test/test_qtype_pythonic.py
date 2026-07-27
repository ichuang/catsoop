from .. import loader
from ..test import CATSOOPTest

QUESTION_NAME = "test_question"

NON_RAW_RESULTS = [
    ("none", "None", None),
    ("boolean", "True", True),
    ("integer", "1729", 1729),
    ("float", "3.125", 3.125),
    ("complex", "2 + 3j", 2 + 3j),
    ("string", "'catsoop'", "catsoop"),
    ("bytes", "b'catsoop'", b"catsoop"),
    ("list", "[1, 'two']", [1, "two"]),
    ("tuple", "(1, 'two')", (1, "two")),
    ("dictionary", "{'one': 1}", {"one": 1}),
    ("set", "{1, 2}", {1, 2}),
    ("empty set", "set()", set()),
]


class Test_Pythonic(CATSOOPTest):
    def setUp(self):
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context

        question, info = context["tutor"].question(
            context,
            "pythonic",
            csq_mode="string",
        )
        info["csm_loader"] = context["csm_loader"]
        info["csq_name"] = QUESTION_NAME
        info["cs_cross_image"] = "FILE_CROSS_IMAGE"
        info["cs_check_image"] = "FILE_CHECK_IMAGE"
        question["pythoncode"]["get_sandbox"] = lambda info: None

        self.question = question
        self.info = info

    def set_sandbox_results(self, info, *serialized_results):
        serialized = iter(serialized_results)

        def sandbox_run_code(*args, **kwargs):
            return {"info": {"result": next(serialized)}}

        info["sandbox_run_code"] = sandbox_run_code

    def test_non_raw_literal_result_types(self):
        for result_type, expression, expected in NON_RAW_RESULTS:
            with self.subTest(result_type=result_type):
                seen = []
                info = dict(self.info)
                info["csq_soln"] = expression
                self.set_sandbox_results(info, repr(expected), repr(expected))
                info["csq_check_function"] = lambda submission, solution: seen.append(
                    (submission, solution)
                ) or (type(submission) is type(solution) and submission == solution)

                result = self.question["handle_submission"](
                    {QUESTION_NAME: {"data": expression}},
                    **info,
                )

                assert result["score"] == 1.0
                assert seen == [(expected, expected)]

    def test_non_raw_submission_repr_is_not_evaluated_in_server_context(self):
        calls = []
        info = dict(self.info)
        info["csq_soln"] = "None"
        self.set_sandbox_results(info, "None", "server_function()")
        info["server_function"] = lambda: calls.append(True)

        result = self.question["handle_submission"](
            {QUESTION_NAME: {"data": "StudentResult()"}},
            **info,
        )

        assert result["score"] == 0.0
        assert calls == []
