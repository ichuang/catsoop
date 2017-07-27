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
import signal
import threading
import traceback
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

c = r.connect(db='catsoop')


class PKiller(threading.Thread):
    def __init__(self, proc, timeout):
        threading.Thread.__init__(self)
        self.proc = proc
        self.timeout = timeout
        self.going = True

    def run(self):
        end = time.time() + self.timeout
        while (time.time() < end):
            time.sleep(0.1)
            if (not self.proc.is_alive()) or (not self.going):
                return
        if self.going:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            except:
                pass


def exc_message(context):
    exc = traceback.format_exc()
    exc = context['csm_errors'].clear_info(context, exc)
    return ('<p><font color="red">'
            '<b>CAT-SOOP ERROR:</b>'
            '<pre>%s</pre></font>') % exc


def do_check(row):
    c = r.connect(db='catsoop')

    os.setpgrp()

    process = multiprocessing.current_process()
    process._catsoop_check_id = row['id']

    context = loader.spoof_early_load(row['path'])
    context['cs_course'] = row['path'][0]
    context['cs_path_info'] = row['path']
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

    # start the process killer with the global timeout so we don't run too long
    killer = PKiller(process, context['cs_checker_global_timeout'])
    killer.start()

    # now, depending on the action we want, take the appropriate steps

    names_done = set()
    for name in row['names']:
        if name.startswith('__'):
            name = name[2:].rsplit('_', 1)[0]
        if name in names_done:
            continue
        names_done.add(name)
        question, args = namemap[name]
        if row['action'] == 'submit':
            try:
                resp = question['handle_submission'](row['form'],
                                                     **args)
                score = resp['score']
                msg = resp['msg']
            except:
                resp = {}
                score = 0.0
                msg = exc_message(context)

            score_box = context['csm_tutor'].make_score_display(context, args,
                                                                name, score,
                                                                True)

        elif row['action'] == 'check':
            try:
                msg = question['handle_check'](row['form'], **args)
            except:
                msg = exc_message(context)

            score = None
            score_box = ''

        r.table('checker').filter(r.row['id'] == row['id']).update({
            'progress': 2,
            'score': score,
            'score_box': score_box,
            'response': language.handle_custom_tags(context, msg),
        }).run(c)

    killer.going = False
    c.close()

running = []

# if anything is in state '1' (running) when we start, that's an error.  turn those back to 0's.
cursor = r.table('checker').filter(r.row['progress'] == 1).update({'progress': 0}).run(c)

while True:
    # check for dead processes
    dead = set()
    for i in range(len(running)):
        id_, p = running[i]
        if not p.is_alive():
            if p.exitcode < 0:  # this probably only happens if we killed it
                r.table('checker').filter(r.row['id'] == id_).update({
                    'progress': 3,  # 3 will be our error signal
                    'score': 0.0,
                    'score_box': '',
                    'response': ('Your submission could not be checked because the '
                                 'checker ran for too long.'),
                }).run(c)
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
    r.table('checker').filter(r.row['id']==row['id']).update({'progress': 1, 'time_started': r.now()}, non_atomic=True).run(c)
    p = multiprocessing.Process(target=do_check, args=(row, ))
    running.append((row['id'], p))
    p.start()
