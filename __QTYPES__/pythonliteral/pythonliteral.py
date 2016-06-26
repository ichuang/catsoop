# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

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
