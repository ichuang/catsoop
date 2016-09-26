# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import base64
import mimetypes

tutor.qtype_inherit('smallbox')
base, _ = tutor.question("smallbox")

always_rerender = True

defaults.update({
    'csq_soln_filename': 'solution.txt',
    'csq_allow_save': False,
    'csq_soln_type': 'string',
})


def handle_submission(submissions, **info):
    o = {'score': None, 'msg': '', 'rerender': True}
    name = info['csq_name']
    ll = submissions.get(name, None)
    if ll is not None:
        submissions[name] = csm_tools.data_uri.DataURI(ll[1]).data
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
        data = csm_tools.data_uri.DataURI.make('text/plain', None, True,
                                         info['csq_soln'])
    else:
        data = csm_tools.data_uri.DataURI.from_file(info['csq_soln'])
        ext = mimetypes.guess_extension(data.mimetype) or '.txt'
        name = name.rsplit('.', 1) + ext
    return ('<a href="%s" '
            'download="%s">Download Most '
            'Recent Submission</a>') % (data, name)
