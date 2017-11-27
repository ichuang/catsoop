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

import os
import re
import json
import time
import uuid
import random
import shutil
import string
import sqlite3
import tempfile
import traceback
import collections


_prefix = 'cs_defaulthandler_'

def new_entry(context, qname, action):
    id_ = str(uuid.uuid4())
    obj = {'path': context['cs_path_info'],
           'username': context.get('cs_username', 'None'),
           'names': [qname],
           'form': {k: v for k, v in context[_n('form')].items() if qname in k},
           'time': time.time(),
           'action': action}
    loc = os.path.join(tempfile.gettempdir(), 'staging', id_)
    os.makedirs(os.path.dirname(loc), exist_ok=True)
    with open(loc, 'wb') as f:
        f.write(context['csm_cslog'].prep(obj))
    newloc = os.path.join(context['cs_data_root'], '__LOGS__', '_checker', 'queued', '%s_%s' % (time.time(), id_))
    shutil.move(loc, newloc)
    return id_


def _n(n):
    return "%s%s" % (_prefix, n)


def _unknown_handler(action):
    return lambda x: 'Unknown Action: %s' % action


def _get(context, key, default, cast=lambda x: x):
    v = context.get(key, default)
    return cast(v(context) if isinstance(v, collections.Callable) else v)


def handle(context):
    # set some variables in context
    pre_handle(context)

    mode_handlers = {'view': handle_view,
                     'submit': handle_submit,
                     'check': handle_check,
                     'save': handle_save,
                     'viewanswer': handle_viewanswer,
                     'clearanswer': handle_clearanswer,
                     'viewexplanation': handle_viewexplanation,
                     'content_only': handle_content_only,
                     'raw_html': handle_raw_html,
                     'copy': handle_copy,
                     'copy_seed': handle_copy_seed,
                     'activate': handle_activate,
                     'lock': handle_lock,
                     'unlock': handle_unlock,
                     'grade': handle_grade,
                     'passthrough': lambda c: '',
                     'new_seed': handle_new_seed,
                     'list_questions': handle_list_questions,
                     'get_state': handle_get_state,
                     'manage_groups': manage_groups,
                     'render_single_question': handle_single_question,
                     'stats': handle_stats,
                     'whdw': handle_whdw,
                     }

    action = context[_n('action')]
    return mode_handlers.get(action, _unknown_handler(action))(context)


def handle_list_questions(context):
    types = {k: v[0]['qtype'] for k,v in context[_n('name_map')].items()}
    order = list(context[_n('name_map')])
    return make_return_json(context, {'order': order, 'types': types}, [])


def handle_get_state(context):
    ll = context[_n('last_log')]
    for i in ll:
        if isinstance(ll[i], set):
            ll[i] = list(ll[i])
    ll['scores'] = {}
    for k, v in ll.get('last_submit_checker_id', {}).items():
        try:
            with open(os.path.join(context['cs_data_root'], '__LOGS__', '_checker', 'results', v), 'rb') as f:
                row = context['csm_cslog'].unprep(f.read())
        except:
            row = None
        if row is None:
            ll['scores'][k] = 0.0
        else:
            ll['scores'][k] = row['score'] or 0.0
    return make_return_json(context, ll, [])


def handle_single_question(context):
    lastlog = context[_n('last_log')]
    lastsubmit = lastlog.get('last_submit', {})

    qname = context['cs_form'].get('name', None)
    elt = context[_n('name_map')][qname]

    o = render_question(elt, context, lastsubmit, wrap=False)
    return ('200', 'OK'), {'Content-type': 'text/html'}, o


def handle_copy_seed(context):
    if context[_n('impersonating')]:
        impersonated = context[_n('uname')]
        uname = context[_n('real_uname')]
        path = context['cs_path_info']
        logname = 'random_seed'
        stored = context['csm_cslog'].most_recent(impersonated, path,
                                                  logname, None)
        context['csm_cslog'].update_log(uname, path, logname, stored)
    return handle_save(context)


def _new_random_seed(n=100):
    try:
        return os.urandom(n)
    except:
        return ''.join(random.choice(string.ascii_letters) for i in range(n))


def handle_new_seed(context):
    uname = context[_n('uname')]
    context['csm_cslog'].update_log(uname, context['cs_path_info'],
                                    'random_seed', _new_random_seed())

    # Rerender the questions
    names = context[_n('question_names')]
    outdict = {}
    for name in names:
        outdict[name] = {'rerender': 'Please refresh the page'}

    return make_return_json(context, outdict)


def handle_activate(context):
    submitted_pass = context[_n('form')].get('activation_password', '')
    if submitted_pass == context[_n('activation_password')]:
        newstate = dict(context[_n('last_log')])
        newstate['activated'] = True

        uname = context[_n('uname')]
        context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                           'problemstate', newstate)
        context[_n('last_log')] = newstate
    return handle_view(context)


def handle_copy(context):
    if context[_n('impersonating')]:
        context[_n('uname')] = context[_n('real_uname')]
        ll = context['csm_cslog'].most_recent(context[_n('uname')],
                                              context['cs_path_info'],
                                              'problemstate', {})
        context[_n('last_log')] = ll
    return handle_save(context)


def handle_activation_form(context):
    context['cs_content_header'] = 'Problem Activation'
    out = '<form method="POST">'
    out += ('\nActivation Password: '
            '<input type="text" '
            'name="activation_password" '
            'value="" />'
            '\n&nbsp;'
            '\n<input type="submit" '
            'name="action" '
            'value="Activate" />')
    if 'admin' in context[_n('perms')]:
        pwd = context[_n('activation_password')]
        out += ('\n<p><u>Staff:</u> password is '
                '<tt><font color="blue">%s</font></tt>') % pwd
    out += '</form>'

    p = context[_n('perms')]
    if 'submit' in p or 'submit_all' in p:
        log_action(context, {'action': 'show_activation_form'})

    return out


def handle_raw_html(context):
    # base function: display the problem
    perms = context[_n('perms')]

    lastlog = context[_n('last_log')]
    lastsubmit = lastlog.get('last_submit', {})

    if (_get(context, 'cs_auth_required', True, bool) and
            'view' not in perms and 'view_all' not in perms):
        return 'You are not allowed to view this page.'

    if (_get(context, 'cs_require_activation', False, bool) and
            not lastlog.get('activated', False)):
        return 'You must activate this page first.'

    due = context[_n('due')]
    timing = context[_n('timing')]

    if timing == -1 and ('view_all' not in perms):
        reltime = context['csm_time'].long_timestamp(context[_n('rel')])
        reltime = reltime.replace(';', ' at')
        return ('This page is not yet available.  '
                'It will become available on %s.') % reltime

    if 'submit' in perms or 'submit_all' in perms:
        # only log an entry for users who can submit
        log_action(context, {'action': 'view',
                             'score': lastlog.get('score', 0.0)})

    page = ''
    num_questions = len(context[_n('name_map')])
    if (num_questions > 0 and _get(context, 'cs_show_due', True, bool) and
            context.get('cs_due_date', 'NEVER') != 'NEVER'):
        duetime = context['csm_time'].long_timestamp(due)
        page += ('<tutoronly><center>'
                 'The questions below are due on %s.'
                 '<br/><hr><br/></center></tutoronly>') % duetime

    for elt in context['cs_problem_spec']:
        if isinstance(elt, str):
            page += elt
        else:
            # this is a question
            page += render_question(elt, context, lastsubmit)

    page += default_javascript(context)
    page += default_timer(context)
    context['cs_template'] = 'BASE/templates/empty.template'
    return page


