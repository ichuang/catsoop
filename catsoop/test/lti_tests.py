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

import os
import cgi
import tempfile
import logging
import unittest

from . import setup_data
from catsoop import loader
from catsoop import dispatch
from catsoop import lti

logging.getLogger("cs").setLevel(1)
LOGGER = logging.getLogger("cs")

# -----------------------------------------------------------------------------


class Test_LTI(unittest.TestCase):
    """
    Test basic LTI functionality
    """

    def setUp(self):
        context = {}
        e = loader.load_global_data(context)
        assert "cs_unit_test_course" in context
        self.cname = context["cs_unit_test_course"]
        self.ckey = "__test_consumer__"
        self.secret = "__test_secret__"
        self.cs_lti_config = {
            "session_key": "aslkdj12",
            "consumers": {self.ckey: {"secret": self.secret}},
        }

        lgd = loader.load_global_data

        def mock_load_global_data(into, check_values=True):
            ret = lgd(into, check_values)
            into["cs_lti_config"] = self.cs_lti_config
            return ret

        loader.load_global_data = mock_load_global_data

        logging.getLogger("pylti.common").setLevel(1)

    def skip_test_lti_auth0(self):
        path = "/_lti/%s/structure" % self.cname
        host = "localhost:6010"
        url = "http://%s%s" % (host, path)
        ltic = lti.LTI_Consumer(lti_url=url, consumer_key=self.ckey, secret=self.secret)
        data = ltic.lti_context
        import requests

        ret = requests.post(url, data=data)
        LOGGER.info("return = %s" % ret)
        assert False

    def test_lti_auth1(self):
        env = {"PATH_INFO": "/_lti/%s/structure" % self.cname}
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0] == "200"
        assert "LTI verification failed" in msg

    def test_lti_auth2(self):
        """
        Test successful authentication with LTI protocol
        """
        path = "/_lti/foo"
        host = "localhost:6010"
        url = "http://%s%s" % (host, path)
        ltic = lti.LTI_Consumer(lti_url=url, consumer_key=self.ckey, secret=self.secret)

        def retform():
            return ltic.lti_context

        cgi.FieldStorage = retform  # monkey patch
        env = {
            "PATH_INFO": path,
            "wsgi.url_scheme": "http",
            "HTTP_HOST": host,
            "REQUEST_URI": path,
            "REQUEST_METHOD": "POST",
        }
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0] == "200"
        assert "Hello LTI" in msg

    def test_lti_auth3(self):
        """
        Test LTI access to courseware
        """
        path = "/_lti/course/%s/structure" % self.cname
        host = "localhost:6010"
        url = "http://%s%s" % (host, path)
        ltic = lti.LTI_Consumer(lti_url=url, consumer_key=self.ckey, secret=self.secret)

        def retform():
            return ltic.lti_context

        cgi.FieldStorage = retform  # monkey patch
        env = {
            "PATH_INFO": path,
            "wsgi.url_scheme": "http",
            "HTTP_HOST": host,
            "REQUEST_URI": path,
            "REQUEST_METHOD": "POST",
        }
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0] == "200"
        assert "Page Specification and Loading" in msg.decode("utf8")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
