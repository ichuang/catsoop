# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import urllib.parse


def get_logged_in_user(context):
    session = context['cs_session_data']

    def generate_token():
        a = context['csm_auth'].get_auth_type_by_name(context, 'login')
        return a['generate_confirmation_token'](50)

    # TODO: log out
    # TODO: show "click here to login" page, with "remember me" link

    # if the session tells us someone is logged in, return their
    # information
    if 'username' in session:
        uname = session['username']
        return {'username': uname,
                'name': session.get('name', uname),
                'email': session.get('email', uname)}

    else:
        redir_url = '%s/__AUTH__/openid_connect/callback' % context['cs_url_root']
        scope = context.get('cs_openid_scope', 'openid profile email')
        state = generate_token()
        nonce = generate_token()
        get_data = {'redirect_uri': redir_url,
                    'state': state,
                    'nonce': nonce,
                    'scope': scope,
                    'client_id': context.get('cs_openid_client_id', None),
                    'response_type': 'code'}
        openid_url = context.get('cs_openid_server', None)
        session['_openid_course'] = context['cs_course']
        session['_openid_path'] = context['cs_path_info']
        session['_openid_nonce'] = nonce
        session['_openid_state'] = state
        # todo: make this redirect actually work
        qstring = urllib.parse.urlencode(get_data)
        return {'cs_redirect': '%s/authorize?%s' % (openid_url, qstring)}
