# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

import re


def handle(context):
    uname = context.get('cs_username', 'None')
    logname = 'staticaccess'
    fname = context['filename']

    user = context['cs_user_info']
    perms = user.get('permissions', [])

    rel = context['csm_tutor'].get_release_date(context)
    ts = context['cs_timestamp']
    current = context['csm_cstime'].from_detailed_timestamp(ts)

    log_entry = {
        k: v
        for (k, v) in context.iteritems()
        if k in {'cs_timestamp', 'cs_path_info', 'cs_ip', 'cs_user_info'}
    }

    m = None

    if 'view' not in perms and 'view_all' not in perms:
        m = 'You are not authorized to view this handout.'
    elif 'view' in perms and current < rel:
        reltime = context['cstime'].short_timestamp(rel)
        m = ('This handout is not yet available.  '
             'It will become available at: %s') % reltime

    log_entry['success'] = m is None
    context['csm_cslog'].update_log(context['cs_course'], uname, logname,
                                    log_entry)

    if m is None:
        return context['csm_web'].serve_static_file(fname, context['cs_env'])
    else:
        return (('200', 'OK'), {'Content-type': 'text/plain',
                                'Content-length': str(len(m))}, m)
