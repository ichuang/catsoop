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

import ast

base1, _ = tutor.question('pythoncode')
base, _ = tutor.question('smallbox')

defaults = dict(base['defaults'])
defaults.update({
    'csq_soln': '',
    'csq_check_function':
    lambda sub, soln: (type(sub) == type(soln)) and (sub == soln),
    'csq_input_check': lambda sub: None,
    'csq_npoints': 1,
    'csq_msg_function': lambda sub: (''),
    'csq_show_check': False,
    'csq_code_pre': '',
    'csq_mode': 'raw',
    'csq_size': 50
})

render_html = base['render_html']
total_points = base['total_points']


def handle_submission(submissions, **info):
    py3k = info.get('csq_python3', True)
    sub = submissions[info['csq_name']]

    inp = info['csq_input_check'](sub)
    if inp is not None:
        return {'score': 0.0, 'msg': '<font color="red">%s</font>' % inp}

    base1['get_sandbox'](info)
    if info['csq_mode'] == 'raw':
        soln = info['csq_soln']
    else:
        code = info['csq_code_pre']
        if py3k:
            code += '\nprint(repr(%s))' % info['csq_soln']
        else:
            code += '\nprint repr(%s)' % info['csq_soln']
        opts = info.get('csq_options', {})
        soln = eval(info['sandbox_run_code'](info, code, opts)[1], info)
    try:
        code = info['csq_code_pre']
        if py3k:
            code += '\nprint(repr(%s))' % sub
        else:
            code += '\nprint repr(%s)' % sub
        opts = info.get('csq_options', {})
        sub = eval(info['sandbox_run_code'](info, code, opts)[1], info)
    except:
        return {'score': 0.0,
                'msg': info['csq_msg_function'](submissions[info['csq_name']])}

    try:
        percent = float(info['csq_check_function'](sub, soln))
    except:
        percent = 0.0

    msg = ''
    if info['csq_show_check']:
        if percent == 1.0:
            msg = '<img src="BASE/images/check.png" />'
        elif percent == 0.0:
            msg = '<img src="BASE/images/cross.png" />'

    msg += info['csq_msg_function'](submissions[info['csq_name']])

    return {'score': percent, 'msg': msg}


def answer_display(**info):
    if info['csq_mode'] == 'raw':
        out = "<p>Solution: <tt>%r</tt><p>" % (info['csq_soln'], )
    else:
        out = "<p>Solution: <tt>%s</tt><p>" % (info['csq_soln'], )
    return out
