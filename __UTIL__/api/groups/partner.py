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

import json

api_token = cs_form.get('api_token', None)
path = cs_form.get('path', None)
name1 = cs_form.get('username1', None)
name2 = cs_form.get('username2', None)

error = None

if api_token is None:
    error = "api_token is required"
elif name1 is None:
    error = "username1 is required"
elif name2 is None:
    error = "username2 is required"

try:
    path = opath = json.loads(path)
except:
    error = "invalid path: %s" % path

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token, course=path[0])
    if output['ok']:
        uinfo = output['user_info']
        if 'groups' not in uinfo['permissions'] and 'admin' not in uinfo['permissions']:
            error = 'Permission Denied'

if error is None:
    ctx = csm_loader.spoof_early_load(opath)
    gnames = ctx.get('cs_group_names', list(map(str, range(100))))
    groups = csm_groups.list_groups(ctx, path)
    secnum = csm_groups.get_section(ctx, path[0], name1)
    sec2 = csm_groups.get_section(ctx, path[0], name2)
    if secnum != sec2:
        error = 'Users are in different sections! (%s and %s)' % (secnum, sec2)
    else:
        taken = groups.get(secnum, {})
        while len(gnames) > 0 and gnames[0] in taken:
            gnames.pop(0)
        error = csm_groups.add_to_group(ctx, path, name1, gnames[0])
        if error is None:
            error = csm_groups.add_to_group(ctx, path, name2, gnames[0])

if error is not None:
    output = {'ok': False, 'error': error}
else:
    output = {'ok': True}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(output)
