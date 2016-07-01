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

base, _ = tutor.question('pythonic')

defaults = dict(base['defaults'])
defaults.update({
    'csq_soln': '',
    'csq_input_check': lambda sub: None,
    'csq_npoints': 1,
    'csq_msg_function': lambda sub: (''),
    'csq_show_check': False,
    'csq_size': 50,
    'csq_check_function':
    lambda sub, soln: ((type(sub) == type(soln)) and (sub == soln))
})

render_html = base['render_html']
total_points = base['total_points']
answer_display = base['answer_display']


def handle_submission(submissions, **info):
    sub = submissions[info['csq_name']]

    inp = info['csq_input_check'](sub)
    if inp is not None:
        return {'score': 0.0, 'msg': '<font color="red">%s</font>' % inp}

    try:
        ast.literal_eval(sub)
    except:
        return {'score': 0.0, 'msg': 'Value must be a valid Python literal.'}

    return base['handle_submission'](submissions, **info)