def handle_content_only(context):
    # base function: display the problem
    perms = context[_n('perms')]

    lastlog = context[_n('last_log')]
    lastsubmit = lastlog.get('last_submit', {})

    if (_get(context, 'cs_auth_required', True, bool) and
            'view' not in perms and 'view_all' not in perms):
        return 'You are not allowed to view this page.'

    if (_get(context, 'cs_require_activation', False, bool) and
            not lastlog.get('activated', False)):
        return 'You must activate this page first.'

    due = context[_n('due')]
    timing = context[_n('timing')]

    if timing == -1 and ('view_all' not in perms):
        reltime = context['csm_time'].long_timestamp(context[_n('rel')])
        reltime = reltime.replace(';', ' at')
        return ('This page is not yet available.  '
                'It will become available on %s.') % reltime

    if 'submit' in perms or 'submit_all' in perms:
        # only log an entry for users who can submit
        log_action(context, {'action': 'view',
                             'score': lastlog.get('score', 0.0)})

    page = ''
    num_questions = len(context[_n('name_map')])
    if (num_questions > 0 and _get(context, 'cs_show_due', True, bool) and
            context.get('cs_due_date', 'NEVER') != 'NEVER'):
        duetime = context['csm_time'].long_timestamp(due)
        page += ('<tutoronly><center>'
                 'The questions below are due on %s.'
                 '<br/><hr><br/></center></tutoronly>') % duetime

    for elt in context['cs_problem_spec']:
        if isinstance(elt, str):
            page += elt
        else:
            # this is a question
            page += render_question(elt, context, lastsubmit)

    page += default_javascript(context)
    page += default_timer(context)
    context['cs_template'] = 'BASE/templates/noborder.template'
    return page

def handle_view(context):
    # base function: display the problem
    perms = context[_n('perms')]

    lastlog = context[_n('last_log')]
    lastsubmit = lastlog.get('last_submit', {})

    if (_get(context, 'cs_auth_required', True, bool) and
            'view' not in perms and 'view_all' not in perms):
        return 'You are not allowed to view this page.'

    if (_get(context, 'cs_require_activation', False, bool) and
            not lastlog.get('activated', False)):
        return handle_activation_form(context)

    due = context[_n('due')]
    timing = context[_n('timing')]

    if timing == -1 and ('view_all' not in perms):
        reltime = context['csm_time'].long_timestamp(context[_n('rel')])
        reltime = reltime.replace(';', ' at')
        return ('This page is not yet available.  '
                'It will become available on %s.') % reltime

    if 'submit' in perms or 'submit_all' in perms:
        # only log an entry for users who can submit
        log_action(context, {'action': 'view',
                             'score': lastlog.get('score', 0.0)})

    page = ''
    num_questions = len(context[_n('name_map')])
    if (num_questions > 0 and _get(context, 'cs_show_due', True, bool) and
            context.get('cs_due_date', 'NEVER') != 'NEVER'):
        duetime = context['csm_time'].long_timestamp(due)
        page += ('<tutoronly><center>'
                 'The questions below are due on %s.'
                 '<br/><hr><br/></center></tutoronly>') % duetime

    for elt in context['cs_problem_spec']:
        if isinstance(elt, str):
            page += elt
        else:
            # this is a question
            page += render_question(elt, context, lastsubmit)

    page += default_javascript(context)
    page += default_timer(context)
    return page


def get_manual_grading_entry(context, name):
    uname = context['cs_user_info'].get('username', 'None')
    log = context['csm_cslog'].read_log(uname, context['cs_path_info'],
                                        'problemgrades')
    out = None
    for i in log:
        if i['qname'] == name:
            out = i
    return out


def handle_clearanswer(context):
    names = context[_n('question_names')]
    due = context[_n('due')]
    lastlog = context[_n('last_log')]
    answerviewed = context[_n('answer_viewed')]
    explanationviewed = context[_n('explanation_viewed')]

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    outdict = {}  # dictionary containing the responses for each question
    for name in names:
        out = {}

        error = clearanswer_msg(context, context[_n('perms')], name)
        if error is not None:
            out['error_msg'] = error
            outdict[name] = out
            continue

        q, args = context[_n('name_map')][name]

        out['clear'] = True
        outdict[name] = out

        answerviewed.discard(name)
        explanationviewed.discard(name)

    newstate['answer_viewed'] = answerviewed
    newstate['explanation_viewed'] = explanationviewed

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    log_action(context, {'action': 'viewanswer',
                         'names': names,
                         'score': newstate.get('score', 0.0),
                         'response': outdict,
                         'due_date': duetime})

    return make_return_json(context, outdict)


def explanation_display(x):
    return '<hr /><p><b>Explanation:</b></p>%s' % x


def handle_viewexplanation(context):
    names = context[_n('question_names')]
    due = context[_n('due')]
    lastlog = context[_n('last_log')]
    explanationviewed = context[_n('explanation_viewed')]
    loader = context['csm_loader']
    language = context['csm_language']

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    outdict = {}  # dictionary containing the responses for each question
    for name in names:
        out = {}

        error = viewexp_msg(context, context[_n('perms')], name)
        if error is not None:
            out['error_msg'] = error
            outdict[name] = out
            continue

        q, args = context[_n('name_map')][name]
        exp = explanation_display(args['csq_explanation'])
        out['explanation'] = language.source_transform_string(context, exp)
        outdict[name] = out

        explanationviewed.add(name)

    newstate['explanation_viewed'] = explanationviewed

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    log_action(context, {'action': 'viewanswer',
                         'names': names,
                         'score': newstate.get('score', 0.0),
                         'response': outdict,
                         'due_date': duetime})

    return make_return_json(context, outdict)


def handle_viewanswer(context):
    names = context[_n('question_names')]
    due = context[_n('due')]
    lastlog = context[_n('last_log')]
    answerviewed = context[_n('answer_viewed')]
    loader = context['csm_loader']
    language = context['csm_language']

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    outdict = {}  # dictionary containing the responses for each question
    for name in names:
        out = {}

        error = viewanswer_msg(context, context[_n('perms')], name)
        if error is not None:
            out['error_msg'] = error
            outdict[name] = out
            continue

        q, args = context[_n('name_map')][name]

        # if we are here, no errors occurred.  go ahead with checking.
        ans = q['answer_display'](**args)
        out['answer'] = language.source_transform_string(context, ans)
        outdict[name] = out

        answerviewed.add(name)

    newstate['answer_viewed'] = answerviewed

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    log_action(context, {'action': 'viewanswer',
                         'names': names,
                         'score': newstate.get('score', 0.0),
                         'response': outdict,
                         'due_date': duetime})

    return make_return_json(context, outdict)


def handle_lock(context):
    names = context[_n('question_names')]
    due = context[_n('due')]
    lastlog = context[_n('last_log')]
    locked = context[_n('locked')]

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    outdict = {}  # dictionary containing the responses for each question
    for name in names:
        q, args = context[_n('name_map')][name]
        outdict[name] = {}
        locked.add(name)

        # automatically view the answer if the option is set
        if 'lock' in _get_auto_view(args) and q.get('allow_viewanswer', True) and _get(args, 'csq_allow_viewanswer', True, bool):
            if name not in newstate.get('answer_viewed', set()):
                c = dict(context)
                c[_n('question_names')] = [name]
                o = json.loads(handle_viewanswer(c)[2])
                ll = context['csm_cslog'].most_recent(
                    context.get('cs_username', 'None'),
                    context['cs_path_info'],
                    'problemstate', {})
                newstate['answer_viewed'] = ll.get('answer_viewed', set())
                newstate['explanation_viewed'] = ll.get('explanation_viewed',
                                                        set())
                outdict[name].update(o[name])

    newstate['locked'] = locked

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    log_action(context, {'action': 'lock',
                         'names': names,
                         'score': newstate.get('score', 0.0),
                         'response': outdict,
                         'due_date': duetime})

    return make_return_json(context, outdict)


def handle_grade(context):
    names = context[_n('question_names')]
    perms = context[_n('perms')]

    newentries = []
    outdict = {}
    for name in names:
        if name.endswith('_grading_score') or name.endswith(
                '_grading_comments'):
            continue
        error = grade_msg(context, perms, name)
        if error is not None:
            outdict[name] = {'error_msg': error}
            continue
        q, args = context[_n('name_map')][name]
        npoints = float(q['total_points'](**args))
        try:
            f = context[_n('form')]
            rawscore = f.get('%s_grading_score' % name, '')
            comments = f.get('%s_grading_comments' % name, '')
            score = float(rawscore)
        except:
            outdict[name] = {'error_msg': 'Invalid score: %s' % rawscore}
            continue
        newentries.append({'qname': name,
                           'grader': context[_n('real_uname')],
                           'score': score / npoints,
                           'comments': comments,
                           'timestamp': context['cs_timestamp']})
        _, args = context[_n('name_map')][name]
        outdict[name] = {
            'score_display': context['csm_tutor'].make_score_display(context, args, name, score),
            'message': "<b>Grader's Comments:</b><br/><br/>%s" % context['csm_language']._md_format_string(context, comments),
            'score': score,
        }

    # update problemstate log
    uname = context[_n('uname')]
    for i in newentries:
        context['csm_cslog'].update_log(uname, context['cs_path_info'],
                                        'problemgrades', i)

    # log submission in problemactions
    log_action(context, {'action': 'grade',
                         'names': names,
                         'scores': newentries,
                         'grader': context[_n('real_uname')]})

    return make_return_json(context, outdict, names=list(outdict.keys()))


