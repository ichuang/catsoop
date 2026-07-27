"""CAT-SOOP question type for symbolic mathematical answers.

Minimal authoring example::

    <question sympy_check>
    csq_soln = "sin(x)^2 + cos(x)^2"
    csq_name = "identity"
    </question>

The default checker is ``sympy_formula_check``.  Set ``csq_checker`` to
``"array"`` or ``"quantum"`` for the other bundled checkers.  All checkers use
the CAT-SOOP argument order and return format, so no ``edx2catsoop.check``
wrapper is needed.

Question settings
-----------------

``csq_checker``
    ``"formula"`` (default), ``"array"``, or ``"quantum"``.  The full public
    function names are accepted as aliases.
``csq_alt_answers``
    A string or list of additional answers to accept.
``csq_tolerance``
    Absolute number or relative percentage string, such as ``"2%"``.
``csq_samples``
    Sampling ranges in legacy form: ``"x,y@-1,-2:1,2#30"``.
``csq_only_symbolic``
    Disable numerical sampling and require structural SymPy equality.
``csq_check_none``
    Accept the words ``none`` or ``empty``.
``csq_phase_ambiguity``
    In quantum mode, ignore a physically irrelevant global phase.
``csq_num_trials``
    Number of numerical samples (default 20).
``csq_options``
    Optional compatibility string, e.g.
    ``"altanswer='2*x'!tolerance='1%'"``.  First-class settings above take
    precedence when supplied.

The module also exports ``sympy_formula_check``, ``array_var_check``, and
``sympy_check_quantum`` as direct CAT-SOOP check functions.
"""

import collections.abc
import html
import traceback


_sympy_check_local_import = cs_local_python_import
tutor.qtype_inherit("smallbox")
smallbox, _ = tutor.question("smallbox")

_checker_module = _sympy_check_local_import("checker.py", "_catsoop_sympy_check")

SympyFormulaChecker = _checker_module.SympyFormulaChecker
array_var_to_str = _checker_module.array_var_to_str
sympy_formula_check = _checker_module.sympy_formula_check
array_var_check = _checker_module.array_var_check
sympy_check_quantum = _checker_module.sympy_check_quantum
get_checker = _checker_module.get_checker


defaults.update(
    {
        "csq_soln": "",
        "csq_check_function": sympy_formula_check,
        "csq_checker": None,
        "csq_options": None,
        "csq_alt_answers": None,
        "csq_tolerance": None,
        "csq_samples": None,
        "csq_only_symbolic": None,
        "csq_check_none": None,
        "csq_phase_ambiguity": None,
        "csq_num_trials": None,
        "csq_force_list_to_matrix": False,
        "csq_extra_symbols": None,
        "csq_random_seed": None,
        "csq_input_check": lambda submission: None,
        "csq_msg_function": lambda submission, solution: "",
        "csq_show_check": False,
        "csq_size": 50,
    }
)

allow_save = False
checktext = "Check Syntax"


def _selected_checker(info):
    selected = info.get("csq_checker")
    if selected:
        if callable(selected):
            return selected
        return get_checker(str(selected))
    checker = info["csq_check_function"]
    if isinstance(checker, str):
        return get_checker(checker)
    return checker


def _checker_settings(info):
    settings = {
        "options": info.get("csq_options"),
        "alt_answers": info.get("csq_alt_answers"),
        "tolerance": info.get("csq_tolerance"),
        "samples": info.get("csq_samples"),
        "only_symbolic": info.get("csq_only_symbolic"),
        "check_none": info.get("csq_check_none"),
        "phase_ambiguity": info.get("csq_phase_ambiguity"),
        "num_trials": info.get("csq_num_trials"),
        "force_list_to_matrix": info.get("csq_force_list_to_matrix", False),
        "extra_symbols": info.get("csq_extra_symbols"),
        "random_seed": info.get("csq_random_seed"),
    }
    return {
        key: value
        for key, value in settings.items()
        if value is not None and not (key == "force_list_to_matrix" and not value)
    }


