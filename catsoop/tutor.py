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

# Tutor-specific things (questions, handlers, etc)

import os
import re
import sys
import random
import string
import importlib

from . import auth
from . import time
from . import loader
from . import logging as logging_import
from . import base_context

from datetime import timedelta

importlib.reload(base_context)


def compute_page_stats(context, user, course, path, keys=None):
    logging = logging_import.get_logger(context)
    if keys is None:
        keys = ['context', 'question_points', 'state', 'actions',
                'manual_grades']
    keys = list(keys)

    out = {}
    logtail = '.'.join(path)
    if 'state' in keys:
        keys.remove('state')
        state_name = '%s.problemstate' % logtail
        out['state'] = logging.most_recent(course, user, state_name, {})
    if 'actions' in keys:
        keys.remove('actions')
        actions_name = '%s.problemactions' % logtail
        out['actions'] = logging.read_log(course, user, actions_name)
    if 'manual_grades' in keys:
        keys.remove('manual_grades')
        grades_name = '%s.problemgrades' % logtail
        out['manual_grades'] = logging.read_log(course, user, grades_name)

    if len(keys) == 0:
        return out

    # spoof loading the page for the user in question
    new = dict(context)
    loader.load_global_data(new)
    new['cs_path_info'] = [course] + path
    cfile = context['csm_dispatch'].content_file_location(context, new['cs_path_info'])
    loader.do_early_load(context, course, path, new, cfile)
    new['cs_course'] = course
    new['cs_username'] = user
    new['cs_form'] = {'action': 'passthrough'}
    new['cs_user_info'] = {'username': user}
    new['cs_user_info'] = auth.get_user_information(new)
    loader.do_late_load(context, course, path, new, cfile)
    if 'cs_post_load' in new:
        new['cs_post_load'](new)
    handle_page(new)
    if 'cs_post_handle' in new:
        new['cs_post_handle'](new)

    if 'context' in keys:
        keys.remove('context')
        out['context'] = new
    if 'question_points' in keys:
        keys.remove('question_points')
        items = new['cs_defaulthandler_name_map'].items()
        out['question_points'] = {n: q['total_points'](**a)
                                  for (n, (q, a)) in items}
    for k in keys:
        out[k] = None
    return out


def qtype_inherit(context, other_type):
    base, _ = question(context, other_type)
    context.update(base)


def _wrapped_defaults_maker(context, name):
    orig = context[name]

    def _wrapped_func(*args, **kwargs):
        info = dict(context.get('defaults', {}))
        info.update(kwargs)
        return orig(*args, **info)

    return _wrapped_func


def question(context, qtype, **kwargs):
    """
    Generate a data structure representing a question.  Looks for the specified
    qtype in the course level first, and then in the global location.

    This function is called as tutor.question(qtype,**kwargs) in almost all
    cases; i.e., it is called without the first argument.  A hack in
    loader.cs_compile will insert the first argument.
    """
    try:
        course = context['cs_course']
        qtypes_folder = os.path.join(context.get('cs_data_root',
                                                 base_context.cs_data_root),
                                                 'courses', course,
                                                '__QTYPES__')
        loc = os.path.join(qtypes_folder, qtype)
        fname = os.path.join(loc, '%s.py' % qtype)
        assert os.path.isfile(fname)
    except:
        qtypes_folder = os.path.join(
            context.get('cs_fs_root', base_context.cs_fs_root), '__QTYPES__')
        loc = os.path.join(qtypes_folder, qtype)
        fname = os.path.join(loc, '%s.py' % qtype)
    new = {}
    new['csm_base_context'] = new['base_context'] = base_context
    for i in context:
        if i.startswith('csm_'):
            new[i] = new[i[4:]] = context[i]
    pre_code = ("import sys\n"
                "_orig_path = sys.path\n"
                "if %r not in sys.path:\n"
                "    sys.path = [%r] + sys.path\n\n") % (loc, loc)
    x = loader.cs_compile(fname,
                          pre_code=pre_code,
                          post_code="sys.path = _orig_path")
    exec(x, new)
    for i in {'total_points', 'handle_submission', 'handle_check',
              'render_html', 'answer_display'}:
        if i in new:
            new[i] = _wrapped_defaults_maker(new, i)
    new['qtype'] = qtype
    return (new, kwargs)


