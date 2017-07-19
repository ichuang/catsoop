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
import sys
import time
import collections
import rethinkdb as r
import multiprocessing

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

import catsoop.base_context as base_context
import catsoop.auth as auth
import catsoop.cslog as cslog
import catsoop.loader as loader
import catsoop.language as language
import catsoop.dispatch as dispatch

TIMEOUT = base_context.cs_checker_global_timeout
c = r.connect(db='catsoop')

def exc_message(context):
    exc = traceback.format_exc()
    exc = context['csm_errors'].clear_info(context, exc)
    return ('<p><font color="red">'
            '<b>CAT-SOOP ERROR:</b>'
            '<pre>%s</pre></font>') % exc

def do_check(row):
    c = r.connect(db='catsoop')

    process = multiprocessing.current_process()

    # spoof a page load.
    context = loader.spoof_early_load(row['path'])
    context['cs_course'] = row['path'][0]
    context['cs_path_info'] = row['path'][1:]
    context['cs_username'] = row['username']
    context['cs_user_info'] = {'username': row['username']}
    context['cs_user_info'] = auth.get_user_information(context)
    cfile = dispatch.content_file_location(context, row['path'])
    loader.do_late_load(context, context['cs_course'], context['cs_path_info'], context, cfile)

    namemap = collections.OrderedDict()
    qcount = 0
    for elt in context['cs_problem_spec']:
        if isinstance(elt, tuple):
            m = elt[1]
            namemap[m['csq_name']] = elt

    # TODO: start the process killer with the global timeout

    # now, depending on the action we want, take the appropriate steps
    if row['action'] == 'submit':
        names_done = set()
        for name in row['names']:
            if name.startswith('__'):
                name = name[2:].rsplit('_', 1)[0]
            if name in names_done:
                continue
            names_done.add(name)

            question, args = namemap[name]
            try:
                resp = question['handle_submission'](row['form'],
                                                     **args)
                score = resp['score']
                msg = resp['msg']
            except:
                resp = {}
                score = 0.0
                msg = exc_message(context)

            r.table('checker').filter(r.row['id'] == row['id']).update({
                'progress': 2,
                'score': score,
                'score_box': context['csm_tutor'].make_score_display(context, args, name, score, True),
                'response': language.handle_custom_tags(context, msg),
            }).run(c)

    elif row['action'] == 'check':
        pass

running = []

# if anything is in state '1' (running) when we start, that's an error.  turn those back to 0's.
cursor = r.table('checker').filter(r.row['progress'] == 1).update({'progress': 0}).run(c)

while True:
    # check for dead processes
    dead = set()
    for i in range(len(running)):
        if not running[i].is_alive():
            # TODO: check if _we_ killed this process.  if so, need to adjust
            # the log accordingly.
            dead.add(i)
    for i in sorted(dead, reverse=True):
        running.pop(i)

    # if no processes are free, head back to the top of the loop.
    if len(running) >= base_context.cs_checker_parallel_checks:
        time.sleep(.01)  # quick sleep, but keeps the CPU usage down
        continue

    # check for entries to run
    cursor = r.table('checker').filter(r.row['progress'] == 0).order_by(r.asc(r.row['time'])).limit(1).run(c)
    if len(cursor) == 0:
        # nothing to be run.
        # we can afford a longer delay here.
        time.sleep(.2)
        continue

    # we have something to run.  so do it.
    row = cursor[0]
    # mark that we're checking this one now.
    r.table('checker').filter(r.row['id']==row['id']).update({'progress': 1}).run(c)
    p = multiprocessing.Process(target=do_check, args=(row, ))
    running.append(p)
    p.start()