def handle_unlock(context):
    names = context[_n('question_names')]
    due = context[_n('due')]
    lastlog = context[_n('last_log')]
    locked = context[_n('locked')]

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    outdict = {}  # dictionary containing the responses for each question
    for name in names:
        q, args = context[_n('name_map')][name]
        outdict[name] = {}
        locked.remove(name)

    newstate['locked'] = locked

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    log_action(context, {'action': 'unlock',
                         'names': names,
                         'score': newstate.get('score', 0.0),
                         'response': outdict,
                         'due_date': duetime})

    return make_return_json(context, outdict)


def handle_save(context):
    names = context[_n('question_names')]
    due = context[_n('due')]

    lastlog = context[_n('last_log')]

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    outdict = {}  # dictionary containing the responses for each question
    saved_names = []
    for name in names:
        out = {}

        error = save_msg(context, context[_n('perms')], name)
        if error is not None:
            out['error_msg'] = error
            outdict[name] = out
            continue

        question, args = context[_n('name_map')].get(name)
        sub = context[_n('form')].get(name, '')

        if sub == "":  # don't overwrite things with blank strings
            outdict[name] = {}
            continue

        saved_names.append(name)

        # if we are here, no errors occurred.  go ahead with checking.
        newstate['last_submit'][name] = sub

        rerender = args.get('csq_rerender', question.get('always_rerender', False))
        if rerender is True:
            out['rerender'] = context['csm_language'].source_transform_string(context, args.get(
                                                                              'csq_prompt', ''))
            out['rerender'] += question['render_html'](newstate['last_submit'],
                                                       **args)
        elif rerender:
            out['rerender'] = rerender

        out['score_display'] = ''
        out['message'] = ''
        outdict[name] = out

        # cache responses
        newstate['%s_score_display' % name] = out['score_display']
        newstate['%s_message' % name] = out['message']

    # update problemstate log
    if len(saved_names) > 0:
        uname = context[_n('uname')]
        context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                           'problemstate', newstate)

        # log submission in problemactions
        duetime = context['csm_time'].detailed_timestamp(due)
        subbed = {n: context[_n('form')].get(n, '') for n in saved_names}
        log_action(context, {'action': 'save',
                             'names': saved_names,
                             'submitted': subbed,
                             'score': newstate.get('score', 0.0),
                             'response': outdict,
                             'due_date': duetime})

    return make_return_json(context, outdict)


def handle_check(context):
    names = context[_n('question_names')]
    due = context[_n('due')]

    lastlog = context[_n('last_log')]
    namemap = context[_n('name_map')]

    newstate = dict(lastlog)
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}

    names_done = set()
    outdict = {}  # dictionary containing the responses for each question

    entry_ids = {}
    if 'last_checker_id' not in newstate:
        newstate['last_checker_id'] = {}

    for name in names:
        if name.startswith('__'):
            name = name[2:].rsplit('_', 1)[0]
        if name in names_done:
            continue
        out = {}
        sub = context[_n('form')].get(name, '')

        # if we are here, no errors occurred.  go ahead with checking.
        newstate['last_submit'][name] = sub
        question, args = namemap[name]

        magic = new_entry(context, name, 'check')

        entry_ids[name] = entry_id = magic

        rerender = args.get('csq_rerender', question.get('always_rerender', False))
        if rerender is True:
            out['rerender'] = question['render_html'](newstate['last_submit'],
                                                      **args)
        elif rerender:
            out['rerender'] = rerender

        out['score_display'] = ''
        out['message'] = WEBSOCKET_RESPONSE % {'name': name, 'magic': entry_id,
                                               'websocket': context['cs_checker_websocket'],
                                               'loading': context['cs_loading_image'],
                                               'id_css': (' style="display:none;"'
                                                          if context.get('cs_show_submission_id', True)
                                                          else '')}
        out['magic'] = entry_id

        outdict[name] = out

        # cache responses
        newstate['last_checker_id'][name] = entry_id
        newstate['%s_score_display' % name] = ''
        msg_key = '%s_message' % name
        if msg_key in newstate:
            del newstate[msg_key]
        newstate['%s_magic' % name] = entry_id

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    subbed = {n: context[_n('form')].get(n, '') for n in names}
    log_action(context, {'action': 'check',
                         'names': names,
                         'submitted': subbed,
                         'checker_ids': entry_ids,
                         'due_date': duetime})

    return make_return_json(context, outdict)


def handle_submit(context):
    names = context[_n('question_names')]
    due = context[_n('due')]

    lastlog = context[_n('last_log')]
    nsubmits_used = context[_n('nsubmits_used')]

    namemap = context[_n('name_map')]

    newstate = dict(lastlog)

    newstate['last_submit_time'] = context['cs_timestamp']
    newstate['last_submit_times'] = newstate.get('last_submit_times', {})
    newstate['timestamp'] = context['cs_timestamp']
    if 'last_submit' not in newstate:
        newstate['last_submit'] = {}
    if 'last_checker_id' not in newstate:
        newstate['last_checker_id'] = {}
    if 'last_submit_checker_id' not in newstate:
        newstate['last_submit_checker_id'] = {}

    names_done = set()
    outdict = {}  # dictionary containing the responses for each question

    # here, we don't do a whole lot.  we log a submission and add it to the
    # checker's queue.

    entry_ids = {}

    for name in names:
        if name.startswith('__'):
            name = name[2:].rsplit('_', 1)[0]
        if name in names_done:
            continue

        names_done.add(name)
        newstate['last_submit_times'][name] = context['cs_timestamp']
        out = {}
        sub = context[_n('form')].get(name, '')

        error = submit_msg(context, context[_n('perms')], name)
        if error is not None:
            out['error_msg'] = error
            outdict[name] = out
            continue

        # if we are here, no errors occurred.  go ahead with submitting.
        nsubmits_used[name] = nsubmits_used.get(name, 0) + 1
        newstate['last_submit'][name] = sub

        question, args = namemap[name]
        grading_mode = _get(args, 'csq_grading_mode', 'auto', str)
        if grading_mode == 'auto':
            magic = new_entry(context, name, 'submit')

            entry_ids[name] = entry_id = magic

            out['message'] = WEBSOCKET_RESPONSE % {'name': name, 'magic': entry_id,
                                                   'websocket': context['cs_checker_websocket'],
                                                   'loading': context['cs_loading_image'],
                                                   'id_css': (' style="display:none;"'
                                                              if context.get('cs_show_submission_id', True)
                                                              else '')}
            out['magic'] = entry_id
            out['score_display'] = ''
            msg_key = '%s_message' % name
            if msg_key in newstate:
                del newstate[msg_key]
            newstate['%s_magic' % name] = entry_id
            newstate['last_checker_id'][name] = entry_id
            newstate['last_submit_checker_id'][name] = entry_id
        elif grading_mode == 'manual':
            out['message'] = 'Submission received for manual grading.'
            out['score_display'] = context['csm_tutor'].make_score_display(
                context, args, name, None,
                assume_submit=True)
            mag_key = '%s_magic' % name
            if mag_key in newstate:
                del newstate[mag_key]
            newstate['%s_message' % name] = out['message']
        else:
            out['message'] = '<font color="red">Unknown grading mode: %s.  Please contact staff.</font>' % grading_mode
            out['score_display'] = context['csm_tutor'].make_score_display(
                context, args, name, 0.0,
                assume_submit=True)
            mag_key = '%s_magic' % name
            if mag_key in newstate:
                del newstate[mag_key]
            newstate['%s_message' % name] = out['message']

        rerender = args.get('csq_rerender', question.get('always_rerender', False))
        if rerender is True:
            out['rerender'] = question['render_html'](newstate['last_submit'],
                                                      **args)
        elif rerender:
            out['rerender'] = rerender

        outdict[name] = out

        # cache responses
        newstate['%s_score_display' % name] = out['score_display']

    context[_n('nsubmits_used')] = newstate['nsubmits_used'] = nsubmits_used

    # update problemstate log
    uname = context[_n('uname')]
    context['csm_cslog'].overwrite_log(uname, context['cs_path_info'],
                                       'problemstate', newstate)

    # log submission in problemactions
    duetime = context['csm_time'].detailed_timestamp(due)
    subbed = {n: context[_n('form')].get(n, '') for n in names}
    log_action(context, {'action': 'submit',
                         'names': names,
                         'submitted': subbed,
                         'checker_ids': entry_ids,
                         'due_date': duetime})

    context['csm_loader'].run_plugins(context, context['cs_course'], 'post_submit', context)

    return make_return_json(context, outdict)


