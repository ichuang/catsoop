# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import json
import base64
import urllib.request, urllib.parse, urllib.error

stored_state = cs_session_data.get('_openid_state', None)
state = cs_form.get('state', None)

if stored_state is None:
    # TODO: Break
    pass
elif state is None:
    # TODO: Break in different way
    pass
elif stored_state != state:
    # TODO: Break in even more different way
    pass

# we should have course information in the session data, so we can see if we
# need to do a preload.

ctx = {}
csm_loader.load_global_data(ctx)

session = cs_session_data

if '_openid_course' in session:
    ctx['cs_course'] = cs_session_data['_openid_course']
    cfile = csm_dispatch.content_file_location(ctx, [ctx['cs_course']])
    csm_loader.do_early_load(ctx, ctx['cs_course'], [], ctx, cfile)



# if we're here, we know we got back something reasonable.
# now, need to send POST request

id = ctx.get('cs_openid_client_id', '')
secret = ctx.get('cs_openid_client_secret', '')

redir_url = '%s/__AUTH__/openid_connect/callback' % ctx['cs_url_root']
data = urllib.parse.urlencode({'grant_type': 'authorization_code',
                               'code': cs_form['code'],
                               'redirect_uri': redir_url,
                               'client_id': id,
                               'client_secret': secret}).encode()
request = urllib.request.Request('%s/token' % ctx['cs_openid_server'], data)
resp = urllib.request.urlopen(request, data).read() # TODO: error handling on this

# TODO: checks on validity of response
resp = json.loads(resp.decode())

# TODO: handle and validate id token
#tok = json.loads(base64.b64decode(rep['id_token']))

access_tok = resp['access_token']

redir = '%s/userinfo' % ctx.get('cs_openid_server', '')
request2 = urllib.request.Request(redir, headers={'Authorization': 'Bearer %s' % access_tok})
resp = json.loads(urllib.request.urlopen(request2).read().decode()) # TODO: error handling on this

# set session info, redirect back to original page
session.update({'username': resp['preferred_username'],
                'email': resp['email'],
                'name': resp['name']})
csm_session.set_session_data(globals(), cs_sid, session)

cs_handler = 'redirect'
redirect_location = '/'.join([csm_base_context.cs_url_root] + session['_openid_path'])
