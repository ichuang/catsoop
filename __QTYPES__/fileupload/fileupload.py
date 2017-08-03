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
    name = info['csq_name']
    out = '''<input type="file" style="display: none" id=%s name="%s" />''' % (name, name)
    out += ('''<button class="btn btn-catsoop" id="%s_select_button">Select File</button>&nbsp;'''
            '''<tt><span id="%s_selected_file">No file selected</span></tt>''') % (name, name)
    out += ('''<script type="text/javascript">'''
            '''$('#%s_select_button').click(function (){$("#%s").click();});'''
            '''$('#%s').change(function (){$('#%s_selected_file').text($('#%s').val());});'''
            '''</script>''') % (name, name, name, name, name)
    ll = last_log.get(name, None)
    if ll is not None:
        try:
            fname, _ = ll
            data = info['csm_loader'].get_file_data(info, last_log, name)
            out += '<br/>'
            out += ('<a href="%s" '
                    'download="%s">Download Most '
                    'Recent Submission</a>') % (data, fname)
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
