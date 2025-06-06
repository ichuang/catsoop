# This file is part of CAT-SOOP
# Copyright (c) 2011-2025 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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


def math(x, env=""):
    env = ' env="%s"' % env if env else ""
    return "<math%s>%s</math>" % (env, x)


def dmath(x, env=""):
    env = ' env="%s"' % env if env else ""
    return "<displaymath%s>%s</displaymath>" % (env, x)


def _md(x):
    out = language._md(x).strip()
    if out.startswith("<p>") and out.endswith("</p>"):
        out = out[3:-4]
    return out


class TestMarkdownMath(CATSOOPTest):
    def setUp(self):
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context
        self.cname = context["cs_unit_test_course"]
        self.ctx = loader.generate_context([self.cname])

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
            self.assertEqual(_md(i), o)

    def test_display_math(self):
        self.maxDiff = 10000
        _ft = r"x_5[n]= \cases{\left({1\over2}\right)^{n/2}&$n=0, 2, 4, 6, 8, \dots, \infty$\cr0&otherwise}"
        pairs = [
            (r"If $$x$$ is 2", r"If %s is 2" % (dmath("x"))),
            (
                r"If $$A$$ is $\frac{2}{3}$ and $x_5[n]$ is given by: $$%s$$" % _ft,
                r"If %s is %s and %s is given by: %s"
                % (dmath("A"), math(r"\frac{2}{3}"), math("x_5[n]"), dmath(_ft)),
            ),
            (
                "$$x = \\text{something like $2$}$$",
                dmath(r"x = \text{something like $2$}"),
            ),
            (
                "\\begin{align}\n  x & \\text{if $y$} \\\\\n  y & \\text{else}\n\\end{align}",
                dmath("\nx & \\text{if $y$} \\\\\ny & \\text{else}\n", "align"),
            ),
            (
                "\\begin{align*}\n  x & \\text{if $y$} \\\\\n  y & \\text{else}\n\\end{align*}",
                dmath("\nx & \\text{if $y$} \\\\\ny & \\text{else}\n", "align*"),
            ),
        ]

        for i, o in pairs:
            self.assertEqual(_md(i), o)

    def test_dollar_sign_escapes(self):
        self.maxDiff = 10000

        allmath = [r"$\$2 + \$3$", r"$x = \$200$", "$math$"]
        pairs = [
            (r"\$x + y\$", "$x + y$"),
            (r"\$\$x + y\$\$", "$$x + y$$"),
            (r"`$not math$`", r"<code>$not math$</code>"),
            (r"```\n$not math$\n```", r"<code>\n$not math$\n</code>"),
        ]

        for i in allmath:
            self.assertEqual(_md(i), math(i[1:-1]))
        for i, o in pairs:
            self.assertEqual(_md(i), o)

    def test_inline_code(self):
        ins = [
            "py`hello`",
            "py``hello`` there",
            "`hello` there",
            "`hell\no` there",
            "py`hell\no` there",
        ]
        outs = [
            '<span class="hl"><code class="lang-py">hello</code></span>',
            '<span class="hl"><code class="lang-py">hello</code></span> there',
            "<code>hello</code> there",
            "<code>hell\no</code> there",
            '<span class="hl"><code class="lang-py">hell\no</code></span> there',
        ]

        for i, o in zip(ins, outs):
            self.assertEqual(_md(i), o)


if __name__ == "__main__":
    unittest.main()
