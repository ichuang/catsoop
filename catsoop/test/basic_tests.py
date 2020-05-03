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
Unit tests for CAT-SOOP

Requires config to be setup, including cs_unit_test_course
"""

import unittest

from catsoop import cslog
from catsoop import loader
from catsoop import session
from catsoop import dispatch

from ..test import CATSOOPTest

# -----------------------------------------------------------------------------


class Test_Basic(CATSOOPTest):
    """
    some basic tests for CAT-SOOP
    """

    def setUp(self):
        cslog.clear_old_log_files(session.SESSION_DIR, 0)
        CATSOOPTest.setUp(self)
        context = {}
        loader.load_global_data(context)
        assert "cs_unit_test_course" in context
        self.cname = context["cs_unit_test_course"]

    def test_static1(self):
        env = {"PATH_INFO": "/%s/structure" % self.cname}
        status, retinfo, msg = dispatch.main(env)
        msg = msg.decode("utf8")
        assert status[0] == "200"
        assert "6.SAMP" in msg

    def test_context1(self):
        env = {"PATH_INFO": "/%s/structure" % self.cname}
        context = dispatch.main(env, return_context=True)
        cui = context["cs_user_info"]
        print("cs_user_info=%s" % context['cs_user_info'])
        assert cui["role"] == "Guest"


if __name__ == "__main__":
    unittest.main()
