"""Unit tests for the symbolic checker and its CAT-SOOP adapter."""

import importlib.util
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent


def load_module(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module("checker.py", "sympy_check_test_checker")


def score(function, submission, solution, **settings):
    return function(submission, solution, random_seed=8371, **settings)[0]


@pytest.mark.parametrize(
    "submission,solution",
    [
        ("x + x", "2*x"),
        ("sin(x)^2 + cos(x)^2", "1"),
        ("sqrt(1-sin(1-p)^2)", "cos(1-p)"),
        ("4 + 5*i", "4 + 5*sqrt(-1)"),
        ("exp(2*pi*i)", "1"),
    ],
)
def test_formula_accepts_equivalent_expressions(submission, solution):
    assert score(checker.sympy_formula_check, submission, solution) == 1.0


def test_formula_rejects_inequivalent_expression():
    assert score(checker.sympy_formula_check, "sin(x)", "cos(x)") == 0.0


def test_formula_reports_parse_error():
    result = checker.sympy_formula_check("sin(", "1")
    assert result[0] == 0.0
    assert "could not be parsed" in result[1]


def test_matrix_expression_and_shape_checking():
    assert (
        score(
            checker.sympy_formula_check,
            "[[2,0],[0,2]]/2",
            "[[1,0],[0,1]]",
        )
        == 1.0
    )
    assert (
        score(
            checker.sympy_formula_check,
            "[[1,0,0],[0,1,0],[0,0,1]]",
            "[[1,0],[0,1]]",
        )
        == 0.0
    )


def test_ordered_list_checking():
    assert score(checker.sympy_formula_check, "[XX, YZ+0]", "[XX,YZ]") == 1.0
    assert score(checker.sympy_formula_check, "[YZ,XX]", "[XX,YZ]") == 0.0


def test_alternate_answers_with_structured_and_legacy_options():
    assert (
        score(
            checker.sympy_formula_check,
            "x-1",
            "x+1",
            alt_answers=["x", "x-1"],
        )
        == 1.0
    )
    assert (
        score(
            checker.sympy_formula_check,
            "x-1",
            "x+1",
            options="altanswer='x-1'",
        )
        == 1.0
    )


def test_absolute_and_relative_tolerances():
    assert (
        score(
            checker.sympy_formula_check,
            "0.399",
            "0.4",
            tolerance=0.002,
        )
        == 1.0
    )
    assert (
        score(
            checker.sympy_formula_check,
            "98",
            "100",
            tolerance="3%",
        )
        == 1.0
    )
    assert (
        score(
            checker.sympy_formula_check,
            "95",
            "100",
            tolerance="3%",
        )
        == 0.0
    )


def test_explicit_sampling_range():
    assert (
        score(
            checker.sympy_formula_check,
            "(x+1)^2",
            "x^2+2*x+1",
            samples="x@-10:10#5",
        )
        == 1.0
    )


def test_only_symbolic_disables_algebraic_and_numerical_equivalence():
    assert (
        score(
            checker.sympy_formula_check,
            "(x+1)^2",
            "x^2+2*x+1",
            only_symbolic=True,
        )
        == 0.0
    )


@pytest.mark.parametrize("submission", ["none", "None", "empty"])
def test_check_none(submission):
    assert (
        score(
            checker.sympy_formula_check,
            submission,
            "None",
            check_none=True,
        )
        == 1.0
    )


def test_array_variable_encoding_and_checking():
    assert checker.array_var_to_str("X[i, j+2]") == "XOBiCOjPL2CB"
    assert (
        score(
            checker.array_var_check,
            "X[i,j] + X[j,i] - X[j,i]",
            "X[i,j]",
        )
        == 1.0
    )
    assert (
        score(
            checker.array_var_check,
            "X[i,j] + X[j,i]",
            "X[i,j]",
        )
        == 0.0
    )


def test_quantum_checker_accepts_reordered_kets_and_html_entities():
    solution = "a*|00> + a*exp(i*theta)*|01> + b*|11>"
    submission = "b*|11&gt; + a*|00&gt; + a*exp(I*theta)*|01&gt;"
    assert score(checker.sympy_check_quantum, submission, solution) == 1.0


def test_quantum_checker_rejects_wrong_amplitude():
    assert (
        score(
            checker.sympy_check_quantum,
            "a*|0> - b*|1>",
            "a*|0> + b*|1>",
        )
        == 0.0
    )


def test_quantum_global_phase_option():
    solution = "a*|0> + b*|1>"
    submission = "i*(a*|0> + b*|1>)"
    assert score(checker.sympy_check_quantum, submission, solution) == 0.0
    assert (
        score(
            checker.sympy_check_quantum,
            submission,
            solution,
            phase_ambiguity=True,
        )
        == 1.0
    )


def test_legacy_phase_ambiguity_flag_without_equals():
    assert (
        score(
            checker.sympy_check_quantum,
            "-(a*|0> + b*|1>)",
            "a*|0> + b*|1>",
            options="phase_ambiguity",
        )
        == 1.0
    )


def test_public_functions_follow_catsoop_convention():
    for function in (
        checker.sympy_formula_check,
        checker.array_var_check,
        checker.sympy_check_quantum,
    ):
        result = function("1", "1")
        assert result == (1.0, "")


class FakeTutor:
    """Small part of the tutor API needed to load the course question type."""

    def qtype_inherit(self, context, qtype):
        assert qtype == "smallbox"
        context["defaults"] = {
            "csq_soln": "",
            "csq_npoints": 1,
            "csq_show_check": False,
        }
        context["smallbox_render"] = lambda last_log, **info: "SMALLBOX"

    def question(self, context, qtype):
        assert qtype == "smallbox"
        return ({"render_html": context["smallbox_render"]}, {})


def load_qtype():
    """Execute the qtype after applying CAT-SOOP's two source rewrites."""

    source = (HERE / "sympy_check.py").read_text()
    source = source.replace(
        'tutor.qtype_inherit("smallbox")',
        'tutor.qtype_inherit(globals(), "smallbox")',
    )
    source = source.replace(
        'tutor.question("smallbox")',
        'tutor.question(globals(), "smallbox")',
    )
    environment = {
        "tutor": FakeTutor(),
        "cs_local_python_import": lambda filename, name=None: load_module(
            filename, name or filename
        ),
    }
    exec(compile(source, str(HERE / "sympy_check.py"), "exec"), environment)
    return environment


def qtype_info(qtype, **updates):
    info = dict(qtype["defaults"])
    info.update(
        {
            "csq_name": "symbolic_test",
            "csq_soln": "2*x",
            "csq_show_check": False,
        }
    )
    info.update(updates)
    return info


def test_qtype_default_checker_needs_no_author_function():
    qtype = load_qtype()
    result = qtype["handle_submission"](
        {"symbolic_test": {"data": "x+x"}},
        **qtype_info(qtype),
    )
    assert result == {"score": 1.0, "msg": ""}


def test_qtype_declarative_quantum_selector():
    qtype = load_qtype()
    result = qtype["handle_submission"](
        {"symbolic_test": {"data": "b*|1> + a*|0>"}},
        **qtype_info(
            qtype,
            csq_soln="a*|0>+b*|1>",
            csq_checker="quantum",
        ),
    )
    assert result["score"] == 1.0


def test_qtype_declarative_array_selector_and_rendering():
    qtype = load_qtype()
    result = qtype["handle_submission"](
        {"symbolic_test": {"data": "A[i]+B[j]-B[j]"}},
        **qtype_info(qtype, csq_soln="A[i]", csq_checker="array"),
    )
    assert result["score"] == 1.0
    assert qtype["render_html"]({}, **qtype_info(qtype)) == "SMALLBOX"
