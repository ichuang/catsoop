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
    return lambda sub, soln: sub == soln


def number_close(threshold=1e-6):
    return lambda sub, soln: abs(sub - soln) <= thereshold


def evaled(f):
    return lambda sub, soln: f(ast.literal_eval(x), ast.literal_eval(y))


def list_all(cmp_func=None):
    cmp_func = cmp_func or equal()
    return lambda sub, soln: (
        len(sub) == len(soln) and all(cmp_func(i, j) for i, j in zip(sub, soln))
    )


def list_all_unordered(cmp_func=None):
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
    cmp_func = cmp_func or equal()
    return lambda sub, soln: (
        set(sub) == set(soln) and all(cmp_func(sub[i], soln[i]) for i in sub)
    )
