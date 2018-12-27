# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
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
import shutil
import signal
import logging
import tempfile
import traceback
import collections
import multiprocessing

from datetime import datetime

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

import catsoop.base_context as base_context
import catsoop.auth as auth
import catsoop.cslog as cslog
import catsoop.loader as loader
import catsoop.language as language
import catsoop.dispatch as dispatch

from catsoop.process import set_pdeathsig

CHECKER_DB_LOC = os.path.join(base_context.cs_data_root, "__LOGS__", "_checker")
RUNNING = os.path.join(CHECKER_DB_LOC, "running")
QUEUED = os.path.join(CHECKER_DB_LOC, "queued")
RESULTS = os.path.join(CHECKER_DB_LOC, "results")

REAL_TIMEOUT = base_context.cs_checker_global_timeout

DEBUG = False

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

def log(msg):
    dt = datetime.now()
    omsg = "[checker:%s]: %s" % (dt, msg)
    # sys.stdout.write(omsg)
    # sys.stdout.flush()
    # print(omsg)
    LOGGER.error(omsg)

def exc_message(context):
    exc = traceback.format_exc()
    exc = context["csm_errors"].clear_info(context, exc)
    return ('<p><font color="red"><b>CAT-SOOP ERROR:</b><pre>%s</pre></font>') % exc


def do_check(row):
    os.setpgrp()  # make this part of its own process group
    set_pdeathsig()()  # but make it die if the parent dies.  will this work?

    context = loader.spoof_early_load(row["path"])
    context["cs_course"] = row["path"][0]
    context["cs_path_info"] = row["path"]
    context["cs_username"] = row["username"]
    context["cs_user_info"] = {"username": row["username"]}
    context['is_running_checker'] = True			# used by preload.py (for LTI users)
    context["cs_user_info"] = auth.get_user_information(context)
    context["cs_now"] = datetime.fromtimestamp(row["time"])
    cfile = dispatch.content_file_location(context, row["path"])
    if DEBUG:
        log("Loading grader python code course=%s, cfile=%s" % (context['cs_course'], cfile))
    loader.do_late_load(
        context, context["cs_course"], context["cs_path_info"], context, cfile
    )

    namemap = collections.OrderedDict()
    cnt = 0
    for elt in context["cs_problem_spec"]:
        if isinstance(elt, tuple):
            m = elt[1]
            namemap[m["csq_name"]] = elt
            if DEBUG:
                question = elt[0]['handle_submission']
                log("Map: %s (%s) -> %s" % (m["csq_name"], m['csq_display_name'], question))
            cnt += 1
    if DEBUG:
        log("Loaded %d procedures into question namemap" % cnt)

    # now, depending on the action we want, take the appropriate steps

    names_done = set()
    for name in row["names"]:
        if name.startswith("__"):
            name = name[2:].rsplit("_", 1)[0]
        if name in names_done:
            continue
        names_done.add(name)
        question, args = namemap[name]
        if row["action"] == "submit":
            if DEBUG:
                log("submit name=%s, row=%s" % (name, row))
            try:
                handler = question["handle_submission"]
                if DEBUG:
                    log("handler=%s" % handler)
                resp = handler(row["form"], **args)
                score = resp["score"]
                msg = resp["msg"]
                extra = resp.get("extra_data", None)
            except Exception as err:
                resp = {}
                score = 0.0
                log("Failed to handle submission, err=%s" % str(err))
                log("Traceback=%s" % traceback.format_exc())
                msg = exc_message(context)
                extra = None

            if DEBUG:
                log("submit resp=%s, msg=%s" % (resp, msg))

            score_box = context["csm_tutor"].make_score_display(
                context, args, name, score, True
            )

        elif row["action"] == "check":
            try:
                msg = question["handle_check"](row["form"], **args)
            except:
                msg = exc_message(context)

            score = None
            score_box = ""
            extra = None

            if DEBUG:
                log("check name=%s, msg=%s" % (name, msg))

        row["score"] = score
        row["score_box"] = score_box
        row["response"] = language.handle_custom_tags(context, msg)
        row["extra_data"] = extra

        # make temporary file to write results to
        _, temploc = tempfile.mkstemp()
        with open(temploc, "wb") as f:
            f.write(context["csm_cslog"].prep(row))
        # move that file to results, close the handle to it.
        magic = row["magic"]
        newloc = os.path.join(RESULTS, magic[0], magic[1], magic)
        os.makedirs(os.path.dirname(newloc), exist_ok=True)
        shutil.move(temploc, newloc)
        try:
            os.close(_)
        except:
            pass
        # then remove from running
        os.unlink(os.path.join(RUNNING, row["magic"]))
        # finally, update the appropriate log
        lockname = context["csm_cslog"].get_log_filename(
            row["username"], row["path"], "problemstate"
        )
        with context["csm_cslog"].log_lock(lockname + ".lock") as lock:
            x = context["csm_cslog"].most_recent(
                row["username"], row["path"], "problemstate", {}, lock=False
            )
            if row["action"] == "submit":
                x.setdefault("scores", {})[name] = row["score"]
            x.setdefault("score_displays", {})[name] = row["score_box"]
            x.setdefault("cached_responses", {})[name] = row["response"]
            x.setdefault("extra_data", {})[name] = row["extra_data"]
            context["csm_cslog"].overwrite_log(
                row["username"], row["path"], "problemstate", x, lock=False
            )


running = []

# if anything is in the "running" dir when we start, that's an error.  turn
# those back to queued to force them to run again (put them at the front of the
# queue).
for f in os.listdir(RUNNING):
    shutil.move(os.path.join(RUNNING, f), os.path.join(QUEUED, "0_%s" % f))

# and now actually start running
if DEBUG:
    log("starting main loop")
while True:
    # check for dead processes
    dead = set()
    if DEBUG and len(running):
        log("have %d running" % len(running))
    for i in range(len(running)):
        id_, row, p = running[i]
        if not p.is_alive():
            if p.exitcode < 0:  # this probably only happens if we killed it
                # update the database
                row["score"] = 0.0
                row["score_box"] = ""
                row["response"] = (
                    "<font color='red'><b>Your submission could not be checked "
                    "because the checker ran for too long.</b></font>"
                )
                magic = row["magic"]
                newloc = os.path.join(RESULTS, magic[0], magic[1], magic)
                with open(newloc, "wb") as f:
                    f.write(cslog.prep(row))
                # then remove from running
                os.unlink(os.path.join(RUNNING, row["magic"]))
            dead.add(i)
        elif time.time() - p._started > REAL_TIMEOUT:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except:
                pass
    for i in sorted(dead, reverse=True):
        running.pop(i)

    if base_context.cs_checker_parallel_checks - len(running) > 0:
        # otherwise, add an entry to running.
        waiting = sorted(os.listdir(QUEUED))
        if waiting:
            # grab the first thing off the queue, move it to the "running" dir
            first = waiting[0]
            with open(os.path.join(QUEUED, first), "rb") as f:
                row = cslog.unprep(f.read())
            _, magic = first.split("_")
            row["magic"] = magic
            shutil.move(os.path.join(QUEUED, first), os.path.join(RUNNING, magic))

            # start a worker for it
            if DEBUG:
                log("Starting checker with row=%s" % row)
            p = multiprocessing.Process(target=do_check, args=(row,))
            running.append((magic, row, p))
            p.start()
            p._started = time.time()
            p._entry = row

    time.sleep(0.1)
