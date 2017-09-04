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

import os
import json
import time
import uuid
import sqlite3

api_token = cs_form.get('api_token', None)
course = cs_form.get('course', None)
room = cs_form.get('room', 'default')
description = cs_form.get('description', '')
location = cs_form.get('location', '')
type_ = cs_form.get('type', 'help')
extra_data = cs_form.get('extra_data', '{}')

error = None

if api_token is None:
    error = "api_token is required"
elif course is None:
    error = "course is required"
elif not os.path.isdir(os.path.join(cs_data_root, 'courses', course)):
    error = 'unknown course: %s' % course

if error is None:
    output = csm_api.get_user_information(globals(), api_token=api_token, course=course)
    if output['ok']:
        uinfo = output['user_info']
        if 'queue' not in uinfo['permissions'] and 'queue_staff' not in uinfo['permissions']:
            error = 'Permission Denied'
    else:
        error = 'Could not authenticate %r' % output

if error is None:
    now = time.time()
    db_loc = os.path.join(cs_data_root, '__LOGS__', '_queue.db')
    photo_dir = os.path.join(cs_data_root, 'courses', course, '__PHOTOS__')
    try:
        possible_photos = [i for i in os.listdir(photo_dir) if i.rsplit('.', 1)[0] == uinfo['username']]
    except:
        possible_photos = []
    if len(possible_photos) == 0:
        photo = None
    else:
        pname = os.path.join(photo_dir, possible_photos[0])
        photo = csm_tools.data_uri.DataURI.from_file(pname)
    conn = sqlite3.connect(db_loc)
    conn.text_factory = str
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO queues VALUES (COALESCE((SELECT id FROM queues WHERE username=? AND course=? AND room=?),?), ?, ?, ?, ?, ?, ?, COALESCE((SELECT started_time FROM queues WHERE username=? AND course=? AND room=?),?), ?, ?, ?, NULL, ?, ?)',
              (uinfo['username'], course, room, uuid.uuid4().hex, uinfo['username'], course, room, type_, description, location, uinfo['username'], course, room, now, now, True, json.dumps([]), photo, extra_data))
    conn.commit()
    conn.close()

if error is not None:
    output = {'ok': False, 'error': error}
else:
    output = {'ok': True}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(output)
