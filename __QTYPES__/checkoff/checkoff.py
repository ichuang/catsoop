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
        un = submissions[info['csq_name']]
        new = dict(info)
        new['cs_form'] = {}
        uinfo = info['csm_auth']._get_user_information(new,
                                                       new,
                                                       info['cs_course'],
                                                       un,
                                                       True)
        if 'checkoff' not in uinfo.get('permissions', []):
            percent = 0
            msg = '%s is not allowed to give checkoffs.' % un
            l = False
        else:
            percent = 1
            now = info['csm_time'].from_detailed_timestamp(info['cs_timestamp'])
            now = info['csm_time'].long_timestamp(now).replace('; ', ' at ')
            msg = 'You received this checkoff from %s on %s.' % (un, now)
            l = True
    return {'score': percent, 'msg': msg, 'lock': l}

def render_html(last_log, **info):
    info['csq_description'] = info['csm_language'].source_transform_string(info, info['csq_description'])
    return '<b>%s</b>:<br/>%s' % (info['csq_display_name'],
                              info['csq_description'])

def answer_display(**info):
    return "You received this checkoff."
