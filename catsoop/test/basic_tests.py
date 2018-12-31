'''
Unit tests for CAT-SOOP

Requires config to be setup, including cs_unit_test_course
'''

import os
import cgi
import logging
import unittest

from . import setup_data
from catsoop import loader
from catsoop import dispatch

logging.getLogger("cs").setLevel(1)
LOGGER = logging.getLogger("cs")

#-----------------------------------------------------------------------------

class Test_Basic(unittest.TestCase):
    '''
    some basic tests for CAT-SOOP
    '''
    def setUp(self):
        context = {}
        e = loader.load_global_data(context)
        assert 'cs_unit_test_course' in context
        self.cname = context['cs_unit_test_course']

    def test_static1(self):
        env = {'PATH_INFO': '/%s/structure' % self.cname}
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        msg = msg.decode('utf8')
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0]=='200'
        assert "6.SAMP" in msg

    def test_context1(self):
        env = {'PATH_INFO': '/%s/structure' % self.cname}
        context = dispatch.main(env, return_context=True)
        cui = context['cs_user_info']
        LOGGER.info("[unit_tests] cs_user_info=%s" % cui)
        assert cui['role'] == 'Guest'

if __name__ == '__main__':
        unittest.main()
