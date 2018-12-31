# This file is part of CAT-SOOP

"""
LTI Tool Provider interface
"""

import os
import uuid
import string
import random
import hashlib
import pylti.common

from lxml import etree
from lxml.builder import ElementMaker

from . import auth
from . import session
from . import debug_log

LOGGER = debug_log.LOGGER

class lti4cs(pylti.common.LTIBase):
    '''
    LTI object representation for CAT-SOOP: validation and data receipt
    '''
    def __init__(self, context, session, lti_args, lti_kwargs):
        self.session = session
        self.lti_data = {}
        pylti.common.LTIBase.__init__(self, lti_args, lti_kwargs)

        self.consumers = context.get('cs_lti_config')['consumers']
        self.lti_session_key = context.get('cs_lti_config')['session_key']
        self.base_url = context.get('cs_lti_config', {}).get('base_url')

    def verify_request(self, params, environment):
        try:
            base_url_default = "%s://%s" % (environment['wsgi.url_scheme'], environment['HTTP_HOST'])
            url = "%s/%s" % (self.base_url or base_url_default, environment['REQUEST_URI'][1:])
            method = environment['REQUEST_METHOD']
            LOGGER.info("[lti.lti4cs.verify_request] method=%s, url=%s" % (method, url))
            pylti.common.verify_request_common(self.consumers,
                                               url,
                                               method,
                                               environment,
                                               params)
            LOGGER.info('[lti.lti4cs.verify_request] verify_request success')
            for prop in pylti.common.LTI_PROPERTY_LIST:
                if params.get(prop, None):
                    LOGGER.info("[lti.lti4cs.verify_request] params %s=%s", prop, params.get(prop, None))
                    self.lti_data[prop] = params[prop]

            self.session['lti_data'] = self.lti_data
            return True

        except Exception as err:
            LOGGER.error('[lti.lti4cs.verify_request] verify_request failed, err=%s' % str(err))
            self.session['lti_data'] = {}
            self.session['is_lti_user'] = False

        return False

    def save_lti_data(self, context):
        '''
        Save LTI data locally (e.g. so that the checker can send grades back to the LTI tool consumer)
        '''
        logging = context["csm_cslog"]
        uname = context["cs_user_info"]["username"]
        db_name = "_lti_data"
        logging.overwrite_log(db_name, [], uname, self.lti_data)
        lfn = logging.get_log_filename(db_name, [], uname)
        LOGGER.info("[lti] saved lti_data for user %s in file %s" % (uname, lfn))

