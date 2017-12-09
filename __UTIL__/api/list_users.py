# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
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

# api endpoint to get user information.
# requires: username and password, or api token
# optional: course ID for extra information

import json

cs_handler = 'raw_response'
content_type = 'application/json'

course = cs_form.get('course', None)
api_token = cs_form.get('api_token', None)

error = None

if api_token is None or course is None:
    error = "api_token and course are required"

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token, course=course)
    if output['ok']:
        uinfo = output['user_info']
        if 'admin' not in uinfo['permissions']:
            error = 'Permission Denied'

if error is None:
    output = {'ok': True, 'result': csm_util.list_all_users(globals(), course)}
else:
    output = {'ok': False, 'error': error}

response = json.dumps(output)
