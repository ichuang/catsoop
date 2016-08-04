# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import ast

base, _ = tutor.question('pythonic')

defaults = dict(base['defaults'])

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