def manage_groups(context):
    # displays the screen to admins who are adjusting groups
    perms = context['cs_user_info'].get('permissions', [])
    if 'groups' not in perms and 'admin' not in perms:
        return 'You are not allowed to view this page.'
    # show the main partnering page
    section = context['cs_user_info'].get('section', None)
    default_section = context.get('cs_default_section', 'default')
    all_sections = context.get('cs_sections', [])
    if len(all_sections) == 0:
        all_sections = {default_section: 'Default Section'}
    if section is None:
        section = default_section
    hdr = ('Group Assignments for %s, Section '
           '<span id="cs_groups_section">%s</span>')
    hdr %= (context['cs_original_path'], section)
    context['cs_content_header'] = hdr

    # menu for choosing section to display
    out = '\nShow Current Groups for Section:\n<select name="section" id="section">'
    for i in sorted(all_sections):
        s = ' selected' if str(i) == str(section) else ''
        out += '\n<option value="%s"%s>%s</option>' % (i, s, i)
    out += '\n</select>'

    # empty table that will eventually be populated with groups
    out += ('\n<p>\n<h2>Groups:</h2>'
            '\n<div id="cs_groups_table" border="1" align="left">'
            '\nLoading...'
            '\n</div>')

    # create partnership from two students
    out += ('\n<p>\n<h2>Make New Partnership:</h2>'
            '\nStudent 1: <select name="cs_groups_name1" id="cs_groups_name1">'
            '</select>&nbsp;'
            '\nStudent 2: <select name="cs_groups_name2" id="cs_groups_name2">'
            '</select>&nbsp;'
            '\n<button class="btn btn-catsoop" id="cs_groups_newpartners">Partner Students</button>'
            '</p>')

    # add a student to a group
    out += ('\n<p>\n<h2>Add Student to Group:</h2>'
            '\nStudent: <select name="cs_groups_nameadd" id="cs_groups_nameadd">'
            '</select>&nbsp;'
            '\nGroup: <select name="cs_groups_groupadd" id="cs_groups_groupadd">'
            '</select>&nbsp;'
            '\n<button class="btn btn-catsoop" id="cs_groups_addtogroup">Add to Group</button></p>')

    # randomly assign all groups.  this needs to be sufficiently scary...
    out += ('\n<p><h2>Randomly assign groups</h2>'
            '\n<button class="btn btn-catsoop" id="cs_groups_reassign">Reassign Groups</button></p>')

    all_group_names = context.get('cs_group_names', None)
    if all_group_names is None:
        all_group_names = map(str, range(100))
    else:
        all_group_names = sorted(all_group_names)
    all_group_names = list(all_group_names)
    out += '\n<script type="text/javascript">catsoop.group_names = %s</script>' % all_group_names
    out += '\n<script type="text/javascript" src="__HANDLER__/default/cs_groups.js"></script>'
    return out + default_javascript(context)


def clearanswer_msg(context, perms, name):
    namemap = context[_n('name_map')]
    timing = context[_n('timing')]
    ansviewed = context[_n('answer_viewed')]
    i = context[_n('impersonating')]
    _, qargs = namemap[name]
    error = None
    if ('submit' not in perms and 'submit_all' not in perms):
        error = ('You are not allowed undo your viewing of '
                 'the answer to this question.')
    elif name not in ansviewed:
        error = "You have not viewed the answer for this question."
    elif name not in namemap:
        error = ('No question with name %s.  '
                 'Please refresh before submitting.') % name
    elif 'submit_all' not in perms:
        if timing == -1 and not i:
            error = 'This question is not yet available.'
        if not qargs.get('csq_allow_submit_after_answer_viewed', False):
            error = ('You are not allowed to undo your viewing of '
                     'the answer to this question.')
    return error


def viewexp_msg(context, perms, name):
    namemap = context[_n('name_map')]
    timing = context[_n('timing')]
    ansviewed = context[_n('answer_viewed')]
    expviewed = context[_n('explanation_viewed')]
    _, qargs = namemap[name]
    error = None
    if ('submit' not in perms and 'submit_all' not in perms):
        error = 'You are not allowed to view the answer to this question.'
    elif name not in ansviewed:
        error = 'You have not yet viewed the answer for this question.'
    elif name in expviewed:
        error = 'You have already viewed the explanation for this question.'
    elif name not in namemap:
        error = ('No question with name %s.  '
                 'Please refresh before submitting.') % name
    elif ('submit_all' not in perms) and timing == -1:
        error = 'This question is not yet available.'
    elif not _get(qargs, 'csq_allow_viewexplanation', True, bool):
        error = 'Viewing explanations is not allowed for this question.'
    else:
        q, args = namemap[name]
        if 'csq_explanation' not in args:
            error = 'No explanation supplied for this question.'
    return error


def viewanswer_msg(context, perms, name):
    namemap = context[_n('name_map')]
    timing = context[_n('timing')]
    ansviewed = context[_n('answer_viewed')]
    i = context[_n('impersonating')]
    _, qargs = namemap[name]
    error = None

    if not _.get('allow_viewanswer', True):
        error = 'You cannot view the answer to this type of question.'
    elif ('submit' not in perms and 'submit_all' not in perms):
        error = 'You are not allowed to view the answer to this question.'
    elif name in ansviewed:
        error = 'You have already viewed the answer for this question.'
    elif name not in namemap:
        error = ('No question with name %s.  '
                 'Please refresh before submitting.') % name
    elif 'submit_all' not in perms:
        if timing == -1 and not i:
            error = 'This question is not yet available.'
        elif not _get(qargs, 'csq_allow_viewanswer', True, bool):
            error = 'Viewing the answer is not allowed for this question.'
    return error


def save_msg(context, perms, name):
    namemap = context[_n('name_map')]
    timing = context[_n('timing')]
    i = context[_n('impersonating')]
    _, qargs = namemap[name]
    error = None
    if not _.get('allow_save', True):
        error = 'You cannot save this type of question.'
    elif 'submit' not in perms and 'submit_all' not in perms:
        error = 'You are not allowed to check answers to this question.'
    elif name not in namemap:
        error = ('No question with name %s.  '
                 'Please refresh before submitting.') % name
    elif 'submit_all' not in perms:
        if timing == -1 and not i:
            error = 'This question is not yet available.'
        elif name in context[_n('locked')]:
            error = 'You are not allowed to save for this question (it has been locked).'
        elif (not _get(qargs, 'csq_allow_submit_after_answer_viewed', False,
                       bool) and name in context[_n('answer_viewed')]):
            error = 'You are not allowed to save to this question after viewing the answer.'
        elif timing == 1 and _get(context, 'cs_auto_lock', False, bool):
            error = ('You are not allowed to save after the '
                     'deadline for this question.')
        elif not _get(qargs, 'csq_allow_save', True, bool):
            error = 'Saving is not allowed for this question.'
    return error


def check_msg(context, perms, name):
    namemap = context[_n('name_map')]
    timing = context[_n('timing')]
    i = context[_n('impersonating')]
    _, qargs = namemap[name]
    error = None
    if 'submit' not in perms and 'submit_all' not in perms:
        error = 'You are not allowed to check answers to this question.'
    elif name not in namemap:
        error = ('No question with name %s.  '
                 'Please refresh before submitting.') % name
    elif namemap[name][0].get('handle_check', None) is None:
        error = 'This question type does not support checking.'
    elif 'submit_all' not in perms:
        if timing == -1 and not i:
            error = 'This question is not yet available.'
        elif name in context[_n('locked')]:
            error = 'You are not allowed to check answers to this question.'
        elif (not _get(qargs, 'csq_allow_submit_after_answer_viewed', False,
                       bool) and name in context[_n('answer_viewed')]):
            error = 'You are not allowed to check answers to this question after viewing the answer.'
        elif timing == 1 and _get(context, 'cs_auto_lock', False, bool):
            error = ('You are not allowed to check after the '
                     'deadline for this problem.')
        elif not _get(qargs, 'csq_allow_check', True, bool):
            error = 'Checking is not allowed for this question.'
    return error


