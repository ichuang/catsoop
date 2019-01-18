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
"""
Small suite of tests for CAT-SOOP's check module
"""

import math
import random
import unittest

from .. import check

from ..test import CATSOOPTest

# -----------------------------------------------------------------------------


class TestCheckers(CATSOOPTest):
    def test_equal(self):
        for pair in ((1, 1.0), (2, 2), (False, 0)):
            self.assertTrue(check.equal()(*pair))

        for pair in ((1, 1.000001), (2, 3), (False, None)):
            self.assertFalse(check.equal()(*pair))

    def test_check_result(self):
        for pair in ((1, 1.0), (2, 2), (False, 0)):
            pair = [{"result": i, "details": {}} for i in pair]
            self.assertTrue(check.check_result(check.equal())(*pair))
            self.assertTrue(check.check_result()(*pair))
        for pair in ((1, 1.000001), (2, 3), (False, None)):
            pair = [{"result": i, "details": {}} for i in pair]
            self.assertFalse(check.check_result(check.equal())(*pair))

    def test_number_close(self):
        for i in range(50):
            threshold = random.uniform(1e-6, 1e-2)
            x = random.uniform(-1000, 1000)
            y = x + threshold - 1e-9
            self.assertTrue(check.number_close(threshold)(x, y))
            y = x - threshold + 1e-9
            self.assertTrue(check.number_close(threshold)(x, y))

        for i in range(50):
            threshold = random.uniform(1e-6, 1e-2)
            x = random.uniform(-1000, 1000)
            y = x - threshold + 1e-1
            self.assertFalse(check.number_close(threshold)(x, y))
            y = x + threshold - 1e-1
            self.assertFalse(check.number_close(threshold)(x, y))

        for i in range(50):
            threshold = random.uniform(1e-6, 1e-2)
            x = complex(random.uniform(-1000, 1000), random.uniform(-1000, 1000))
            y = x + (threshold - 1e-9) * math.e ** (1j * random.uniform(0, 2 * math.pi))
            self.assertTrue(check.number_close(threshold)(x, y))
            y = x + (threshold + 1e-9) * math.e ** (1j * random.uniform(0, 2 * math.pi))
            self.assertFalse(check.number_close(threshold)(x, y))

        self.assertTrue(check.number_close(1e-9, 0.01)(1e-10, 0))
        self.assertFalse(check.number_close(None, 0.01)(1e-10, 0))

        self.assertTrue(check.number_close(1e-9, 0.01)(100000, 100100))
        self.assertFalse(check.number_close(1e-9, 0.01)(100000, 10100.0001))

    def test_evaled(self):
        vals = (1, 1e-9, "cat", None, True, False, 1 + 2j)
        for ix, i in enumerate(vals):
            self.assertTrue(check.evaled(check.equal())(repr(i), repr(i)))
            if ix != 0:
                self.assertFalse(
                    check.evaled(check.equal())(repr(i), repr(vals[ix - 1]))
                )

        for i in range(2):
            self.assertTrue(
                check.evaled(check.number_close(1e-6))(repr(i), repr(i + 1e-9))
            )
            self.assertFalse(
                check.evaled(check.number_close(1e-6))(repr(i), repr(i + 1e-5))
            )

        self.assertFalse(check.evaled()('"cat"', '"cat'))
        self.assertFalse(check.evaled()('"cat', '"cat"'))
        self.assertFalse(check.evaled()("[1, 2, 3]", "1, 2, 3]"))
        self.assertTrue(check.evaled()("[1, 2, 3]", "[1, 2, 3]"))

    def test_list_all(self):
        x = [1, 1e-9, "cat", None, True, False, 1.2j]
        y = x[:]
        self.assertTrue(check.list_all()(x, y))
        self.assertFalse(check.list_all()(x, y[:-1]))
        self.assertFalse(check.list_all()(x, y + ["something"]))
        self.assertFalse(check.list_all()(x, y[::-1]))

    def test_list_all_unordered(self):
        x = [1, 1e-9, "cat", None, True, False, 1.2j]
        y = x[:]
        self.assertTrue(check.list_all_unordered()(x, y))
        self.assertFalse(check.list_all_unordered()(x, y[:-1]))
        self.assertFalse(check.list_all_unordered()(x, y + ["something"]))
        self.assertTrue(check.list_all_unordered()(x, y[::-1]))
        self.assertFalse(check.list_all_unordered()(x, y[::-1] + [y[-1]]))

    def test_dict_all(self):
        a = {"cat": [7, 8, 9], "coca": "cola", "thing": lambda x: x ** 3}
        b = {k: v for k, v in reversed(list(a.items()))}
        self.assertTrue(check.dict_all()(a, b))

        a = {"cat": 7, "dog": 1e-9, "ferret": 1 + 2j, "tomato": 3j}
        b = {k: v + random.uniform(-1e-6, 1e-6) for k, v in a.items()}
        self.assertTrue(check.dict_all(check.number_close(1e-6))(a, b))
        b = {k: v + 1j * random.uniform(1e-2, 1e-1) for k, v in a.items()}
        self.assertFalse(check.dict_all(check.number_close(1e-6))(a, b))


if __name__ == "__main__":
    unittest.main()
