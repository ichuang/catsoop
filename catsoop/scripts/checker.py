# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
import tempfile
import traceback
import collections
import multiprocessing

from datetime import datetime

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

import catsoop.base_context as base_context
import catsoop.lti as lti
import catsoop.auth as auth
import catsoop.cslog as cslog
import catsoop.loader as loader
import catsoop.language as language
import catsoop.dispatch as dispatch

from catsoop.process import set_pdeathsig

CHECKER_DB_LOC = os.path.join(base_context.cs_data_root, "_logs", "_checker")
RUNNING = os.path.join(CHECKER_DB_LOC, "running")
QUEUED = os.path.join(CHECKER_DB_LOC, "queued")
RESULTS = os.path.join(CHECKER_DB_LOC, "results")
STAGING = os.path.join(CHECKER_DB_LOC, "staging")

REAL_TIMEOUT = base_context.cs_checker_global_timeout

_pid = os.getpid()


def _log(*args, **kwargs):
    print(f"[checker.py {_pid}]", *args, **kwargs)


def exc_message(context):
    exc = traceback.format_exc()
    exc = context["csm_errors"].clear_info(context, exc)
    return ('<p><font color="red"><b>CAT-SOOP ERROR:</b><pre>%s</pre></font>') % exc


def do_check(row):
    """
    Check submission, dispatching to appropriate question handler

    row: (dict) action to take, with input data
    """
    os.setpgrp()  # make this part of its own process group
    set_pdeathsig()()  # but make it die if the parent dies.  will this work?

    context = loader.generate_context(row["path"])
    context["cs_course"] = row["path"][0]
    context["cs_path_info"] = row["path"]
    context["cs_username"] = row["username"]
    context["cs_user_info"] = {"username": row["username"]}
    context["cs_user_info"] = auth.get_user_information(context)
    context["cs_now"] = datetime.fromtimestamp(row["time"])

    have_lti = ("cs_lti_config" in context) and ("lti_data" in row)
    if have_lti:
        lti_data = row["lti_data"]
        lti_handler = lti.lti4cs_response(
            context, lti_data
        )  # LTI response handler, from row['lti_data']
        if lti_handler.have_data:
            if not "cs_session_data" in context:
                context["cs_session_data"] = {}
            context["cs_session_data"][
                "is_lti_user"
            ] = True  # so that course preload.py knows

    cfile = dispatch.content_file_location(context, row["path"])
    loader.load_content(
        context, context["cs_course"], context["cs_path_info"], context, cfile
    )

    namemap = {}
    for elt in context["cs_problem_spec"]:
        if isinstance(elt, tuple):  # each elt is (problem_context, problem_kwargs)
            namemap[elt[1]["csq_name"]] = elt

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
            try:
                handler = question["handle_submission"]
                resp = handler(row["form"], **args)
                score = resp["score"]
                msg = resp["msg"]
                extra = resp.get("extra_data", None)
            except Exception as err:
                resp = {}
                score = 0.0
                msg = exc_message(context)
                extra = None

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

        row["score"] = score
        row["score_box"] = score_box
        row["response"] = language.handle_custom_tags(context, msg)
        row["extra_data"] = extra

        # make temporary file to write results to
        magic = row["magic"]
        temploc = os.path.join(STAGING, "results.%s" % magic)
        with open(temploc, "wb") as f:
            f.write(context["csm_cslog"].prep(row))
        # move that file to results, close the handle to it.
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
        cm = context["csm_cslog"].log_lock(
            [row["username"], *row["path"], "problemstate"]
        )
        with cm as lock:
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

            # update LTI tool consumer with new aggregate score
            if have_lti and lti_handler.have_data and row["action"] == "submit":
                lti.update_lti_score(lti_handler, x, namemap)


if __name__ == "__main__":
    running = []

    # if anything is in the "running" dir when we start, that's an error.  turn
    # those back to queued to force them to run again (put them at the front of the
    # queue).
    for f in os.listdir(RUNNING):
        shutil.move(os.path.join(RUNNING, f), os.path.join(QUEUED, "0_%s" % f))

    # and now actually start running
    _log("ready to go")
    while True:
        # check for dead processes
        dead = set()
        for i in range(len(running)):
            id_, row, p = running[i]
            if not p.is_alive():
                if p.exitcode != 0:
                    row["score"] = 0.0
                    row["score_box"] = ""
                    if p.exitcode < 0:  # this probably only happens if we killed it
                        row["response"] = (
                            "<font color='red'><b>Your submission could not be checked "
                            "because the checker ran for too long.</b></font>"
                        )
                    else:  # a python error or similar
                        row["response"] = (
                            "<font color='red'><b>An unknown error occurred when "
                            "processing your submission</b></font>"
                        )
                    magic = row["magic"]
                    newloc = os.path.join(RESULTS, magic[0], magic[1], magic)
                    os.makedirs(os.path.dirname(newloc), exist_ok=True)
                    with open(newloc, "wb") as f:
                        f.write(cslog.prep(row))
                    # then remove from running
                    os.unlink(os.path.join(RUNNING, row["magic"]))
                    _log(f"marked {row['magic']} (pid {p.pid}) as done.  removing it.")
                dead.add(i)
            elif time.time() - p._started > REAL_TIMEOUT:
                _log(f"check for {row['magic']} (pid {p.pid}) timed out.  killing it.")
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
                qfn = os.path.join(QUEUED, first)
                with open(qfn, "rb") as f:
                    try:
                        row = cslog.unprep(f.read())
                    except Exception as err:
                        continue
                _, magic = first.split("_")
                row["magic"] = magic
                shutil.move(os.path.join(QUEUED, first), os.path.join(RUNNING, magic))

                # start a worker for it
                p = multiprocessing.Process(target=do_check, args=(row,))
                _log(f"started checker {magic} with PID {p.pid}")
                running.append((magic, row, p))
                p.start()
                p._started = time.time()
                p._entry = row

        time.sleep(0.1)
