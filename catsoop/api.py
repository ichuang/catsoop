# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/agpl-3.0-standalone.html>.

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


def invalidate_api_token(context, token):
    token = token or get_api_token(context, user_info['username'])
    context['csm_cslog'].overwrite_log(None, '_api_tokens',
                                       '%s.userinfo' % token,
                                       None)


def get_logged_in_user(context):
    form = context.get('cs_form', {})
    if 'api_token' in form:
        tok = form['api_token']
        log = context['csm_cslog'].most_recent(None, '_api_tokens',
                                               '%s.userinfo' % tok, None)
        if log is not None:
            return log
    return None
