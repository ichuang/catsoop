# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import collections.abc

defaults = {
    'csq_npoints': 1
}

allow_viewanswer = False
allow_self_submit = False
allow_save = False

def total_points(**info):
    return info['csq_npoints']

def handle_submission(submissions, **info):
    if 'real_user' not in info['cs_user_info']:
        percent = 0
        msg = 'You must receive this checkoff from a staff member.'
        l = False
    else:
        import time
        un = info['cs_user_info']['real_user']['username']
        percent = 1
        msg = 'You received this checkoff from %s on %s.' % (un, time.time())
        l = True
    return {'score': percent, 'msg': msg, 'lock': l}

def render_html(last_log, **info):
    return '<b>%s</b>:<br/>%s' % (info['csq_display_name'],
                              info['csq_description'])

def answer_display(**info):
    return "You received this checkoff."