def grade_msg(context, perms, name):
    namemap = context[_n('name_map')]
    _, qargs = namemap[name]
    if 'grade' not in perms:
        return 'You are not allowed to grade exercises.'


def submit_msg(context, perms, name):
    if name.startswith('__'):
        name = name[2:].rsplit('_', 1)[0]
    namemap = context[_n('name_map')]
    timing = context[_n('timing')]
    i = context[_n('impersonating')]
    _, qargs = namemap[name]
    error = None
    if not _.get('allow_submit', True):
        error = 'You cannot submit this type of question.'
    if (not _.get('allow_self_submit', True)) and 'real_user' not in context['cs_user_info']:
        error = 'You cannot submit this type of question yourself.'
    elif 'submit' not in perms and 'submit_all' not in perms:
        error = 'You are not allowed to submit answers to this question.'
    elif name not in namemap:
        error = ('No question with name %s.  '
                 'Please refresh before submitting.') % name
    elif 'submit_all' not in perms:
        # don't allow if...
        if timing == -1 and not i:
            # ...the problem has not yet been released
            error = 'This question is not yet open for submissions.'
        elif _get(context, 'cs_auto_lock', False, bool) and timing == 1:
            # ...the problem auto locks and it is after the due date
            error = ('Submissions are not allowed after the '
                     'deadline for this question')
        elif name in context[_n('locked')]:
            error = 'You are not allowed to submit to this question.'
        elif (not _get(qargs, 'csq_allow_submit_after_answer_viewed', False,
                       bool) and name in context[_n('answer_viewed')]):
            # ...the answer has been viewed and submissions after
            #    viewing the answer are not allowed
            error = ('You are not allowed to submit to this question '
                     'because you have already viewed the answer.')
        elif not _get(qargs, 'csq_allow_submit', True, bool):
            # ...submissions are not allowed (custom message)
            if 'cs_nosubmit_message' in context:
                error = context['cs_nosubmit_message'](context)
            else:
                error = 'Submissions are not allowed for this question.'
        elif (not _get(qargs, 'csq_grading_mode', 'auto', str) == 'manual' and
              context['csm_tutor'].get_manual_grading_entry(context, name) is not None):
            # ...prior submission has been graded
            error = 'You are not allowed to submit after a previous submission has been graded.'
        else:
            # ...the user does not have enough checks left
            nleft, _ = nsubmits_left(context, name)
            if nleft <= 0:
                error = ('You have used all of your allowed '
                         'submissions for this question.')
    return error


def log_action(context, log_entry):
    uname = context[_n('uname')]
    entry = {'action': context[_n('action')],
             'timestamp': context['cs_timestamp'],
             'user_info': context['cs_user_info']}
    entry.update(log_entry)
    context['csm_cslog'].update_log(uname, context['cs_path_info'],
                                    'problemactions', entry)


def simple_return_json(val):
    content = json.dumps(val, separators=(',', ':'))
    length = str(len(content))
    retcode = ('200', 'OK')
    headers = {'Content-type': 'application/json', 'Content-length': length}
    return retcode, headers, content


def make_return_json(context, ret, names=None):
    names = context[_n('question_names')] if names is None else names
    names = set(i[2:].rsplit('_', 1)[0] if i.startswith('__') else i
                for i in names)
    for name in names:
        ret[name]['nsubmits_left'] = nsubmits_left(context, name)[1],
        ret[name]['buttons'] = make_buttons(context, name)
    return simple_return_json(ret)


def render_question(elt, context, lastsubmit, wrap=True):
    q, args = elt
    name = args['csq_name']
    lastlog = context[_n('last_log')]
    answer_viewed = context[_n('answer_viewed')]
    if wrap:
        out = '\n<!--START question %s -->' % (name)
    else:
        out = ''
    if wrap and q.get('indiv', True) and args.get('csq_indiv', True):
        out += '\n<div class="question question-%s" id="cs_qdiv_%s" style="position: static">' % (q['qtype'], name)

    out += '\n<div id="%s_rendered_question">\n' % name
    out += context['csm_language'].source_transform_string(context, args.get(
        'csq_prompt', ''))
    out += q['render_html'](lastsubmit, **args)
    out += '\n</div>'

    out += '<div>'
    out += (('\n<span id="%s_buttons">' % name) + make_buttons(context, name) +
            "</span>")
    out += ('\n<span id="%s_loading" style="display:none;"><img src="%s"/>'
            '</span>') % (name, context['cs_loading_image'])
    out += (('\n<span id="%s_score_display">' % args['csq_name']) +
            context['csm_tutor'].make_score_display(context, args, name, None) + '</span>')
    out += (('\n<div id="%s_nsubmits_left" class="nsubmits_left">' % name) +
            nsubmits_left(context, name)[1] + "</div>")
    out += '</div>'

    if name in answer_viewed:
        answerclass = ' class="solution"'
        showanswer = True
    elif context[_n('impersonating')]:
        answerclass = ' class="impsolution"'
        showanswer = True
    else:
        answerclass = ''
        showanswer = False
    out += '\n<div id="%s_solution_container"%s>' % (args['csq_name'],
                                                     answerclass)
    out += '\n<div id="%s_solution">' % (args['csq_name'])
    if showanswer:
        ans = q['answer_display'](**args)
        out += '\n'
        out += context['csm_language'].source_transform_string(context, ans)
    out += '\n</div>'
    out += '\n<div id="%s_solution_explanation">' % name
    if (name in context[_n('explanation_viewed')] and
            args.get('csq_explanation', '') != ''):
        exp = explanation_display(args['csq_explanation'])
        out += context['csm_language'].source_transform_string(context, exp)
    out += '\n</div>'
    out += '\n</div>'

    out += '\n<div id="%s_message">' % args['csq_name']

    gmode = _get(args, 'csq_grading_mode', 'auto', str)
    message = context[_n('last_log')].get('%s_message' % name, '')
    magic = context[_n('last_log')].get('%s_magic' % name, None)
    if magic is not None:
        checker_loc = os.path.join(context['cs_data_root'], '__LOGS__',
                                   '_checker', 'results', magic)
        if os.path.isfile(checker_loc):
            with open(checker_loc, 'rb') as f:
                result = context['csm_cslog'].unprep(f.read())
            message = '\n<script type="text/javascript">$("#%s_score_display").html(%r);</script>' % (name, result['score_box'])
            try:
                result['response'] = result['response'].decode()
            except:
                pass
            message += '\n' + result['response']

        else:
            message = WEBSOCKET_RESPONSE % {'name': name, 'magic': magic,
                                            'websocket': context['cs_checker_websocket'],
                                            'loading': context['cs_loading_image'],
                                            'id_css': (' style="display:none;"'
                                                       if context.get('cs_show_submission_id', True)
                                                       else '')}
    if gmode == 'manual':
        q, args = context[_n('name_map')][name]
        lastlog = context['csm_tutor'].get_manual_grading_entry(context, name) or {}
        lastscore = lastlog.get('score', '')
        tpoints = q['total_points'](**args)
        comments = (context['csm_tutor'].get_manual_grading_entry(context, name) or {}).get('comments',None)
        if comments is not None:
            comments = context['csm_language']._md_format_string(context, comments)
        try:
            score_output = lastscore * tpoints
        except:
            score_output = ""

        if comments is not None:
            message = '<b>Score:</b> %s (out of %s)<br><br><b>Grader\'s Comments:</b><br/>%s' % (
                score_output, tpoints, comments)
    out += message + "</div>"
    if wrap and q.get('indiv', True) and args.get('csq_indiv', True):
        out += '\n</div>'
    if wrap:
        out += '\n<!--END question %s -->\n' % args['csq_name']
    return out


