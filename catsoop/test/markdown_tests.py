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
Tests for CAT-SOOP's markdown math extension
"""

import unittest
import markdown

from .. import loader
from .. import markdown_math

from ..test import CATSOOPTest

# -----------------------------------------------------------------------------


def _md_format_string(s):
    return markdown.markdown(s, extensions=[markdown_math.MathExtension()])


def math(x):
    return "<math>%s</math>" % (x,)


def dmath(x):
    return "<displaymath>%s</displaymath>" % (x,)


class TestMarkdownMath(CATSOOPTest):
    def test_inline_math(self):
        pairs = [
            (r"If $x$ is 2", r"<p>If %s is 2</p>" % (math("x"))),
            (
                r"If $x$ is $\frac{2}{3}$",
                r"<p>If %s is %s</p>" % (math("x"), math(r"\frac{2}{3}")),
            ),
            (r"If $x$ is $\frac{2}{3}", r"<p>If %s is $\frac{2}{3}</p>" % (math("x"),)),
            (r"If \$2.38 is $x$", r"<p>If $2.38 is %s</p>" % (math("x"),)),
            (
                r"If $x$ is \$2.38, but $y$ is $\$3.47$",
                r"<p>If %s is $2.38, but %s is %s</p>"
                % (math("x"), math("y"), math(r"\$3.47")),
            ),
        ]

        for i, o in pairs:
            self.assertEqual(_md_format_string(i), o)

    def test_display_math(self):
        self.maxDiff = 10000
        _ft = r"x_5[n]= \cases{\left({1\over2}\right)^{n/2}&$n=0, 2, 4, 6, 8, \dots, \infty$\cr0&otherwise}"
        pairs = [
            (r"If $$x$$ is 2", r"<p>If %s is 2</p>" % (dmath("x"))),
            (
                r"If $$A$$ is $\frac{2}{3}$ and $x_5[n]$ is given by: $$%s$$" % _ft,
                r"<p>If %s is %s and %s is given by: %s</p>"
                % (dmath("A"), math(r"\frac{2}{3}"), math("x_5[n]"), dmath(_ft)),
            ),
        ]

        for i, o in pairs:
            self.assertEqual(_md_format_string(i), o)


if __name__ == "__main__":
    unittest.main()