def handler(context, handler, check_course=True):
    """
    Generate a data structure representing an activity.  Looks for the
    specified handler in the course level first, and then in the global
    location.
    """
    new = {}
    new['csm_base_context'] = new['base_context'] = base_context
    for i in context:
        if i.startswith('csm_'):
            new[i] = new[i[4:]] = context[i]
    try:
        assert check_course
        course = context['cs_course']
        qtypes_folder = os.path.join(context.get('cs_data_root',
                                                 base_context.cs_data_root),
                                                 'courses', course,
                                                '__HANDLERS__')
        loc = os.path.join(qtypes_folder, handler)
        fname = os.path.join(loc, '%s.py' % handler)
        assert os.path.isfile(fname)
    except:
        fname = os.path.join(context.get('cs_fs_root',
                                         base_context.cs_fs_root),
                             '__HANDLERS__', handler,
                             '%s.py' % handler)
    code = loader.cs_compile(fname)
    exec(code, new)
    return new


def get_canonical_name(path):
    """
    Return the canonical name of the resource at path.  This name is
    the cdr of path, joined by '__'.
    """
    return '.'.join(path[1:])


def get_release_date(context):
    """
    Get the release date of a resource.  The inspected variable is
    release_date.  If realize_time is defined in context, it will be used in
    place of time.realize_time (note that it must have the same number and type
    of arguments, and the same return type as time.realize_time).
    """
    rel = context.get('cs_release_date', 'ALWAYS')
    if callable(rel):
        rel = rel(context)
    realize = context.get('cs_realize_time', time.realize_time)
    return realize(context, context.get('cs_release_date', 'ALWAYS'))


def get_due_date(context, do_extensions=False):
    """
    Get the due date of a resource.  The inspected variable is due_date.  If
    realize_time is defined in context, it will be used in place of
    time.realize_time (note that it must have the same number and type of
    arguments, and the same return type as time.realize_time).
    """
    due = context.get('cs_due_date', 'NEVER')
    if callable(due):
        due = due(context)
    realize = context.get('cs_realize_time', time.realize_time)
    due = realize(context, due)
    try:
        if do_extensions:
            extensions = context['cs_user_info'].get('extensions', [])
            for ex in extensions:
                if re.match(ex[0], get_canonical_name(context)):
                    due += timedelta(weeks=ex[1])
    except:
        pass
    return due


def available_courses():
    """
    Returns a list of available courses.
    """
    base = os.path.join(base_context.cs_data_root, 'courses')
    if not os.path.isdir(base):
        return []
    out = []
    for course in os.listdir(base):
        if course.startswith('_') or course.startswith('.'):
            continue
        if not os.path.isdir(os.path.join(base, course)):
            continue
        data = loader.spoof_early_load([course])
        if data.get('cs_course_available', True):
            t = data.get('cs_long_name', course)
            out.append((course, t))
    return out


def handle_page(context):
    """
    Generate content for activities.  If atype is defined in context, replaces
    the content variable with the result of calling the atype's handle function
    on context.  Specifics vary by atype.
    """
    hand = context.get('cs_handler', None)
    if hand is None:
        hand = 'default'
    h = handler(context, hand)
    result = h['handle'](context)
    if isinstance(result, tuple):
        return result
    context['cs_content'] = result


def _new_random_seed(n=100):
    try:
        return os.urandom(n)
    except:
        return ''.join(random.choice(string.ascii_letters) for i in xrange(n))


def _get_random_seed(context, n=100, force_new=False):
    uname = context['cs_username']
    course = context['cs_course']
    logname = '.'.join(['random.seed'] + context['cs_path_info'])
    if force_new:
        stored = None
    else:
        stored = context['csm_cslog'].most_recent(course, uname, logname, None)
    if stored is None:
        stored = _new_random_seed(n)
        context['csm_cslog'].update_log(course, uname, logname, stored)
    return stored


def init_random(context, prefix=''):
    """
    Initialize the random number generator for per-user, per-resource
    randomness.  This function is called as tutor.init_random() in almost all
    cases; i.e., it is called with no arguments.  A hack in loader.cs_compile
    will insert the argument.
    """
    try:
        seed = _get_random_seed(context)
    except:
        seed = '.'.join([context['cs_username']] + context['cs_path_info'])
    context['cs_random_seed'] = seed
    context['cs_random'].seed(seed)
    context['cs_random_inited'] = True