def nsubmits_left(context, name):
    nused = context[_n('nsubmits_used')].get(name, 0)
    q, args = context[_n('name_map')][name]

    if not q.get('allow_submit', True) or not q.get('allow_self_submit', True):
        return 0, ''

    info = q.get('defaults', {})
    info.update(args)

    # look up 'nsubmits' in the question's arguments
    # (fall back on default in qtype)
    nsubmits = info.get('csq_nsubmits', None)
    if nsubmits is None:
        nsubmits = context.get('cs_nsubmits_default', float('inf'))

    perms = context[_n('orig_perms')]
    if 'submit' not in perms and 'submit_all' not in perms:
        return 0, ''
    nleft = max(0, nsubmits - nused)
    for (regex, nchecks) in context['cs_user_info'].get('nsubmits_extra', []):
        if re.match(regex, '.'.join(context['cs_path_info'][1:] + [name])):
            nleft += nchecks
    nmsg = info.get('csq_nsubmits_message', None)
    if nmsg is None:
        if nleft < float('inf'):
            msg = "<i>You have %d submission%s remaining.</i>" % (nleft, 's'
                                                                  if nleft != 1
                                                                  else '')
        else:
            msg = "<i>You have infinitely many submissions remaining.</i>"
    else:
        msg = nmsg(nsubmits, nused, nleft)

    if 'submit_all' in perms:
        msg = (
            "As staff, you are always allowed to submit.  "
            "If you were a student, you would see the following:<br/>%s") % msg

    return max(0, nleft), msg


def button_text(x, msg):
    if x is None:
        return msg
    else:
        return None


_button_map = {
    'submit': (submit_msg, 'Submit'),
    'save': (save_msg, 'Save'),
    'viewanswer': (viewanswer_msg, 'View Answer'),
    'clearanswer': (clearanswer_msg, 'Clear Answer'),
    'viewexplanation': (viewexp_msg, 'View Explanation'),
    'check': (check_msg, True),
}


def make_buttons(context, name):
    uname = context[_n('uname')]
    rp = context[_n('perms')]  # the real user's perms
    p = context[_n('orig_perms')]  # the impersonated user's perms, if any
    i = context[_n('impersonating')]
    q, args = context[_n('name_map')][name]
    nsubmits, _ = nsubmits_left(context, name)

    buttons = {'copy_seed': None, 'copy': None, 'new_seed': None}
    buttons['new_seed'] = ("New Random Seed" if 'submit_all' in p and
                           context.get('cs_random_inited', False) else None)
    abuttons = {
        'copy_seed': ('Copy Random Seed'
                      if context.get('cs_random_inited', False) else None),
        'copy': 'Copy to My Account',
        'lock': None,
        'unlock': None
    }
    for (b, (func, text)) in list(_button_map.items()):
        buttons[b] = button_text(func(context, p, name), text)
        abuttons[b] = button_text(func(context, rp, name), text)

    for d in (buttons, abuttons):
        if d['check']:
            d['check'] = q.get('checktext', 'Check')

    if name in context[_n('locked')]:
        abuttons['unlock'] = 'Unlock'
    else:
        abuttons['lock'] = 'Lock'

    aout = ''
    if i:
        for k in {'submit', 'check', 'save'}:
            if buttons[k] is not None:
                abuttons[k] = None
            elif abuttons[k] is not None:
                abuttons[k] += ' (as %s)' % uname
        for k in ('viewanswer', 'clearanswer', 'viewexplanation'):
            if buttons[k] is not None:
                abuttons[k] = None
            elif abuttons[k] is not None:
                abuttons[k] += ' (for %s)' % uname
        aout = '<div><b><font color="red">Admin Buttons:</font></b><br/>'
        for k in ('copy', 'copy_seed', 'check', 'save', 'submit', 'viewanswer',
                  'viewexplanation', 'clearanswer', 'lock', 'unlock'):
            x = {'b': abuttons[k], 'k': k, 'n': name}
            if abuttons[k] is not None:
                aout += (
                    '\n<button id="%(n)s_%(k)s" '
                    'class="%(k)s btn btn-danger" '
                    'onclick="catsoop.%(k)s(\'%(n)s\');">'
                    '%(b)s</button>') % x
        # in manual grading mode, add a box and button for grading
        gmode = _get(args, 'csq_grading_mode', 'auto', str)
        if gmode == 'manual':
            lastlog = context['csm_tutor'].get_manual_grading_entry(context, name) or {}
            lastscore = lastlog.get('score', '')
            lastcomments = lastlog.get('comments', '')
            tpoints = q['total_points'](**args)
            try:
                output = lastscore * tpoints
            except:
                output = ""
            aout += ('<br/><b><font color="red">Grading:</font></b>'
                     '<table border="0" width="100%%">'
                     '<tr><td align="right" width="30%%">'
                     '<font color="red">Points Earned (out of %2.2f):</font>'
                     '</td><td><input type="text" value="%s" size="5" '
                     'style="border-color: red;" '
                     'id="%s_grading_score" '
                     'name="%s_grading_score" /></td></tr>'
                     '<tr><td align="right">'
                     '<font color="red">Comments:</font></td>'
                     '<td><textarea rows="5" id="%s_grading_comments" '
                     'name="%s_grading_comments" '
                     'style="width: 100%%; border-color: red;">'
                     '%s'
                     '</textarea></td></tr><tr><td></td><td>'
                     '<button class="grade" '
                     'style="background-color: #FFD9D9; '
                     'border-color: red;" '
                     'onclick="catsoop.grade(\'%s\');">'
                     'Submit Grade'
                     '</button></td></tr></table>') % (tpoints, output, name,
                                                       name, name, name,
                                                       lastcomments, name)
        aout += '</div>'

    out = ''
    for k in ('check', 'save', 'submit', 'viewanswer', 'viewexplanation',
              'clearanswer', 'new_seed'):
        x = {'b': buttons[k], 'k': k, 'n': name}
        if buttons[k] is not None:
            out += ('\n<button id="%(n)s_%(k)s" '
                    'class="%(k)s btn btn-catsoop" '
                    'style="margin-top: 10px;" '
                    'onclick="catsoop.%(k)s(\'%(n)s\');">'
                    '%(b)s</button>') % x
    return out + aout


