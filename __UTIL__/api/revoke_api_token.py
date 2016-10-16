# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import json

api_token = cs_form.get('api_token', None)

error = None

if api_token is None:
    error = "api_token is required"

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token)
    if output['ok']:
        uinfo = output['user_info']
    else:
        error = 'Could not get user information'

if error is not None:
    output = {'ok': False, 'error': error}
else:
    tok = cslog.most_recent(None, 'api_users',
                            uinfo['username'], None)
    if tok is not None:
        cslog.overwrite_log(None, 'api_tokens',
                            tok, None)
    newtok = csm_api.initialize_api_token(globals(), uinfo)
    output = {'ok': True, 'new_token': newtok}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(output)
