# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.


def get_logged_in_user(context):
    # certificates-based login
    env = context['cs_env']
    if 'SSL_CLIENT_S_DN_Email' in env:
       email = env['SSL_CLIENT_S_DN_Email']
       return {'username': email.split('@')[0],
               'email': email,
               'name': env['SSL_CLIENT_S_DN_CN']}
    elif 'SSL_CLIENT_S_DN' in env:
        cert_data = {}
        for i in env['SSL_CLIENT_S_DN'].split('/'):
            try:
                k, v = i.split('=')
                cert_data[k] = v
            except:
                pass
        email = cert_data.get('emailAddress', 'None')
        return {'username': email.split('@')[0],
                'email': email,
                'name': cert_data.get('CN', email)}
    else:
        return {'username': 'None'}
