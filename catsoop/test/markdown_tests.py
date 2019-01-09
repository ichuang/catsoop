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

from .. import loader
from .. import language

from ..test import CATSOOPTest

# -----------------------------------------------------------------------------


def math(x):
    return '<span class="cs_math_to_render">%s</span>' % (x,)


def dmath(x):
    return (
        '<div class="cs_displaymath cs_math_to_render" style="text-align:center;padding-bottom:10px;">%s</div>'
        % (x,)
    )


class TestMarkdownMath(CATSOOPTest):
    def setUp(self):
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context
        self.cname = context["cs_unit_test_course"]
        self.ctx = loader.spoof_early_load([self.cname])

    def test_inline_math(self):
        pairs = [
            (r"If $x$ is 2", r"If %s is 2" % (math("x"))),
            (
                r"If $x$ is $\frac{2}{3}$",
                r"If %s is %s" % (math("x"), math(r"\frac{2}{3}")),
            ),
            (r"If $x$ is $\frac{2}{3}", r"If %s is $\frac{2}{3}" % (math("x"),)),
            (r"If \$2.38 is $x$", r"If $2.38 is %s" % (math("x"),)),
            (
                r"If $x$ is \$2.38, but $y$ is $\$3.47$",
                r"If %s is $2.38, but %s is %s"
                % (math("x"), math("y"), math(r"\$3.47")),
            ),
        ]

        for i, o in pairs:
            self.assertEqual(language._md_format_string(self.ctx, i), o)

    def test_display_math(self):
        pairs = [
            (r"If $$x$$ is 2", r"If %s is 2" % (dmath("x"))),
            (
                r"If $x$ is $\frac{2}{3}$",
                r"If %s is %s" % (math("x"), math(r"\frac{2}{3}")),
            ),
            (r"If $x$ is $\frac{2}{3}", r"If %s is $\frac{2}{3}" % (math("x"),)),
            (r"If \$2.38 is $x$", r"If $2.38 is %s" % (math("x"),)),
            (
                r"If $x$ is \$2.38, but $y$ is $\$3.47$",
                r"If %s is $2.38, but %s is %s"
                % (math("x"), math("y"), math(r"\$3.47")),
            ),
        ]

        for i, o in pairs:
            self.assertEqual(language._md_format_string(self.ctx, i), o)


if __name__ == "__main__":
    unittest.main()