def pre_handle(context):
    # enumerate the questions in this problem
    global CHECKER_DB_LOC
    CHECKER_DB_LOC = os.path.join(context['cs_data_root'], '__LOGS__',
                                  '_checker.db')
    context[_n('name_map')] = collections.OrderedDict()
    for elt in context['cs_problem_spec']:
        if isinstance(elt, tuple):
            m = elt[1]
            context[_n('name_map')][m['csq_name']] = elt
            if 'init' in elt[0]:
                a = elt[0].get('defaults', {})
                a.update(elt[1])
                elt[0]['init'](a)

    # who is the user (and, who is being impersonated?)
    user_info = context.get('cs_user_info', {})
    uname = user_info.get('username', 'None')
    real = user_info.get('real_user', user_info)
    context[_n('role')] = real.get('role', 'None')
    context[_n('section')] = real.get('section', None)
    context[_n('perms')] = real.get('permissions', [])
    context[_n('orig_perms')] = user_info.get('permissions', [])
    context[_n('uname')] = uname
    context[_n('real_uname')] = real.get('username', uname)
    context[_n('impersonating')] = (
        context[_n('uname')] != context[_n('real_uname')])

    # store release and due dates
    r = context[_n('rel')] = context['csm_tutor'].get_release_date(context)
    d = context[_n('due')] = context['csm_tutor'].get_due_date(context)
    n = context['csm_time'].from_detailed_timestamp(context['cs_timestamp'])
    context[_n('now')] = n
    context[_n('timing')] = -1 if n <= r else 0 if n <= d else 1

    if _get(context, 'cs_require_activation', False, bool):
        pwd = _get(context, 'cs_activation_password', 'password', str)
        context[_n('activation_password')] = pwd

    # determine the right log name to look up, and grab the most recent entry
    loghead = '___'.join(context['cs_path_info'][1:])
    ps_name = '%s___problemstate' % loghead
    pa_name = '%s___problemactions' % loghead
    pg_name = '%s___problemgrades' % loghead
    grp_name = '%s___group' % loghead
    ll = context['csm_cslog'].most_recent(uname,
                                          context['cs_path_info'],
                                          'problemstate',
                                          {})
    _cs_group_path = context.get('cs_groups_to_use', context['cs_path_info'])
    context[_n('all_groups')] = context['csm_groups'].list_groups(context,
                                                                  _cs_group_path)
    context[_n('group')] = context['csm_groups'].get_group(context,
                                                           _cs_group_path,
                                                           uname,
                                                           context[_n('all_groups')])
    _ag = context[_n('all_groups')]
    _g = context[_n('group')]
    context[_n('group_members')] = _gm = _ag.get(_g[0], {}).get(_g[1], [])
    if uname not in _gm:
        _gm.append(uname)
    context[_n('last_log')] = ll
    context[_n('logname_state')] = ps_name
    context[_n('logname_actions')] = pa_name
    context[_n('logname_grades')] = pg_name
    context[_n('logname_group')] = grp_name
    context[_n('logname_groups')] = '%ss' % grp_name

    context[_n('locked')] = set(ll.get('locked', set()))
    context[_n('answer_viewed')] = set(ll.get('answer_viewed', set()))
    context[_n('explanation_viewed')] = set(ll.get('explanation_viewed', set()))
    context[_n('nsubmits_used')] = ll.get('nsubmits_used', {})

    # what is the user trying to do?
    context[_n('action')] = context['cs_form'].get('action', 'view').lower()
    if context[_n('action')] in ('view', 'activate',
                                 'passthrough', 'list_questions',
                                 'get_state', 'manage_groups',
                                 'render_single_question'):
        context[_n('form')] = context['cs_form']
    else:
        names = context['cs_form'].get('names', "[]")
        context[_n('question_names')] = json.loads(names)
        context[_n('form')] = json.loads(context['cs_form'].get('data', '{}'))
        if context['cs_upload_management'] == 'file':
            for name, value in context[_n('form')].items():
                if name == '__names__':
                    continue
                if isinstance(value, list):
                    data = csm_tools.data_uri.DataURI(value[1]).data
                    dir_ = os.path.join(context['cs_data_root'], '__LOGS__', '_uploads', *context['cs_path_info'])
                    os.makedirs(dir_, exist_ok=True)
                    value[0] = value[0].replace('<', '').replace('>', '').replace('"', '').replace('"', '')
                    fname = '%s___%.06f___%s' % (context['cs_username'], time.time(), value[0])
                    fullname = os.path.join(dir_, fname)
                    with open(fullname, 'wb') as f:
                        f.write(data)
                    value[1] = os.path.join(*context['cs_path_info'], fname)
        elif context['cs_upload_management'] == 'db':
            pass
        else:
            raise Exception('unknown upload management style: %r' % context['cs_upload_management'])


def _get_auto_view(context):
    # when should we automatically view the answer?
    ava = context.get('csq_auto_viewanswer', False)
    if ava is True:
        ava = set(['nosubmits', 'perfect', 'lock'])
    elif isinstance(ava, str):
        ava = set([ava])
    elif not ava:
        ava = set()
    return ava


def default_javascript(context):
    namemap = context[_n('name_map')]
    if 'submit_all' in context[_n('perms')]:
        skip_alert = list(namemap.keys())
    else:
        skipper = 'csq_allow_submit_after_answer_viewed'
        skip_alert = [name for (name, (q, args)) in list(namemap.items())
                      if _get(args, skipper, False, bool)]
    out = '''
<script type="text/javascript" src="__HANDLER__/default/cs_ajax.js"></script>
<script type="text/javascript">
catsoop.all_questions = %(allqs)r;
catsoop.username = %(uname)s;
catsoop.api_token = %(secret)s;
catsoop.this_path = %(path)r;
catsoop.path_info = %(pathinfo)r;
catsoop.course = %(course)s;
catsoop.url_root = %(root)r;
'''

    if len(namemap) > 0:
        out += '''catsoop.imp = %(imp)r;
catsoop.skip_alert = %(skipalert)s;
catsoop.viewans_confirm = "Are you sure?  Viewing the answer will prevent any further submissions to this question.  Press 'OK' to view the answer, or press 'Cancel' if you have changed your mind.";
'''
    out += '</script>'

    api_tok = 'null'
    uname = 'null'
    given_tok = context.get('cs_user_info', {}).get('api_token', None)
    if given_tok is not None:
        api_tok = repr(given_tok)
    given_uname = context.get('cs_user_info', {}).get('username', None)
    if given_uname is not None:
        uname = repr(given_uname)

    return out % {
        'skipalert': json.dumps(skip_alert),
        'allqs': list(context[_n('name_map')].keys()),
        'user': context[_n('real_uname')],
        'path': '/'.join([context['cs_url_root']] + context['cs_path_info']),
        'imp': context[_n('uname')] if context[_n('impersonating')] else '',
        'secret': api_tok,
        'course': repr(context['cs_course']) if context['cs_course'] else 'null',
        'pathinfo': context['cs_path_info'],
        'root': context['cs_url_root'],
        'uname': uname,
    }


def default_timer(context):
    out = ''
    if not _get(context, 'cs_auto_lock', False, bool):
        return out
    if len(context[_n('locked')]) >= len(context[_n('name_map')]):
        return out
    if context[_n('now')] > context[_n('due')]:
        # view answers immediately if viewed past the due date
        out += '\n<script type="text/javascript">'
        out += "\ncatsoop.ajaxrequest(catsoop.all_questions,'lock');"
        out += '\n</script>'
        return out
    else:
        out += '\n<script type="text/javascript">'
        out += ("\ncatsoop.timer_now = %d;"
                "\ncatsoop.timer_due = %d;"
                "\ncatsoop.time_url = %r;") % (
                    context['csm_time'].unix(context[_n('now')]),
                    context['csm_time'].unix(context[_n('due')]),
                    context['cs_url_root'] + '/cs_util/time')
        out += '\n</script>'
        out += ('<script type="text/javascript" '
                'src="__HANDLER__/default/cs_timer.js"></script>')
    return out


def exc_message(context):
    exc = traceback.format_exc()
    exc = context['csm_errors'].clear_info(context, exc)
    return ('<p><font color="red">'
            '<b>CAT-SOOP ERROR:</b>'
            '<pre>%s</pre></font>') % exc

def _get_scores(context):
    section = str(context.get('cs_form', {}).get('section',
            context.get('cs_user_info').get('section', 'default')))

    util = context['csm_util']

    usernames = util.list_all_users(context, context['cs_course'])
    users = [
        util.read_user_file(context, context['cs_course'], username, {})
        for username in usernames
    ]
    no_section = context.get('cs_whdw_no_section', False)
    students = [
        user
        for user in users
        if user.get('role', None) in ['Student', 'SLA'] and (no_section or str(user.get('section', 'default')) == section)
    ]

    questions = context[_n('name_map')]
    scores = collections.OrderedDict()
    for name, question in questions.items():
        if not context.get('cs_whdw_filter', lambda q: True)(question): continue

        counts = {}

        for student in students:
            username = student.get('username', 'None')
            log = context['csm_cslog'].most_recent(
                username,
                context['cs_path_info'],
                'problemstate',
                {},
            )
            log = context['csm_tutor'].compute_page_stats(context, username, context['cs_path_info'], ['state'])['state']
            score = log.get('scores', {}).get(name, None)
            counts[username] = score

        scores[name] = counts

    return scores

