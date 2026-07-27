import ast
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

    def literal_sandbox(self, calls):
        def sandbox_run_code(info, code, options, result_as_string=False):
            expression = code.rsplit("_catsoop_answer =", 1)[1].strip()
            value = ast.literal_eval(expression)
            calls.append(
                {
                    "expression": expression,
                    "result_as_string": result_as_string,
                    "value": value,
                }
            )
            result = repr(value) if result_as_string else value
            return {"err": "", "info": {"result": result}}

        return sandbox_run_code

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

    def test_multi_prompt_renderer_labels_and_restores_each_field(self):
        rendered = self.render(
            {
                "__test_question_0000": {
                    "data": '  Alice "A" & <admin>  ',
                    "type": "text",
                },
            },
            csq_prompts=["First value:", "Second value:"],
        )

        assert "<fieldset>" in rendered
        assert 'for="__test_question_0000"' in rendered
        assert 'for="__test_question_0001"' in rendered
        assert "First value:" in rendered
        assert "Second value:" in rendered
        assert 'value="  Alice &quot;A&quot; &amp; &lt;admin&gt;  "' in rendered
        assert 'value="" name="__test_question_0001"' in rendered
        assert (
            'aria-labelledby="catsoop_prompt_test_question '
            '__test_question_0000_prompt"' in rendered
        )
        with mock.patch.object(self.question["LOGGER"], "error") as logger:
            self.render(
                {"__test_question_0000": {"data": "private response"}},
                csq_prompts=["First value:"],
            )
        logger.assert_not_called()

    def test_multi_prompt_raw_grading_receives_only_field_data(self):
        sandbox_calls = []
        input_checks = []
        checker_calls = []
        expected = {"0": "alpha", "1": "beta"}
        info = dict(self.info)
        info.update(
            {
                "csq_prompts": ["First:", "Second:"],
                "csq_soln": expected,
                "csq_input_check": lambda submission: input_checks.append(
                    ast.literal_eval(submission)
                ),
                "csq_check_function": lambda submission, solution: checker_calls.append(
                    (submission, solution)
                )
                or submission == solution,
                "sandbox_run_code": self.literal_sandbox(sandbox_calls),
            }
        )

        result = self.question["handle_submission"](
            {
                "__test_question_0000": {"data": " alpha ", "type": "text"},
                "__test_question_0001": {"data": " beta ", "type": "text"},
            },
            **info,
        )

        assert result["score"] == 1.0
        assert input_checks == [expected]
        assert checker_calls == [(expected, expected)]
        assert sandbox_calls == [
            {
                "expression": repr(expected),
                "result_as_string": False,
                "value": expected,
            }
        ]

    def test_multi_prompt_non_raw_grading_uses_literal_result_contract(self):
        sandbox_calls = []
        checker_calls = []
        expected = {"0": "red", "1": "blue"}
        info = dict(self.info)
        info.update(
            {
                "csq_prompts": ["First:", "Second:"],
                "csq_mode": "string",
                "csq_soln": repr(expected),
                "csq_check_function": lambda submission, solution: checker_calls.append(
                    (submission, solution)
                )
                or submission == solution,
                "sandbox_run_code": self.literal_sandbox(sandbox_calls),
            }
        )

        result = self.question["handle_submission"](
            {
                "__test_question_0000": {"data": "red"},
                "__test_question_0001": {"data": "blue"},
            },
            **info,
        )

        assert result["score"] == 1.0
        assert checker_calls == [(expected, expected)]
        assert [call["result_as_string"] for call in sandbox_calls] == [True, True]

    def test_multi_prompt_uses_existing_format_check(self):
        sandbox = mock.Mock(return_value={"err": ""})
        info = dict(self.info)
        info.update(
            {
                "csq_prompts": ["First:", "Second:"],
                "sandbox_run_code": sandbox,
            }
        )

        result = self.question["handle_check"](
            {
                "__test_question_0000": {"data": "alpha"},
                "__test_question_0001": {"data": "beta"},
            },
            **info,
        )

        assert result == "Your submission is properly formatted."
        submitted_code = sandbox.call_args.args[1]
        assert repr({"0": "alpha", "1": "beta"}) in submitted_code

    def test_multi_prompt_blank_or_missing_field_is_invalid(self):
        sandbox = mock.Mock()
        info = dict(self.info)
        info.update(
            {
                "csq_prompts": ["First:", "Second:"],
                "csq_soln": {"0": "alpha", "1": "beta"},
                "sandbox_run_code": sandbox,
            }
        )

        result = self.question["handle_submission"](
            {"__test_question_0000": {"data": "alpha"}},
            **info,
        )

        assert result["score"] == 0.0
        assert "valid Python expression" in result["msg"]
        sandbox.assert_not_called()

    def test_multi_prompt_configuration_is_validated_up_front(self):
        invalid_prompts = [
            "not a list",
            [],
            ["valid", 123],
        ]
        for prompts in invalid_prompts:
            with self.subTest(prompts=prompts):
                with self.assertRaisesRegex(ValueError, "csq_prompts"):
                    self.render(csq_prompts=prompts)

        with self.assertRaisesRegex(ValueError, "requires csq_prompts"):
            self.question["answer_display"](
                **self.info,
                csq_solns=["orphan"],
            )
        with self.assertRaisesRegex(ValueError, "csq_solns must be a list"):
            self.question["answer_display"](
                **self.info,
                csq_prompts=["First:"],
                csq_solns="not a list",
            )
        with self.assertRaisesRegex(ValueError, "same length"):
            self.question["answer_display"](
                **self.info,
                csq_prompts=["First:", "Second:"],
                csq_solns=["only one"],
            )

    def test_multi_prompt_solution_display_is_formatted_and_styled(self):
        rendered = self.question["answer_display"](
            **self.info,
            csq_mode="raw",
            csq_prompts=["First:", "Second:"],
            csq_solns=["alpha", 2],
        )

        assert "<p><b>Solution:</b></p>" in rendered
        assert '<th scope="row">First:</th>' in rendered
        assert "First:" in rendered
        assert "Second:" in rendered
        assert "<tt>'alpha'</tt>" in rendered
        assert "<tt>2</tt>" in rendered

        formatted = self.question["answer_display"](
            **self.info,
            csq_mode="raw",
            csq_output_mode="formatted",
            csq_prompts=["First:"],
            csq_solns=["alpha"],
        )
        assert "<tt>alpha</tt>" in formatted
        assert "<tt>'alpha'</tt>" not in formatted
