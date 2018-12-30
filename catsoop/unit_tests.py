'''
Unit tests for CAT-SOOP

Requires config to be setup, including cs_unit_test_course
'''

import cgi
import urllib
import logging
import unittest

from . import config
from . import loader
from . import dispatch

from oauthlib.oauth1 import Client

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

#-----------------------------------------------------------------------------

class LTI_Consumer(object):
    '''
    Simple LTI tool consumer used for unit-tests of CAT-SOOP acting as an LTI tool provider.
    '''
    def __init__(self, lti_url="", username="lti_user", service_url="http://localhost",
                 consumer_key="consumer_key", secret="secret_key"):
        self.lti_url = lti_url
        self.username = username
        self.service_url = service_url
        self.consumer_key = consumer_key
        self.lti_context = self._get_lti_context(self.lti_url, secret=secret)

    def _get_lti_context(self, lti_url, secret=None):
        """
        Generate the LTI context for a specific LTI url request

        lti_url: (str) URL to the LTI tool provider
        secret: (str) shared secret with the LTI tool provder
        """
        body = {
            'tool_consumer_instance_guid': u'lti_test_%s' % self.lti_url,
            'user_id': self.username + "__LTI__1234",
            'roles': u'[student]',
            'context_id': u"catsoop_test",
            'lti_url': self.lti_url,
            'lti_version': u'LTI-1p0',
            'lis_result_sourcedid': self.username,
            'lis_outcome_service_url': self.service_url,
            'lti_message_type': 'basic-lti-launch-request',	# required, see https://www.imsglobal.org/specs/ltiv2p0/implementation-guide#toc-21
            'resource_link_id': '123',
        }
        retdat = body.copy()
        key = self.consumer_key
        self._sign_lti_message(body, key, secret, lti_url)
        LOGGER.info("[unit_tests] signing OAUTH with key=%s, secret=%s, url=%s" % (key, secret, lti_url))
        retdat.update(dict(
            lti_url=lti_url,
            oauth_consumer_key=key,
            oauth_timestamp=body['oauth_timestamp'],
            oauth_nonce=body['oauth_nonce'],
            # oauth_signature=urllib.parse.unquote(body['oauth_signature']).encode('utf8'),
            oauth_signature=urllib.parse.unquote(body['oauth_signature']),
            oauth_signature_method=body['oauth_signature_method'],
            oauth_version=body['oauth_version'],
        ))
        return retdat
    
    def _sign_lti_message(self, body, key, secret, url):
        client = Client(
            client_key=key,
            client_secret=secret
        )
    
        __, headers, __ = client.sign(
            url,
            http_method=u'POST',
            body=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
    
        auth_header = headers['Authorization'][len('OAuth '):]
        auth = dict([param.strip().replace('"', '').split('=') for param in
                     auth_header.split(',')])
    
        body['oauth_nonce'] = auth['oauth_nonce']
        body['oauth_signature'] = auth['oauth_signature']
        body['oauth_timestamp'] = auth['oauth_timestamp']
        body['oauth_signature_method'] = auth['oauth_signature_method']
        body['oauth_version'] = auth['oauth_version']
    

#-----------------------------------------------------------------------------

class Test_LTI(unittest.TestCase):
    '''
    Test basic LTI functionality
    '''
    def setUp(self):
        context = {}
        e = loader.load_global_data(context)
        assert 'cs_unit_test_course' in context
        self.cname = context['cs_unit_test_course']
        self.ckey = "__test_consumer__"
        self.secret = "__test_secret__"
        self.cs_lti_config = {'session_key': 'aslkdj12', 'consumers': {self.ckey : { "secret": self.secret }}}

        lgd = loader.load_global_data
        def mock_load_global_data(into, check_values=True):
            ret = lgd(into, check_values)
            into['cs_lti_config'] = self.cs_lti_config
            return ret
        loader.load_global_data = mock_load_global_data

        logging.getLogger('pylti.common').setLevel(1)



    def skip_test_lti_auth0(self):
        path = '/_lti/%s/structure' % self.cname
        host = 'localhost:6010'
        url = "http://%s%s" % (host, path)
        ltic = LTI_Consumer(lti_url=url, consumer_key=self.ckey, secret=self.secret)
        data = ltic.lti_context        
        import requests
        ret = requests.post(url, data=data)
        LOGGER.info("return = %s" % ret)
        assert False

    def test_lti_auth1(self):
        env = {'PATH_INFO': '/_lti/%s/structure' % self.cname}
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0]=='200'
        assert "LTI verification failed" in msg

    def test_lti_auth2(self):
        '''
        Test successful authentication with LTI protocol
        '''
        path = '/_lti/foo'
        host = 'localhost:6010'
        url = "http://%s%s" % (host, path)
        ltic = LTI_Consumer(lti_url=url, consumer_key=self.ckey, secret=self.secret)
        def retform():
            return ltic.lti_context
        cgi.FieldStorage = retform	# monkey patch
        env = {'PATH_INFO': path,
               'wsgi.url_scheme': 'http',
               'HTTP_HOST': host,
               'REQUEST_URI': path,
               'REQUEST_METHOD': 'POST',
        }
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0]=='200'
        assert "Hello LTI" in msg

    def test_lti_auth3(self):
        '''
        Test LTI access to courseware
        '''
        path = '/_lti/course/%s/structure' % self.cname
        host = 'localhost:6010'
        url = "http://%s%s" % (host, path)
        ltic = LTI_Consumer(lti_url=url, consumer_key=self.ckey, secret=self.secret)
        def retform():
            return ltic.lti_context
        cgi.FieldStorage = retform	# monkey patch
        env = {'PATH_INFO': path,
               'wsgi.url_scheme': 'http',
               'HTTP_HOST': host,
               'REQUEST_URI': path,
               'REQUEST_METHOD': 'POST',
        }
        status, retinfo, msg = dispatch.main(env)
        LOGGER.info("[unit_tests] status=%s, msg=%s" % (status, msg))
        LOGGER.info("[unit_tests] type(msg)=%s" % type(msg))
        assert status[0]=='200'
        assert "Page Specification and Loading" in msg.decode('utf8')

#-----------------------------------------------------------------------------

if __name__ == '__main__':
        unittest.main()
