"""Symbolic checkers used by the :mod:`sympy_check` CAT-SOOP question type.

The public functions in this module follow CAT-SOOP's checker convention:
the student's submission comes first, the instructor's solution comes second,
and the return value is ``(score, message)``.  They can therefore be assigned
directly to ``csq_check_function``; ``edx2catsoop.check`` is not needed.

Public checkers
---------------

``sympy_formula_check(submission, solution, ...)``
    Compare scalars, expressions, lists, and matrices symbolically, falling
    back to numerical sampling when SymPy cannot prove equality.

``array_var_check(submission, solution, ...)``
    As above, but treat indexed names such as ``A[i,j+1]`` as indivisible
    symbolic variables.

``sympy_check_quantum(submission, solution, ...)``
    As above, with support for ket notation such as ``a*|00> + b*|11>``.

All three accept either the legacy ``options`` string used by the 8.371
checker or explicit keyword arguments.  Explicit arguments take precedence.
The supported settings are:

``alt_answers``
    A string or iterable of additional correct answers.
``tolerance``
    An absolute tolerance (for example ``0.001``) or a relative percentage
    (for example ``"2%"``).  The default is ``"0.1%"``.
``samples``
    Legacy sampling specification, e.g. ``"x,y@-1,-2:1,2#30"``.
``only_symbolic``
    If true, require SymPy's parsed expressions to be structurally equal and
    do not use numerical sampling.
``check_none``
    Accept ``none`` or ``empty`` instead of checking a formula.
``phase_ambiguity``
    For quantum states, accept answers differing only by a global phase.
``num_trials``
    Number of random trials when ``samples`` does not specify a count.

The legacy options string separates settings with ``!``:
``"altanswer='2*x'!tolerance='1%'!only_symbolic=0"``.
"""

from __future__ import annotations

import ast
import html
import math
import numbers
import random
import re
from typing import Any, Iterable, Mapping

import sympy
from sympy.physics.quantum import represent
from sympy.physics.quantum.qubit import Qubit


DEFAULT_TOLERANCE = "0.1%"
DEFAULT_NUM_TRIALS = 20


class CheckResult:
    """Internal result with a CAT-SOOP conversion helper."""

    def __init__(self, ok: bool, message: str = ""):
        self.ok = bool(ok)
        self.message = message

    def catsoop(self) -> tuple[float, str]:
        return (1.0 if self.ok else 0.0, self.message)


def _literal(value: str) -> Any:
    """Parse a legacy option value without executing arbitrary Python."""

    value = value.strip()
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        lowered = value.casefold()
        if lowered in {"true", "yes", "on"}:
            return True
        if lowered in {"false", "no", "off"}:
            return False
        if lowered in {"none", "null"}:
            return None
        try:
            return float(value)
        except ValueError:
            return value