def handle_stats(context):
    perms = context['cs_user_info'].get('permissions', [])
    if 'whdw' not in perms:
        return 'You are not allowed to view this page.'

    section = str(context.get('cs_form', {}).get('section',
            context.get('cs_user_info').get('section', 'default')))

    questions = context[_n('name_map')]
    stats = collections.OrderedDict()

    groups = context['csm_groups'].list_groups(
        context,
        context['cs_path_info'],
    ).get(section, None)

    if groups:
        total = len(groups)
        for name, scores in _get_scores(context).items():
            counts = {
                'completed': 0,
                'attempted': 0,
                'not tried': 0,
            }

            for members in groups.values():
                score = min(
                    (scores.get(member, None) for member in members),
                    key=lambda x: -1 if x is None else x,
                )

                if score is None:
                    counts['not tried'] += 1
                elif score == 1:
                    counts['completed'] += 1
                else:
                    counts['attempted'] += 1

            stats[name] = counts
    else:
        total = 0
        for name, scores in _get_scores(context).items():
            counts = {
                'completed': 0,
                'attempted': 0,
                'not tried': 0,
            }

            for score in scores.values():
                if score is None:
                    counts['not tried'] += 1
                elif score == 1:
                    counts['completed'] += 1
                else:
                    counts['attempted'] += 1

            stats[name] = counts
            total = max(total, sum(counts.values()))

    BeautifulSoup = context['csm_tools'].bs4.BeautifulSoup
    soup = BeautifulSoup('')
    table = soup.new_tag('table')
    table['class'] = 'table table-bordered'

    header = soup.new_tag('tr')
    for heading in ['name', 'completed', 'attempted', 'not tried']:
        th = soup.new_tag('th')
        th.string = heading
        header.append(th)
    table.append(header)

    for name, counts in stats.items():
        tr = soup.new_tag('tr')
        td = soup.new_tag('td')
        a = soup.new_tag('a',
            href = '?section={}&action=whdw&question={}'.format(section, name),
        )
        qargs = questions[name][1]
        a.string = qargs.get('csq_display_name', name)
        td.append(a)
        td['class'] = 'text-left'
        tr.append(td)
        for key in ['completed', 'attempted', 'not tried']:
            td = soup.new_tag('td')
            td.string = '{count}/{total} ({percent:.2%})'.format(
                    count = counts[key],
                    total = total,
                    percent = (counts[key] / total) if total != 0 else 0,
            )
            td['class'] = 'text-right'
            tr.append(td)
        table.append(tr)

    soup.append(table)

    return str(soup)

def _real_name(context, username):
    return (context['csm_cslog'].most_recent('_extra_info', [], username, None) or {}).get('name', None)

def _whdw_name(context, username):
    real_name = _real_name(context, username)
    if real_name:
        return '{} (<a href="?as={}" target="_blank">{}</a>)'.format(real_name, username, username)
    else:
        return username

def handle_whdw(context):
    perms = context['cs_user_info'].get('permissions', [])
    if 'whdw' not in perms:
        return 'You are not allowed to view this page.'

    section = str(context.get('cs_form', {}).get('section',
            context.get('cs_user_info').get('section', 'default')))

    question = context['cs_form']['question']
    qtype, qargs = context[_n('name_map')][question]
    display_name = qargs.get('csq_display_name', qargs['csq_name'])
    context['cs_content_header'] += ' | {}'.format(display_name)

    scores = _get_scores(context)[question]

    groups = context['csm_groups'].list_groups(
        context,
        context['cs_path_info'],
    ).get(section, None)

    BeautifulSoup = context['csm_tools'].bs4.BeautifulSoup
    soup = BeautifulSoup('')

    if groups:
        css = soup.new_tag('style')
        css.string = '''\
        .whdw-cell {
          border: 1px white solid;
        }

        .whdw-not-tried {
          background-color: #ff6961;
          color: black;
        }

        .whdw-attempted {
          background-color: #ffb347;
          color: black;
        }

        .whdw-completed {
          background-color: #77dd77;
          color: black;
        }

        .whdw-cell ul {
          padding-left: 5px;
        }
        '''
        soup.append(css)

        grid = soup.new_tag('div')
        grid['class'] = 'row'
        for group, members in sorted(groups.items()):
            min_score = min(
                (scores.get(member, None) for member in members),
                key=lambda x: -1 if x is None else x,
            )

            cell = soup.new_tag('div')
            cell['class'] = 'col-sm-3 whdw-cell {}'.format({
                    None: 'whdw-not-tried',
                    1: 'whdw-completed',
            }.get(min_score, 'whdw-attempted'))
            grid.append(cell)

            header = soup.new_tag('div')
            header['class'] = 'text-center'
            header.string = '{}'.format(group)
            cell.append(header)

            people = soup.new_tag('ul')
            header['class'] = 'text-center'

            for member in members:
                m = soup.new_tag('li')
                name = soup.new_tag('span')
                name.insert(1, BeautifulSoup(_whdw_name(context, member)))
                m.append(name)

                score = soup.new_tag('span')
                score['class'] = 'pull-right'
                score.string = str(scores.get(member, None))
                m.append(score)

                people.append(m)
            cell.append(people)

        soup.append(grid)
        return str(soup)
    else:
        states = {
            'completed': [],
            'attempted': [],
            'not tried': [],
        }

        for username, score in scores.items():
            if score is None:
                state = 'not tried'
            elif score == 1:
                state = 'completed'
            else:
                state = 'attempted'

            states[state].append(username)

        for state in ['not tried', 'attempted', 'completed']:
            usernames = states[state]
            h3 = soup.new_tag('h3')
            h3.string = '{} ({})'.format(state, len(states[state]))
            soup.append(h3)

            grid = soup.new_tag('div')
            grid['class'] = 'row'
            for username in sorted(usernames):
                cell = soup.new_tag('div')
                cell.insert(1, BeautifulSoup(_whdw_name(context, username)))
                cell['class'] = 'col-sm-2'
                grid.append(cell)
            soup.append(grid)

        return str(soup)


WEBSOCKET_RESPONSE = """
<div class="bs-callout bs-callout-default" id="cs_partialresults_%(name)s">
  <div id="cs_partialresults_%(name)s_body">
    <span id="cs_partialresults_%(name)s_message">Looking up your submission (id <code>%(magic)s</code>).  Watch here for updates.</span><br/>
    <center><img src="%(loading)s"/></center>
  </div>
</div>
<small%(id_css)s>ID: <code>%(magic)s</code></small>

<script type="text/javascript">
var magic_%(name)s = %(magic)r;
if (typeof ws_%(name)s != 'undefined'){
    ws_%(name)s.onclose = function(){}
    ws_%(name)s.onmessage = function(){}
    ws_%(name)s.close();
    var ws_%(name)s = undefined;
}

$('#%(name)s_score_display').html('<img src="%(loading)s" style="vertical-align: -6px; margin-left: 5px;"/>');

$('#%(name)s_buttons button').prop("disabled", true);

var ws_%(name)s = new WebSocket(%(websocket)r);

ws_%(name)s.onopen = function(){
    ws_%(name)s.send(JSON.stringify({type: "hello", magic: magic_%(name)s}));
}

ws_%(name)s.onclose = function(){
    if (this !== ws_%(name)s) return;
    if (ws_%(name)s_state != 2){
        var thediv = $('#cs_partialresults_%(name)s')
        thediv.html('Your connection to the server was lost.  Please reload the page.');
    }
}

var ws_%(name)s_state = -1;

ws_%(name)s.onmessage = function(event){
    var m = event.data;
    var j = JSON.parse(m);
    var thediv = $('#cs_partialresults_%(name)s')
    var themessage = $('#cs_partialresults_%(name)s_message');
    if (j.type == 'ping'){
        ws_%(name)s.send(JSON.stringify({type: 'pong'}));
    }else if (j.type == 'inqueue'){
        ws_%(name)s_state = 0;
        try{clearInterval(ws_%(name)s_interval);}catch(err){}
        thediv[0].className = '';
        thediv.addClass('bs-callout');
        thediv.addClass('bs-callout-warning');
        themessage.html('Your submission (id <code>%(magic)s</code>) is queued to be checked (position ' + j.position + ').');
        $('#%(name)s_buttons button').prop("disabled", false);
    }else if (j.type == 'running'){
        ws_%(name)s_state = 1;
        try{clearInterval(ws_%(name)s_interval);}catch(err){}
        thediv[0].className = '';
        thediv.addClass('bs-callout');
        thediv.addClass('bs-callout-info');
        themessage.html('Your submission is currently being checked<span id="%(name)s_ws_running_time"></span>.');
        $('#%(name)s_buttons button').prop("disabled", false);
        var sync = ((new Date()).valueOf()/1000 - j.now)
        ws_%(name)s_interval = setInterval(function(){catsoop.setTimeSince("%(name)s",
                                                                           j.started,
                                                                           sync);}, 1000);
    }else if (j.type == 'newresult'){
        ws_%(name)s_state = 2;
        try{clearInterval(ws_%(name)s_interval);}catch(err){}
        $('#%(name)s_score_display').html(j.score_box);
        thediv[0].className = '';
        thediv.html(j.response);
        $('#%(name)s_buttons button').prop("disabled", false);
    }
}

ws_%(name)s.onerror = function(event){
    console.log(event);
}
</script>
"""
