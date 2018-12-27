# This file is part of CAT-SOOP

"""
LTI Tool Provider interface
"""

import os
import logging
import pylti.common

LOGGER = logging.getLogger('pylti.common')
LOGGER.setLevel(logging.DEBUG)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

class lti4cs(pylti.common.LTIBase):
    '''
    LTI object representation
    '''
    def __init__(self, session, lti_args, lti_kwargs):
        self.session = session
        pylti.common.LTIBase.__init__(self, lti_args, lti_kwargs)
        self.consumers = {
            "__consumer_key__": {
                "secret": "__lti_secret__",
            }
        }
        self.LTI_SESSION_KEY = "oij1op24jsdnf"

    def verify_request(self, params, environment):
        try:
            url = "%s://%s%s" % (environment['wsgi.url_scheme'],
                                  environment['HTTP_HOST'],
                                  environment['REQUEST_URI'])
            method = environment['REQUEST_METHOD']
            LOGGER.error("[lti.lti4cs.verify_request] method=%s, url=%s" % (method, url))
            pylti.common.verify_request_common(self.consumers,
                                               url,
                                               method,
                                               environment,
                                               params)
            LOGGER.error('[lti.lti4cs.verify_request] verify_request success')
            for prop in pylti.common.LTI_PROPERTY_LIST:
                if params.get(prop, None):
                    LOGGER.error("[lti.lti4cs.verify_request] params %s=%s", prop, params.get(prop, None))
                    self.session[prop] = params[prop]

            # Set logged in session key
            self.session[self.LTI_SESSION_KEY] = True
            return True
        except Exception as err:
            LOGGER.error('[lti.lti4cs.verify_request] verify_request failed, err=%s' % str(err))
            for prop in pylti.common.LTI_PROPERTY_LIST:
                if self.session.get(prop, None):
                    del self.session[prop]
            self.session[self.LTI_SESSION_KEY] = False

        return False

    @property
    def response_url(self):
        """
        Returns remapped lis_outcome_service_url
        uses PYLTI_URL_FIX map to support edX dev-stack

        :return: remapped lis_outcome_service_url
        """
        url = ""
        url = self.session['lis_outcome_service_url']
        app_config = self.lti_kwargs['app'].config
        urls = app_config.get('PYLTI_URL_FIX', dict())
        # url remapping is useful for using devstack
        # devstack reports httpS://localhost:8000/ and listens on HTTP
        for prefix, mapping in urls.items():
            if url.startswith(prefix):
                for _from, _to in mapping.items():
                    url = url.replace(_from, _to)
        return url

def serve_lti(context, path_info, environment, params, dispatch_main):
    '''
    context: (dict) catsoop global context
    path_info: (list) URL path components
    environment: (dict-like) web server data, such as form input
    dispatch_main: (proc) call this with environment to dispatch to render URL
    '''
    LOGGER.error("[lti] parameters=%s" % params)
    lti_action = path_info[0]
    LOGGER.error("[lti] lti_action=%s, path_info=%s" % (lti_action, path_info))

    session = context['cs_session_data']
    l4c = lti4cs(session, {}, {})
    if not l4c.verify_request(params, environment):
        msg = "LTI verification failed"

    else:
        if lti_action=="course":
            sub_path_info = path_info[1:]	# path without _lti/course prefix
            sub_path = '/'.join(sub_path_info)
            LOGGER.error("[lti] sub_path=%s" % sub_path)
            environment['PATH_INFO'] = sub_path
            return dispatch_main(environment)

        msg = "Hello LTI"

    return (
        ("200", "Ok"),
        {"Content-type": "text/plain", "Content-length": str(len(msg))},
        msg
    )
        
