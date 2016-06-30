# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

# API authentication

import time
import uuid
import random
import string

CHARACTERS = string.ascii_letters + string.digits


def get_api_token(context, username):
    length = context.get('cs_api_token_length', 70)
    seed = username + uuid.uuid4().hex
    r = random.Random()
    r.seed(seed)
    return ''.join(r.choice(CHARACTERS) for i in range(length))


def initialize_api_token(context, token, user_info):
    token = token or get_api_token(context, user_info['username'])
    user_info['_api_token'] = token
    context['csm_cslog'].overwrite_log(None, '_api_tokens',
                                       '%s.userinfo' % token,
                                       user_info)


def get_logged_in_user(context):
    form = context.get('cs_form', {})
    if 'api_token' in form:
        tok = form['api_token']
        log = context['csm_cslog'].most_recent(None, '_api_tokens',
                                               '%s.userinfo' % tok, None)
        if log is not None:
            return log
    return None
