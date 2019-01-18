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


def equal():
    """
    Check whether two values are equivalent using Python's ==
    """
    return lambda sub, soln: sub == soln


def check_result(f=None):
    """
    Given a function that compares two Python values, return a new check
    function that compares the 'result' fields of a submission and solution
    using the given function.
    """
    f = f if f is not None else equal()
    return lambda sub, soln: f(sub["result"], soln["result"])


def number_close(absolute_threshold=None, ratio_threshold=None):
    """
    Check whether two numbers are close (within the given thresholds)
    """

    def _checker(sub, sol):
        try:
            r = ratio_threshold is not None
            a = absolute_threshold is not None
            if r and a:
                threshold = max(ratio_threshold * sol, absolute_threshold)
            elif r:
                threshold = ratio_threshold * sol
            elif a:
                threshold = absolute_threshold
            else:
                return sub == sol
            if abs(sub - sol) > abs(threshold):
                return False
        except:
            return False
        return True

    return _checker


def evaled(f=None):
    """
    Returns a new check function that evaluates its arguments (using
    ast.literal_eval) before calling the given function on the evaluated
    results
    """
    f = f if f is not None else equal()

    def _inner(sub, soln):
        try:
            return f(ast.literal_eval(sub), ast.literal_eval(soln))
        except:
            return False

    return _inner


def list_all(cmp_func=None):
    """
    Check that two lists are equal (same values in the same order)
    """
    cmp_func = cmp_func or equal()
    return lambda sub, soln: (
        len(sub) == len(soln) and all(cmp_func(i, j) for i, j in zip(sub, soln))
    )


def list_all_unordered(cmp_func=None):
    """
    Check function for lists containing all the same elements (including
    duplicates), regardless of order.
    """
    cmp_func = cmp_func or equal()

    def _cmp(sub, soln):
        sub = list(sub)
        soln = list(soln)
        while sub:
            elt = sub.pop()
            for elt2 in soln:
                if cmp_func(elt, elt2):
                    soln.remove(elt2)
                    break
            else:
                return False
        return len(sub) == len(soln) == 0

    return _cmp


def dict_all(cmp_func=None):
    """
    Checker function for dictionaries.  Makes sure all keys and associated
    values match.
    """
    cmp_func = cmp_func or equal()
    return lambda sub, soln: (
        set(sub) == set(soln) and all(cmp_func(sub[i], soln[i]) for i in sub)
    )