def parse_options(options: str | Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a normalized dictionary from legacy or structured options.

    The old checker used ``eval`` on every option.  This implementation uses
    ``ast.literal_eval`` instead, so an answer-checking option cannot execute
    arbitrary Python.
    """

    if options is None:
        return {}
    if isinstance(options, Mapping):
        return dict(options)
    if not isinstance(options, str):
        raise TypeError("options must be a string, mapping, or None")

    aliases = {
        "altanswer": "alt_answers",
        "altanswers": "alt_answers",
        "check_none": "check_none",
        "only_symbolic": "only_symbolic",
        "phase_ambiguity": "phase_ambiguity",
        "tolerance": "tolerance",
        "samples": "samples",
        "num_trials": "num_trials",
        "nsamples": "num_trials",
    }
    parsed: dict[str, Any] = {}
    for item in filter(None, (part.strip() for part in options.split("!"))):
        if "=" in item:
            key, value = item.split("=", 1)
            key = aliases.get(key.strip(), key.strip())
            value = _literal(value)
            if key == "alt_answers" and key in parsed:
                current = parsed[key]
                if not isinstance(current, list):
                    current = [current]
                current.append(value)
                value = current
            parsed[key] = value
        else:
            key = aliases.get(item, item)
            parsed[key] = True
    return parsed


def _merge_options(
    options: str | Mapping[str, Any] | None, explicit: Mapping[str, Any]
) -> dict[str, Any]:
    out = parse_options(options)
    out.update({key: value for key, value in explicit.items() if value is not None})
    return out


class _MatrixLiteralTransformer(ast.NodeTransformer):
    """Wrap nested list literals in ``Matrix(...)`` before SymPy parsing."""

    def __init__(self, force_flat: bool = False):
        self.force_flat = force_flat

    def visit_List(self, node: ast.List) -> ast.AST:
        node = self.generic_visit(node)
        nested = any(isinstance(value, ast.List) for value in node.elts)
        if nested or self.force_flat:
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id="Matrix", ctx=ast.Load()),
                    args=[node],
                    keywords=[],
                ),
                node,
            )
        return node


def _prepare_matrix_literals(source: str, force_flat: bool = False) -> str:
    """Convert Python-style matrix literals in a larger expression."""

    try:
        tree = ast.parse(source, mode="eval")
        tree = _MatrixLiteralTransformer(force_flat=force_flat).visit(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except (SyntaxError, ValueError):
        # Let sympify produce the useful parse error.
        return source


_INDEX_RE = re.compile(r"\[([^\[\]]+)\]")


def array_var_to_str(expression: str) -> str:
    """Encode array subscripts as legal, unique SymPy symbol names.

    For example, ``X[i, j+2]`` becomes ``XOBiCOjPL2CB``.  This deliberately
    treats the entire indexed expression as a variable, rather than applying
    Python/SymPy indexing semantics.
    """

    expression = expression.replace(" ", "")

    def encode(match: re.Match[str]) -> str:
        value = match.group(1)
        for old, new in (
            ("+", "PL"),
            ("-", "MI"),
            ("*", "TI"),
            ("/", "DI"),
            (",", "CO"),
            ("(", "OP"),
            (")", "CP"),
        ):
            value = value.replace(old, new)
        return "OB%sCB" % value

    previous = None
    while previous != expression:
        previous = expression
        expression = _INDEX_RE.sub(encode, expression)
    return expression


class SympyFormulaChecker:
    """Parse and compare symbolic answers using SymPy.

    This class is intentionally independent of CAT-SOOP.  The three public
    checker functions below provide the CAT-SOOP calling convention.
    """

    def __init__(
        self,
        *,
        extra_symbols: Mapping[str, Any] | None = None,
        quantum: bool = False,
        array_variables: bool = False,
        force_list_to_matrix: bool = False,
        random_seed: int | None = None,
    ):
        self.quantum = quantum
        self.array_variables = array_variables
        self.force_list_to_matrix = force_list_to_matrix
        self.random = random.Random(random_seed)

        p = sympy.Symbol("p", real=True, positive=True)
        g = sympy.Symbol("g", real=True)
        self.locals: dict[str, Any] = {
            "p": p,
            "g": g,
            "e": sympy.E,
            "pi": sympy.pi,
            "i": sympy.I,
            "I": sympy.I,
            "X": sympy.Matrix([[0, 1], [1, 0]]),
            "Y": sympy.Matrix([[0, -sympy.I], [sympy.I, 0]]),
            "Z": sympy.Matrix([[1, 0], [0, -1]]),
            "ZZ": sympy.Symbol("ZZ"),
            "N": sympy.Symbol("N"),
            "E": sympy.Symbol("E"),
            "gamma": sympy.Symbol("gamma"),
            "beta": sympy.Symbol("beta"),
            "Matrix": sympy.Matrix,
        }
        if quantum:
            self.locals.update(
                {
                    "Qubit": Qubit,
                    "Ket": sympy.physics.quantum.state.Ket,
                    "bit": sympy.Function("bit"),
                }
            )
        if extra_symbols:
            self.locals.update(extra_symbols)

    def preprocess(self, expression: str) -> str:
        """Normalize HTML, powers, array variables, kets, and matrices."""

        if not isinstance(expression, str):
            expression = str(expression)
        expression = html.unescape(expression).strip()
        if self.array_variables:
            expression = array_var_to_str(expression)
        if self.quantum:
            expression = re.sub(
                r"\|([01]+?)\s*(?:>|⟩)",
                lambda match: "Qubit(%r)" % match.group(1),
                expression,
                flags=re.IGNORECASE,
            )
        expression = expression.replace("^", "**")
        return _prepare_matrix_literals(
            expression, force_flat=self.force_list_to_matrix
        )

    def parse_input(self, expression: str) -> Any:
        """Parse a student's or author's expression into a SymPy object."""

        prepared = self.preprocess(expression)
        return sympy.sympify(prepared, locals=self.locals)

    @staticmethod
    def _is_matrix(value: Any) -> bool:
        return isinstance(value, sympy.MatrixBase)

    @classmethod
    def _sequence_equal(cls, expected: Any, given: Any) -> bool | None:
        if isinstance(expected, (list, tuple)) or isinstance(given, (list, tuple)):
            if not (
                isinstance(expected, (list, tuple))
                and isinstance(given, (list, tuple))
                and len(expected) == len(given)
            ):
                return False
            return all(cls._symbolically_equal(a, b) for a, b in zip(expected, given))
        return None

    @classmethod
    def _symbolically_equal(cls, expected: Any, given: Any) -> bool:
        seq_result = cls._sequence_equal(expected, given)
        if seq_result is not None:
            return seq_result
        if cls._is_matrix(expected) or cls._is_matrix(given):
            if not (cls._is_matrix(expected) and cls._is_matrix(given)):
                return False
            if expected.shape != given.shape:
                return False
            return all(
                sympy.simplify(a - b) == 0 for a, b in zip(expected, given)
            )
        if expected == given:
            return True
        try:
            difference = sympy.simplify(expected - given)
            return difference == 0
        except (AttributeError, TypeError, ValueError):
            return False

    @classmethod
    def _free_symbols(cls, value: Any) -> set[sympy.Symbol]:
        if isinstance(value, (list, tuple)):
            out: set[sympy.Symbol] = set()
            for element in value:
                out.update(cls._free_symbols(element))
            return out
        if cls._is_matrix(value):
            out: set[sympy.Symbol] = set()
            for element in value:
                out.update(getattr(element, "free_symbols", set()))
            return out
        return set(getattr(value, "free_symbols", set()))

    @staticmethod
    def _parse_sample_atom(value: str) -> complex | float:
        value = value.strip()
        if "j" in value.casefold():
            return complex(value)
        return float(value)

    def _sampling_plan(
        self,
        expected: Any,
        given: Any,
        samples: str | None,
        num_trials: int,
    ) -> tuple[dict[str, tuple[complex | float, complex | float]], int]:
        symbols = self._free_symbols(expected) | self._free_symbols(given)
        names = sorted({str(symbol) for symbol in symbols})
        if samples is None:
            return ({name: (0.001, 0.999) for name in names}, int(num_trials))

        try:
            variables_text, values_text = samples.split("@", 1)
            ranges_text, count_text = values_text.rsplit("#", 1)
            lower_text, upper_text = ranges_text.split(":", 1)
            variables = [part.strip() for part in variables_text.split(",")]
            lowers = [
                self._parse_sample_atom(part) for part in lower_text.split(",")
            ]
            uppers = [
                self._parse_sample_atom(part) for part in upper_text.split(",")
            ]
            if not (len(variables) == len(lowers) == len(uppers)):
                raise ValueError("variables and bounds have different lengths")
            ranges = dict(zip(variables, zip(lowers, uppers)))
            missing = set(names) - set(ranges)
            if missing:
                raise ValueError(
                    "no sampling range was supplied for %s"
                    % ", ".join(sorted(missing))
                )
            return ranges, int(count_text)
        except Exception as exc:
            raise ValueError("bad samples specification %r: %s" % (samples, exc))

    @staticmethod
    def _magnitude(value: Any) -> float:
        if isinstance(value, (list, tuple)):
            return math.sqrt(sum(SympyFormulaChecker._magnitude(x) ** 2 for x in value))
        if isinstance(value, sympy.MatrixBase):
            return float(abs(complex(value.norm().evalf())))
        return abs(complex(sympy.N(value)))

    @staticmethod
    def _tolerance_limit(expected: Any, given: Any, tolerance: Any) -> float:
        if tolerance is None:
            tolerance = DEFAULT_TOLERANCE
        if isinstance(tolerance, str) and tolerance.strip().endswith("%"):
            relative = float(sympy.N(sympy.sympify(tolerance.strip()[:-1]))) / 100
            scale = max(
                SympyFormulaChecker._magnitude(expected),
                SympyFormulaChecker._magnitude(given),
                1e-300,
            )
            return relative * scale
        if isinstance(tolerance, numbers.Number):
            return float(tolerance)
        return float(sympy.N(sympy.sympify(str(tolerance))))

    @classmethod
    def _phase_aligned_distance(cls, expected: Any, given: Any) -> float | None:
        if not (cls._is_matrix(expected) and cls._is_matrix(given)):
            return None
        if expected.shape != given.shape:
            return math.inf
        expected_values = [complex(sympy.N(value)) for value in expected]
        given_values = [complex(sympy.N(value)) for value in given]
        norm_expected = math.sqrt(sum(abs(value) ** 2 for value in expected_values))
        norm_given = math.sqrt(sum(abs(value) ** 2 for value in given_values))
        if norm_expected == 0 or norm_given == 0:
            return 0.0 if norm_expected == norm_given else math.inf
        inner = sum(
            a.conjugate() * b for a, b in zip(expected_values, given_values)
        )
        if abs(inner) == 0:
            return math.inf
        phase = inner / abs(inner)
        aligned = [
            b - phase * a for a, b in zip(expected_values, given_values)
        ]
        phase_distance = math.sqrt(sum(abs(value) ** 2 for value in aligned))
        return max(phase_distance, abs(norm_expected - norm_given))

    @classmethod
    def _numerical_distance(
        cls, expected: Any, given: Any, phase_ambiguity: bool
    ) -> float:
        if phase_ambiguity:
            phase_distance = cls._phase_aligned_distance(expected, given)
            if phase_distance is not None:
                return phase_distance
        if isinstance(expected, (list, tuple)) or isinstance(given, (list, tuple)):
            if not (
                isinstance(expected, (list, tuple))
                and isinstance(given, (list, tuple))
                and len(expected) == len(given)
            ):
                return math.inf
            return math.sqrt(
                sum(
                    cls._numerical_distance(a, b, phase_ambiguity=False) ** 2
                    for a, b in zip(expected, given)
                )
            )
        if cls._is_matrix(expected) or cls._is_matrix(given):
            if not (cls._is_matrix(expected) and cls._is_matrix(given)):
                return math.inf
            if expected.shape != given.shape:
                return math.inf
            return cls._magnitude(expected - given)
        return abs(complex(sympy.N(expected - given)))

    def _evaluate(self, expression: Any, substitutions: Mapping[Any, Any]) -> Any:
        if isinstance(expression, list):
            return [self._evaluate(item, substitutions) for item in expression]
        if isinstance(expression, tuple):
            return tuple(self._evaluate(item, substitutions) for item in expression)
        value = expression.subs(substitutions)
        if self.quantum and not self._is_matrix(value):
            value = represent(value)
        return value.evalf()

    def _comparison_form(self, expression: Any) -> Any:
        """Represent kets as vectors before finding free scalar symbols.

        Older SymPy versions include the ket objects themselves in an
        expression's ``free_symbols`` set.  Converting to a vector first keeps
        numerical sampling restricted to the actual amplitude variables.
        """

        if not self.quantum:
            return expression
        if isinstance(expression, list):
            return [self._comparison_form(item) for item in expression]
        if isinstance(expression, tuple):
            return tuple(self._comparison_form(item) for item in expression)
        return represent(expression)

    def _numerically_equal(
        self,
        expected: Any,
        given: Any,
        *,
        samples: str | None,
        tolerance: Any,
        num_trials: int,
        phase_ambiguity: bool,
    ) -> bool:
        ranges, trials = self._sampling_plan(
            expected, given, samples=samples, num_trials=num_trials
        )
        all_symbols = self._free_symbols(expected) | self._free_symbols(given)
        symbols_by_name: dict[str, list[sympy.Symbol]] = {}
        for symbol in all_symbols:
            symbols_by_name.setdefault(str(symbol), []).append(symbol)

        for _ in range(max(1, trials)):
            substitutions: dict[sympy.Symbol, Any] = {}
            for name, (lower, upper) in ranges.items():
                if isinstance(lower, complex) or isinstance(upper, complex):
                    real = self.random.uniform(
                        complex(lower).real, complex(upper).real
                    )
                    imag = self.random.uniform(
                        complex(lower).imag, complex(upper).imag
                    )
                    value: complex | float = complex(real, imag)
                else:
                    value = self.random.uniform(float(lower), float(upper))
                for symbol in symbols_by_name.get(name, []):
                    substitutions[symbol] = value

            expected_value = self._evaluate(expected, substitutions)
            given_value = self._evaluate(given, substitutions)
            distance = self._numerical_distance(
                expected_value, given_value, phase_ambiguity=phase_ambiguity
            )
            limit = self._tolerance_limit(
                expected_value, given_value, tolerance=tolerance
            )
            if not math.isfinite(distance) or distance > limit:
                return False
        return True

    def check(
        self,
        solution: str,
        submission: str,
        *,
        options: str | Mapping[str, Any] | None = None,
        alt_answers: str | Iterable[str] | None = None,
        tolerance: Any = None,
        samples: str | None = None,
        only_symbolic: bool | None = None,
        check_none: bool | None = None,
        phase_ambiguity: bool | None = None,
        num_trials: int | None = None,
    ) -> CheckResult:
        """Compare one submission with one or more acceptable solutions."""

        settings = _merge_options(
            options,
            {
                "alt_answers": alt_answers,
                "tolerance": tolerance,
                "samples": samples,
                "only_symbolic": only_symbolic,
                "check_none": check_none,
                "phase_ambiguity": phase_ambiguity,
                "num_trials": num_trials,
            },
        )
        if settings.get("check_none", False):
            answer = str(submission).strip().casefold()
            return CheckResult(answer in {"none", "empty"})

        alternates = settings.get("alt_answers", [])
        if isinstance(alternates, str):
            alternates = [alternates]
        acceptable_answers = [solution, *list(alternates or [])]

        try:
            given = self._comparison_form(self.parse_input(submission))
        except Exception as exc:
            return CheckResult(
                False,
                "Your input could not be parsed: %s" % html.escape(str(exc)),
            )

        parse_errors: list[str] = []
        for acceptable_source in acceptable_answers:
            try:
                expected = self._comparison_form(
                    self.parse_input(acceptable_source)
                )
            except Exception as exc:
                parse_errors.append(str(exc))
                continue

            if settings.get("only_symbolic", False):
                if expected == given:
                    return CheckResult(True)
                continue

            if self._symbolically_equal(expected, given):
                return CheckResult(True)
            try:
                if self._numerically_equal(
                    expected,
                    given,
                    samples=settings.get("samples"),
                    tolerance=settings.get("tolerance", DEFAULT_TOLERANCE),
                    num_trials=int(
                        settings.get("num_trials", DEFAULT_NUM_TRIALS)
                    ),
                    phase_ambiguity=bool(
                        settings.get("phase_ambiguity", False)
                    ),
                ):
                    return CheckResult(True)
            except Exception as exc:
                return CheckResult(
                    False,
                    "Your expression could not be evaluated: %s"
                    % html.escape(str(exc)),
                )

        if parse_errors:
            return CheckResult(
                False,
                "The configured solution could not be parsed: %s"
                % html.escape(parse_errors[0]),
            )
        return CheckResult(False)

    def latex(self, expression: str) -> str:
        """Return a LaTeX rendering of a parsed expression."""

        return sympy.latex(self.parse_input(expression))


def _run_checker(
    submission: str,
    solution: str,
    *,
    quantum: bool = False,
    array_variables: bool = False,
    options: str | Mapping[str, Any] | None = None,
    alt_answers: str | Iterable[str] | None = None,
    tolerance: Any = None,
    samples: str | None = None,
    only_symbolic: bool | None = None,
    check_none: bool | None = None,
    phase_ambiguity: bool | None = None,
    num_trials: int | None = None,
    force_list_to_matrix: bool = False,
    extra_symbols: Mapping[str, Any] | None = None,
    random_seed: int | None = None,
) -> tuple[float, str]:
    checker = SympyFormulaChecker(
        extra_symbols=extra_symbols,
        quantum=quantum,
        array_variables=array_variables,
        force_list_to_matrix=force_list_to_matrix,
        random_seed=random_seed,
    )
    return checker.check(
        solution,
        submission,
        options=options,
        alt_answers=alt_answers,
        tolerance=tolerance,
        samples=samples,
        only_symbolic=only_symbolic,
        check_none=check_none,
        phase_ambiguity=phase_ambiguity,
        num_trials=num_trials,
    ).catsoop()


def sympy_formula_check(
    submission: str,
    solution: str,
    options: str | Mapping[str, Any] | None = None,
    **settings: Any,
) -> tuple[float, str]:
    """CAT-SOOP checker for symbolic scalars, lists, and matrices."""

    return _run_checker(submission, solution, options=options, **settings)


def array_var_check(
    submission: str,
    solution: str,
    options: str | Mapping[str, Any] | None = None,
    **settings: Any,
) -> tuple[float, str]:
    """CAT-SOOP checker treating ``A[i,j]``-style terms as variables."""

    return _run_checker(
        submission,
        solution,
        array_variables=True,
        options=options,
        **settings,
    )


def sympy_check_quantum(
    submission: str,
    solution: str,
    options: str | Mapping[str, Any] | None = None,
    **settings: Any,
) -> tuple[float, str]:
    """CAT-SOOP checker for symbolic quantum states written with kets."""

    return _run_checker(
        submission,
        solution,
        quantum=True,
        options=options,
        **settings,
    )


CHECKERS = {
    "formula": sympy_formula_check,
    "sympy": sympy_formula_check,
    "sympy_formula_check": sympy_formula_check,
    "array": array_var_check,
    "array_var": array_var_check,
    "array_var_check": array_var_check,
    "quantum": sympy_check_quantum,
    "sympy_check_quantum": sympy_check_quantum,
}


def get_checker(name: str):
    """Resolve a documented checker name, raising a helpful error if unknown."""

    try:
        return CHECKERS[name]
    except KeyError:
        raise ValueError(
            "unknown sympy checker %r; choose one of %s"
            % (name, ", ".join(sorted(CHECKERS)))
        )