def _result_parts(result, submission, solution, info):
    if isinstance(result, collections.abc.Mapping):
        score = result.get("score", result.get("ok", False))
        message = result.get("msg", result.get("message", ""))
    elif (
        isinstance(result, collections.abc.Sequence)
        and not isinstance(result, (str, bytes))
    ):
        score, message = result
    else:
        score = result
        message = ""

    if not message:
        message_function = info["csq_msg_function"]
        try:
            message = message_function(submission, solution)
        except TypeError:
            message = message_function(submission)
    return float(score), message or ""


def handle_submission(submissions, **info):
    """Grade a raw symbolic string without evaluating it as Python."""

    submission = submissions[info["csq_name"]]["data"].strip()
    solution = info["csq_soln"]
    if not submission:
        return {
            "score": 0.0,
            "msg": (
                '<font color="red">Please enter a mathematical expression.</font>'
            ),
        }

    input_message = info["csq_input_check"](submission)
    if input_message is not None:
        return {
            "score": 0.0,
            "msg": '<font color="red">%s</font>' % html.escape(str(input_message)),
        }

    checker = _selected_checker(info)
    try:
        if checker in {
            sympy_formula_check,
            array_var_check,
            sympy_check_quantum,
        }:
            result = checker(submission, solution, **_checker_settings(info))
        else:
            # Custom CAT-SOOP checkers retain the normal two-argument contract.
            result = checker(submission, solution)
        score, message = _result_parts(result, submission, solution, info)
    except Exception:
        errors = info.get("csm_errors")
        if errors is not None:
            detail = errors.html_format(
                errors.clear_info(info, traceback.format_exc())
            )
        else:
            detail = html.escape(traceback.format_exc())
        score = 0.0
        message = (
            '<font color="red">An error occurred in the symbolic checker: '
            "<pre>%s</pre></font>" % detail
        )

    if info["csq_show_check"]:
        if score == 1.0:
            icon = '<img src="%s" alt="Correct" /><br/>' % info["cs_check_image"]
        elif score == 0.0:
            icon = '<img src="%s" alt="Incorrect" /><br/>' % info["cs_cross_image"]
        else:
            icon = ""
        message = icon + message
    return {"score": score, "msg": message}


def _parser_for(info):
    checker = _selected_checker(info)
    quantum = checker is sympy_check_quantum
    array_variables = checker is array_var_check
    return SympyFormulaChecker(
        quantum=quantum,
        array_variables=array_variables,
        force_list_to_matrix=info.get("csq_force_list_to_matrix", False),
        extra_symbols=info.get("csq_extra_symbols"),
    )


def handle_check(submissions, **info):
    """Render the student's parsed expression without grading it."""

    submission = submissions[info["csq_name"]]["data"].strip()
    if not submission:
        return '<font color="red">Please enter a mathematical expression.</font>'
    try:
        latex = _parser_for(info).latex(submission)
        output = (
            '<div id="sympy-preview-%s">Your entry was parsed as:'
            "<displaymath>%s</displaymath></div>" % (info["csq_name"], latex)
        )
        return info["csm_language"].source_transform_string(info, output)
    except Exception as exc:
        return (
            '<font color="red">Your input could not be parsed: %s</font>'
            % html.escape(str(exc))
        )


def render_html(last_log, **info):
    """Use the standard CAT-SOOP one-line input control."""

    return smallbox["render_html"](last_log, **info)


def answer_display(**info):
    """Display both the source form and rendered form of the solution."""

    source = str(info["csq_soln"])
    try:
        rendered = _parser_for(info).latex(source)
        output = (
            "<p><b>Solution:</b> <tt>%s</tt></p>"
            '<div id="sympy-solution-%s"><displaymath>%s</displaymath></div>'
            % (html.escape(source), info["csq_name"], rendered)
        )
        return info["csm_language"].source_transform_string(info, output)
    except Exception:
        return "<p><b>Solution:</b> <tt>%s</tt></p>" % html.escape(source)