class lti4cs_response(object):
    '''
    LTI handler for responses from CAT-SOOP to tool consumer
    '''
    def __init__(self, context, lti_data=None):
        '''
        Load LTI data from logs (cs database) if available
        '''
        if lti_data:
            self.lti_data = lti_data	# use provided LTI data (e.g. for asynchronous grading response)
        else:
            logging = context["csm_cslog"]
            uname = context["cs_user_info"]["username"]
            db_name = "_lti_data"
            self.lti_data = logging.most_recent(db_name, [], uname)	# retrieve LTI data 
        self.consumers = context.get('cs_lti_config')['consumers']
        self.pylti_url_fix = context.get('cs_lti_config').get('pylti_url_fix', {})

    def to_dict(self):
        '''
        Return dict representation of this LTI response handler
        '''
        return self.lti_data

    @property
    def have_data(self):
        return bool(self.lti_data)

    def send_outcome(self, data):
        '''
        Send outcome (ie grade) to LTI tool consumer (XML as defined in LTI v1.1)
        '''
        url = self.response_url
        result_sourcedid = self.lti_data.get('lis_result_sourcedid', None)
        consumer_key = self.lti_data.get("oauth_consumer_key")
        xml_body = self.generate_result_xml(result_sourcedid, data)
        LOGGER.info("[lti.lti4cs_response.send_outcome] sending grade=%s to %s" % (data, url))
        success = pylti.common.post_message(self.consumers, consumer_key, url, xml_body)
        if success:
            LOGGER.info("[lti.lti4cs_response.send_outcome] outcome sent successfully")
        else:
            LOGGER.error("[lti.lti4cs_response.send_outcome] outcome sending FAILED")

    def generate_result_xml(self, result_sourcedid, score):
        '''
        Create the XML document that contains the new score to be sent to the LTI
        consumer. The format of this message is defined in the LTI 1.1 spec.
        '''
        elem = ElementMaker(nsmap={None: 'http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'})
        xml = elem.imsx_POXEnvelopeRequest(
            elem.imsx_POXHeader(
                elem.imsx_POXRequestHeaderInfo(
                    elem.imsx_version('V1.0'),
                    elem.imsx_messageIdentifier(str(uuid.uuid4()))
                )
            ),
            elem.imsx_POXBody(
                elem.replaceResultRequest(
                    elem.resultRecord(
                        elem.sourcedGUID(
                            elem.sourcedId(result_sourcedid)
                        ),
                        elem.result(
                            elem.resultScore(
                                elem.language('en'),
                                elem.textString(str(score))
                            )
                        )
                    )
                )
            )
        )
        xml = etree.tostring(xml, xml_declaration=True, encoding='UTF-8')	# bytes
        xml = xml.decode("utf-8")
        return xml

    @property
    def response_url(self):
        """
        Returns remapped lis_outcome_service_url
        uses pylti_url_fix map to support edX dev-stack

        :return: remapped lis_outcome_service_url
        """
        url = ""
        url = self.lti_data['lis_outcome_service_url']
        urls = self.pylti_url_fix
        # url remapping is useful for using edX devstack
        # edX devstack reports httpS://localhost:8000/ and listens on HTTP
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
    if not 'cs_lti_config' in context:
        msg = "[lti] LTI not configured - missing cs_lti_config in config.py"
        LOGGER.error(msg)
        raise Exception(msg)

    LOGGER.info("[lti] parameters=%s" % params)
    lti_action = path_info[0]
    LOGGER.info("[lti] lti_action=%s, path_info=%s" % (lti_action, path_info))

    session_data = context['cs_session_data']
    l4c = lti4cs(context, session_data, {}, {})
    lti_ok = l4c.verify_request(params, environment)
    if not lti_ok:
        msg = "LTI verification failed"
    else:
        lti_data = session_data["lti_data"]
        lup = context['cs_lti_config'].get("lti_username_prefix", "lti_")
        lti_uname = lti_data['user_id']
        if not context['cs_lti_config'].get("force_username_from_id"):
            lti_uname = lti_data.get("lis_person_sourcedid", lti_uname)	# prefer username to user_id
        uname = "%s%s" % (lup, lti_uname)
        email = lti_data.get('lis_person_contact_email_primary', "%s@unknown" % uname)
        name = lti_data.get('lis_person_name_full', uname)
        lti_data['cs_user_info'] = {"username": uname, "name": name, "email": email,
                                    "lti_role": lti_data.get('roles'),
                                    "is_lti_user": True}		# save LTI user data in session for auth.py
        session_data.update(lti_data['cs_user_info'])
        session.set_session_data(context, context["cs_sid"], session_data)	# save session data
        user_info = auth.get_logged_in_user(context)			# saves user_info in context["cs_user_info"]
        LOGGER.info("[lti] auth user_info=%s" % user_info)
        
        l4c.save_lti_data(context)	# save lti data, e.g. for later use by the checker
        if lti_action=="course":

            LOGGER.info("[lti] rendering course page for %s" % uname)

            sub_path_info = path_info[1:]	# path without _lti/course prefix
            sub_path = '/'.join(sub_path_info)
            LOGGER.info("[lti] sub_path=%s" % sub_path)
            environment['PATH_INFO'] = sub_path
            environment['session_id'] = context['cs_sid']	# so that a new session ID isn't generated
            return dispatch_main(environment)

        msg = "Hello LTI"

    return (
        ("200", "Ok"),
        {"Content-type": "text/plain", "Content-length": str(len(msg))},
        msg
    )
