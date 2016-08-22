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

import os
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


def userinfo_from_token(context, tok):
        return context['csm_cslog'].most_recent(None, 'api_tokens',
                                                '%s' % tok, None)


def get_logged_in_user(context):
    form = context.get('cs_form', {})
    if 'api_token' in form:
        tok = form['api_token']
        log = userinfo_from_token(context, tok)
        if log is not None:
            log['api_token'] = tok
            return log
    return None


def get_user_information(context, uname=None, passwd=None, api_token=None, course=None, _as=None):
    login = context['csm_auth'].get_auth_type_by_name(context, 'login')

    user = None
    error = None

    log = context['csm_cslog']
    if api_token is not None:
        # if there is an API token, check it.
        user = userinfo_from_token(context, api_token)
        if user is None:
            error = "Invalid API token: %s" % api_token
        else:
            user['api_token'] = api_token
            extra_info = log.most_recent(None, user['username'],
                                           'extra_info', {})
            user.update(extra_info)
    else:
        if uname is not None and passwd is not None:
            # if no API token was given, but username and password were, check
            # those.
            hash_iters = context.get('cs_password_hash_iterations', 250000)
            pwd_check = login.check_password(context, passwd, uname, hash_iters)
            if not pwd_check:
                error = 'Invalid username or password.'
            else:
                user = log.most_recent(None, uname, 'logininfo', None)
        else:
            error = 'API token or username and password hash required.'

    if user is None and error is None:
        # catch-all error: if we haven't authenticated but don't have an error
        # messge, use this one.
        error = 'Could not authenticate'

    if error is None and course is not None:
        # if we have successfully logged in and a course is specified, we need to
        # look up extra information from the course in question.
        ctx = context['csm_loader'].spoof_early_load([course])

        ctx['cs_form'] = {}
        if _as is not None:
            ctx['cs_form']['as'] = _as

        base_loc = os.path.join(context['cs_data_root'], 'courses', course)
        if os.path.isdir(base_loc):
            uname = user['username']
            ctx['cs_user_info'] = user
            user = context['csm_auth']._get_user_information(ctx, user,
                                                             course, uname,
                                                             do_preload=True)
        else:
            error = 'No such course: %s' % course

    if error is not None:
        return {'ok': False, 'error': error}
    else:
        return {'ok': True, 'user_info': user}
