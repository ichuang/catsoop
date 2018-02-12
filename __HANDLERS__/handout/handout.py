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

from http import HTTPStatus


def handle(context):
    uname = context.get('cs_username', 'None')
    logname = 'staticaccess'
    fname = context['filename']

    user = context['cs_user_info']
    perms = user.get('permissions', [])

    rel = context['csm_tutor'].get_release_date(context)
    ts = context['cs_timestamp']
    current = context['csm_time'].from_detailed_timestamp(ts)

    log_entry = {
        k: v
        for (k, v) in context.items()
        if k in {'cs_timestamp', 'cs_path_info', 'cs_user_info'}
    }

    m = None
    status = HTTPStatus.OK

    if 'view' not in perms and 'view_all' not in perms or uname == 'None':
        m = 'You are not authorized to view this handout.'
        status = HTTPStatus.UNAUTHORIZED
    elif 'view' in perms and current < rel:
        reltime = context['csm_time'].short_timestamp(rel)
        m = ('This handout is not yet available.  '
             'It will become available at: %s') % reltime
        status = HTTPStatus.NOT_FOUND

    log_entry['success'] = m is None
    context['csm_cslog'].update_log(uname, [context['cs_course']], logname, log_entry)

    if m is None:
        return context['csm_dispatch'].serve_static_file(context, fname, context['cs_env'])
    else:
        return ((status.value, status.phrase), {'Content-type': 'text/plain',
                                'Content-length': str(len(m))}, m)
