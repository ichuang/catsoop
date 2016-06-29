# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE


def get_logged_in_user(context):
    # certificates-based login
    env = context['cs_env']
    if 'SSL_CLIENT_S_DN_Email' not in env:
        return {'username': 'None'}
    else:
        email = env['SSL_CLIENT_S_DN_Email']
        return {'username': email.split('@')[0],
                'email': email,
                'name': env['SSL_CLIENT_S_DN_CN']}
