from unittest import mock

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


class Test_Pythonic_Rendering(CATSOOPTest):
    def setUp(self):
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context

        question, info = context["tutor"].question(context, "pythonic")
        info["csq_name"] = QUESTION_NAME
        info["cs_cross_image"] = "FILE_CROSS_IMAGE"
        info["cs_check_image"] = "FILE_CHECK_IMAGE"
        question["pythoncode"]["get_sandbox"] = lambda info: None

        self.question = question
        self.info = info

    def render(self, last_log=None, **updates):
        info = dict(self.info)
        info.update(updates)
        return self.question["render_html"](last_log, **info)

    def test_rows_do_not_implicitly_select_multiline_renderer(self):
        rendered = self.render(csq_rows=6)

        assert 'type="text"' in rendered
        assert "<textarea" not in rendered
        assert "embedded_ace_code" not in rendered

    def test_explicit_ace_renderer_restores_response_and_uses_rows(self):
        rendered = self.render(
            {QUESTION_NAME: {"data": "(\n1 + 2\n)"}},
            csq_renderer="ace",
            csq_rows=6,
        )

        assert "embedded_ace_code" in rendered
        assert "1 + 2" in rendered
        assert 'name="%s"' % QUESTION_NAME in rendered
        assert "120px" in rendered

    def test_explicit_ace_renderer_starts_blank(self):
        rendered = self.render(csq_renderer="ace")

        assert "pass  # Your code here" not in rendered

    def test_explicit_textarea_renderer_restores_and_escapes_response(self):
        rendered = self.render(
            {QUESTION_NAME: {"data": "(\nvalue < 10\n)"}},
            csq_renderer="textarea",
            csq_rows=6,
        )

        assert '<textarea rows="6"' in rendered
        assert "value &lt; 10" in rendered
        assert 'name="%s"' % QUESTION_NAME in rendered

    def test_bigbox_renderer_remains_supported(self):
        rendered = self.render(csq_renderer="bigbox", csq_rows=4)

        assert '<textarea rows="4"' in rendered

    def test_invalid_renderer_is_safe_and_visible(self):
        rendered = self.render(csq_renderer="<script>alert(1)</script>")

        assert "Invalid <tt>pythonic</tt> renderer" in rendered
        assert "&lt;script&gt;" in rendered
        assert "<script>" not in rendered

    def test_multiline_expression_uses_existing_submission_contract(self):
        info = dict(self.info)
        info.update(
            {
                "csq_renderer": "ace",
                "csq_soln": 3,
                "sandbox_run_code": lambda *args, **kwargs: {
                    "err": "",
                    "info": {"result": 3},
                },
            }
        )

        result = self.question["handle_submission"](
            {QUESTION_NAME: {"data": "(\n1 + 2\n)"}},
            **info,
        )

        assert result["score"] == 1.0

    def test_multiline_expression_uses_existing_format_check(self):
        info = dict(self.info)
        info["sandbox_run_code"] = lambda *args, **kwargs: {"err": ""}

        result = self.question["handle_check"](
            {QUESTION_NAME: {"data": "(\n1 + 2\n)"}},
            **info,
        )

        assert result == "Your submission is properly formatted."

    def test_raw_solution_display_defaults_to_repr(self):
        rendered = self.question["answer_display"](
            **self.info,
            csq_mode="raw",
            csq_soln="formatted value",
        )

        assert rendered == "<p><b>Solution:</b> <tt>'formatted value'</tt><p>"

    def test_formatted_solution_display_uses_str_and_preserves_styling(self):
        rendered = self.question["answer_display"](
            **self.info,
            csq_mode="raw",
            csq_output_mode="formatted",
            csq_soln="formatted value",
        )

        assert rendered == "<p><b>Solution:</b> <tt>formatted value</tt><p>"

    def test_invalid_output_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid csq_output_mode"):
            self.question["answer_display"](
                **self.info,
                csq_output_mode="unknown",
            )

    def test_failed_submission_log_excludes_student_and_exception_text(self):
        info = dict(self.info)
        info["csq_soln"] = None

        def failed_sandbox(*args, **kwargs):
            raise RuntimeError("PRIVATE EXCEPTION DETAILS")

        info["sandbox_run_code"] = failed_sandbox
        private_submission = "PRIVATE_STUDENT_RESPONSE()"

        with mock.patch.object(self.question["LOGGER"], "info") as logger:
            result = self.question["handle_submission"](
                {QUESTION_NAME: {"data": private_submission}},
                **info,
            )

        assert result["score"] == 0.0
        logger.assert_called_once()
        logged = repr(logger.call_args)
        assert QUESTION_NAME in logged
        assert "RuntimeError" in logged
        assert private_submission not in logged
        assert "PRIVATE EXCEPTION DETAILS" not in logged
