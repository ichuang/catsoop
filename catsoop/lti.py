# This file is part of CAT-SOOP

"""
LTI Tool Provider interface
"""

import os
import string
import random
import hashlib
import logging
import pylti.common

from . import auth
from . import session

LOGGER = logging.getLogger('pylti.common')
LOGGER.setLevel(logging.DEBUG)

LOGGER = logging.getLogger("cs")
LOGGER.setLevel(logging.DEBUG)

class lti4cs(pylti.common.LTIBase):
    '''
    LTI object representation for CAT-SOOP
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

def get_or_create_user(context, uname, email, name):
    '''
    Ensure that the named user (by username) exists; create if necessary
    '''
    session_data = context["cs_session_data"]
    logging = context["csm_cslog"]
    LOGGER.error("[lti.get_or_create_user] uname=%s, email=%s, name=%s" % (uname, email, name))

    login_info = logging.most_recent("_logininfo", [], uname, {})
    if not login_info:	# account doesn't exist, create

        LOGGER.error("[lti.get_or_create_user] uname=%s unknown username -> creating new account")
        passwd = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
        hash_iterations = context.get("cs_password_hash_iterations", 500000)
        salt = get_new_password_salt()
        phash = compute_password_hash(context, passwd, salt, hash_iterations)
        confirmed = True
        
        uinfo = {
            "password_salt": salt,
            "password_hash": phash,
            "email": email,
            "name": name,
            "confirmed": confirmed,
        }
        logging.overwrite_log("_logininfo", [], uname, uinfo)
        
        # session_data["course"] = context.get("cs_course", None)
        login_info = logging.most_recent("_logininfo", [], uname, {})

    LOGGER.error("[lti.get_or_create_user] login_info=%s" % login_info)

    if login_info is None:	# account creation failed
        msg = "[lti.get_or_create_user] failed to create user %s" % uinfo
        LOGGER.error(msg)
        raise Exception(msg)

    info = {"username": uname, "name": name, "email": email}
    session_data.update(info)

    LOGGER.error("[lti.get_or_create_user] login_info = %s" % login_info)
    # LOGGER.error("[lti.get_or_create_user] auth_type=%s" % auth.get_auth_type(context))

    user_info = auth.get_logged_in_user(context)
    LOGGER.error("[lti.get_or_create_user] user_info=%s" % user_info)
    context["cs_user_info"] = user_info
    context["cs_username"] = str(user_info.get("username", None))

    session.set_session_data(
        context, context["cs_sid"], context["cs_session_data"]
    )

    return login_info


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
    lti_ok = l4c.verify_request(params, environment)
    if not lti_ok:
        msg = "LTI verification failed"

    else:
        if lti_action=="course":

            uname = "lti_%s" % session['user_id']
            email = session['lis_person_contact_email_primary']
            name = session['lis_person_name_full']

            get_or_create_user(context, uname, email, name)
            LOGGER.error("[lti] rendering course page for %s" % uname)

            sub_path_info = path_info[1:]	# path without _lti/course prefix
            sub_path = '/'.join(sub_path_info)
            LOGGER.error("[lti] sub_path=%s" % sub_path)
            environment['PATH_INFO'] = sub_path
            environment['is_lti_user'] = True	# see preload.py in course data; forces authorization
            return dispatch_main(environment)

        msg = "Hello LTI"

    return (
        ("200", "Ok"),
        {"Content-type": "text/plain", "Content-length": str(len(msg))},
        msg
    )
        
#-----------------------------------------------------------------------------

def get_new_password_salt(length=128):
    """
    Generate a new salt of length length.  Tries to use os.urandom, and
    falls back on random if that doesn't work for some reason.
    """
    try:
        out = os.urandom(length)
    except:
        out = "".join(chr(random.randint(1, 127)) for i in range(length)).encode()
    return out

def compute_password_hash(context, password, salt=None, iterations=500000, encrypt=True):
    """
    Given a password, and (optionally) an associated salt, return a hash value.
    """
    hash_ = hashlib.pbkdf2_hmac(
        "sha512", _ensure_bytes(password), _ensure_bytes(salt), iterations
    )
    if encrypt and (context["csm_cslog"].ENCRYPT_KEY is not None):
        hash_ = context["csm_cslog"].FERNET.encrypt(hash_)
    return hash_

def _ensure_bytes(x):
    try:
        return x.encode()
    except:
        return x
