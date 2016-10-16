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
path = cs_form.get('path', None)
username = cs_form.get('username', None)
group = cs_form.get('group', None)

error = None

if api_token is None:
    error = "api_token is required"
elif username is None:
    error = "username is required"
elif group is None:
    error = "group is required"

try:
    path = opath = json.loads(path)
    course, path = path[0], path[1:]
except:
    error = "invalid path: %s" % path

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token, course=course)
    if output['ok']:
        uinfo = output['user_info']
        if 'groups' not in uinfo['permissions'] and 'admin' not in uinfo['permissions']:
            error = 'Permission Denied'

if error is None:
    ctx = csm_loader.spoof_early_load(opath)
    error = csm_groups.remove_from_group(ctx, course, path, username, group)

if error is not None:
    output = {'ok': False, 'error': error}
else:
    output = {'ok': True}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(output)
