# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/agpl-3.0-standalone.html>.

import base64
import mimetypes

base, _ = csm_tutor.question('smallbox')

always_rerender = True

defaults = base['defaults']
defaults.update({
    'csq_soln_filename': 'solution.txt',
    'csq_allow_save': False,
    'csq_soln_type': 'string',
})

total_points = base['total_points']
answer_display = base['answer_display']


def handle_submission(submissions, **info):
    o = {'score': None, 'msg': '', 'rerender': True}
    name = info['csq_name']
    ll = submissions.get(name, None)
    if ll is not None:
        submissions[name] = csm_data_uri.DataURI(ll[1]).data
        o.update(base['handle_submission'](submissions, **info))
    return o


def render_html(last_log, **info):
    out = '''<input type="file" id=%(name)s name="%(name)s" />'''
    out %= {'name': info['csq_name']}
    ll = last_log.get(info['csq_name'], None)
    if ll is not None:
        try:
            name, data = ll
            out += '<br/>'
            name = '.'.join(info['cs_path_info'] + [info['cs_username'], name])
            out += ('<a href="%s" '
                    'download="%s">Download Most '
                    'Recent Submission</a>') % (data, name)
        except:
            pass
    return out


def answer_display(**info):
    name = info['csq_soln_filename']
    if info['csq_soln_type'] == 'string':
        data = csm_data_uri.DataURI.make('text/plain', None, True,
                                         info['csq_soln'])
    else:
        data = csm_data_uri.DataURI.from_file(info['csq_soln'])
        ext = mimetypes.guess_extension(data.mimetype) or '.txt'
        name = name.rsplit('.', 1) + ext
    return ('<a href="%s" '
            'download="%s">Download Most '
            'Recent Submission</a>') % (data, name)
