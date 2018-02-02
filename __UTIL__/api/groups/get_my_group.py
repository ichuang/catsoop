# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hartz@mit.edu>
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
path = cs_form.get('path', None)
_as = cs_form.get('as', None)

error = None

if api_token is None:
    error = "api_token is required"

try:
    path = opath = json.loads(path)
except:
    error = "invalid path: %s" % path

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token, course=path[0], _as=_as)
    if output['ok']:
        uinfo = output['user_info']
    else:
        error = 'Could not get user information'

if error is None:
    ctx = csm_loader.spoof_early_load(opath)
    section, group, members = csm_groups.get_group(ctx, path, uinfo['username'])
    if section is None and group is None:
        error = "%s has not been assigned to a group" % uinfo['username']
        members = [uinfo['username']]
    members = list(sorted(members, key=lambda x: (0 if x == uinfo['username'] else 1, x)))

if error is not None:
    output = {'ok': False, 'error': error}
else:
    output = {'ok': True, 'section': section, 'group': group, 'members': members}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(output)
