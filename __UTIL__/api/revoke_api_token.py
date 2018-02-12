# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    tok = cslog.most_recent('_api_users', [],
                            uinfo['username'], None)
    if tok is not None:
        cslog.overwrite_log('_api_tokens', [],
                            tok, None)
    newtok = csm_api.initialize_api_token(globals(), uinfo)
    output = {'ok': True, 'new_token': newtok}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(output)
