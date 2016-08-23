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

    logintype = context['csm_auth'].get_auth_type_by_name(context, 'login')

    def generate_token():
        return logintype['generate_confirmation_token'](50)

    _get_base_url = logintype['_get_base_url']

    # if the session tells us someone is logged in, return their
    # information
    action = context['cs_form'].get('loginaction', None)
    if action == 'logout':
        context['cs_session_data'] = {}
        return {'cs_reload': True}
    elif 'username' in session:
        uname = session['username']
        return {'username': uname,
                'name': session.get('name', uname),
                'email': session.get('email', uname)}
    elif action is None:
        if context.get('cs_view_without_auth', True):
            context['cs_handler'] = 'passthrough'
            context['cs_content_header'] = 'Please Log In'
            context['cs_content'] = LOGIN_PAGE % _get_base_url(context)
            return {'cs_render_now': True}
        else:
            old_postload = context.get('cs_post_load', None)
            if old_postload is not None:
                def new_postload(context):
                    old_postload(context)
                    context['cs_content'] = ((LOGIN_BOX % _get_base_url(context)) +
                                              context['cs_content'])
                context['cs_post_load'] = new_postload
            return {}
    elif action == 'redirect':
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
        qstring = urllib.parse.urlencode(get_data)
        return {'cs_redirect': '%s/authorize?%s' % (openid_url, qstring)}
    else:
        raise Exception("Unknown action: %r" % action)


LOGIN_PAGE = """
Access to this page requires logging in via OpenID Connect.  Please <a href="%s?loginaction=redirect">Log In</a> to continue.
"""

LOGIN_BOX = """
<div class="response">
<b><center>You are not logged in.</center></b><br/>
If you are a current student, please <a href="%s?loginaction=redirect">Log In</a> for full access to this page.
</div>
"""
