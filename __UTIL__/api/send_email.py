# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import json

course = cs_form.get('course', None)
api_token = cs_form.get('api_token', None)
messages = cs_form.get('messages', None)
from_addr = cs_form.get('from_address', None)

error = None

if api_token is None:
    error = "api_token is required"

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token, course=course)
    if output['ok']:
        uinfo = output['user_info']
        if 'email' not in uinfo['permissions']:
            error = 'Permission Denied'

if error is None:
    try:
        messages = json.loads(messages)
    except:
        error = 'error loading messages'

required_fields = ('recipient', 'subject', 'body')

if error is None:
    out = []
    for m in messages:
        if any(i not in m for i in required_fields):
            out.append('Required field missing')
            continue
        out.append(csm_mail.internal_message(globals(), course, m['recipient'], m['subject'], m['body'], from_addr))

cs_handler = 'raw_response'
content_type = 'application/json'
if error is not None:
    out = {'ok': False, 'error': error}
else:
    out = {'ok': True, 'responses': out}
response = json.dumps(out)
