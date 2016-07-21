# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

# API authentication

import time
import uuid
import random
import string

CHARACTERS = string.ascii_letters + string.digits


def new_api_token(context, username):
    length = context.get('cs_api_token_length', 70)
    seed = username + uuid.uuid4().hex
    r = random.Random()
    r.seed(seed)
    return ''.join(r.choice(CHARACTERS) for i in range(length))


def initialize_api_token(context, user_info):
    token = new_api_token(context, user_info['username'])
    context['csm_cslog'].overwrite_log(None, 'api_tokens',
                                       '%s' % token,
                                       user_info)
    context['csm_cslog'].update_log(None, user_info['username'],
                                    'api_token', token)
    return token


def get_logged_in_user(context):
    form = context.get('cs_form', {})
    if 'api_token' in form:
        tok = form['api_token']
        log = context['csm_cslog'].most_recent(None, 'api_tokens',
                                               '%s' % tok, None)
        if log is not None:
            return log
    return None
