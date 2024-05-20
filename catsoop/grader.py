'''
Run the aysynchronous checker which grades queued submissions.
Use catsoop.queue to retrieve submissions and save responses.
'''

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

from . import lti
from . import auth
from . import cslog
from . import loader
from . import csqueue
from . import language
from . import dispatch
from . import debug_log
from . import base_context
from .process import set_pdeathsig

try:
    # under macOS, need to use fork for multiprocessing
    import platform
    if platform.system().startswith("Darwin"):
        # multiprocessing.freeze_support()
        multiprocessing.set_start_method('fork')
except RuntimeError:
    pass

LOGGER = debug_log.LOGGER
# LOGGER.setLevel(1)
    
REAL_TIMEOUT = base_context.cs_checker_global_timeout

DEBUG = True

# multiprocessing.set_start_method('spawn')	# safer for cloud DB connections (versus using fork)
# multiprocessing.set_executable(sys.executable)

def log(msg):
    if not DEBUG:
        return
    dt = datetime.now()
    omsg = "[checker:%s]: %s" % (dt, msg)
    LOGGER.warning(omsg)


def exc_message(context):
    exc = traceback.format_exc()
    exc = context["csm_errors"].clear_info(context, exc)
    return ('<p><font color="red"><b>CAT-SOOP ERROR:</b><pre>%s</pre></font>') % exc


def update_lti(lti_handler, row, problemstate, total_possible_npoints, npoints_by_name):
    '''
    update LTI tool consumer with new aggregate score
    '''
    aggregate_score = 0
    cnt = 0
    try:
        empirical_total_possible = 0
        for k, v in problemstate["scores"].items():  # e.g. 'scores': {'q000000': 1.0, 'q000001': True, 'q000002': 1.0}
            v = float(v)
            nbyn = npoints_by_name.get(str(k), 1.0)
            aggregate_score += v * nbyn
            if (DEBUG > 10):
                log("    Adding to aggregate_score: k=%s, v=%s, nbyn=%s" % (k, v, nbyn))
            cnt += 1
            empirical_total_possible += nbyn

        if total_possible_npoints == 0 or total_possible_npoints < empirical_total_possible:
            total_possible_npoints = empirical_total_possible
            LOGGER.error("[checker] total_possible_npoints=0 ???? changed to empirical_total_possible=%s" % empirical_total_possible)
        if total_possible_npoints == 0:
            aggregate_score_fract = 0
        else:
            aggregate_score_fract = aggregate_score / total_possible_npoints  # LTI wants score in [0, 1.0]
        log(
            "Computed aggregate score from %d questions, total_possible=%s, nbyname=%s, aggregate_score=%s (fraction=%s)"
            % (cnt, total_possible_npoints, npoints_by_name, aggregate_score, aggregate_score_fract)
        )
        log(
            "magic=%s sending aggregate_score_fract=%s to LTI tool consumer, scores=%s"
            % (row["magic"], aggregate_score_fract, problemstate['scores'])
        )
        score_ok = True
    except Exception as err:
        LOGGER.error(
            "[checker] failed to compute score for problem %s, err=%s, traceback=%s"
            % (str(row)[:100], err, traceback.format_exc())
        )
        score_ok = False

    if score_ok:
        try:
            lti_handler.send_outcome(aggregate_score_fract)
        except Exception as err:
            LOGGER.error(
                "[checker] failed to send outcome to LTI consumer, problem=%s, err=%s, traceback=%s"
                % (str(row)[:100], str(err), traceback.format_exc())
            )
            # LOGGER.error("[checker] traceback=%s" % traceback.format_exc())

def save_grader_results(result_queue, context, name, row):
    '''
    Save results from the completion of a do_check process, for a specific question name
    '''
    jobid = row['magic']
    if "lti_data" in row:			# don't save lti_data in results (it was just needed for pushing scores to LTI consumer)
        row.pop("lti_data")
    row['job_complete'] = time.time()		# record job completion time
    if result_queue is not None:		# if result_queue then stuff results there; don't do the db update here (let the master process do it instead)
        log("[grader.save_grader_results] queueing results for jobid=%s, name=%s, user=%s, path=%s" % (jobid, name, row.get('username'), row.get('path')))
        the_context = {'cs_data_root': context['cs_data_root']}		# used by filesystem queue
        result_queue.put((the_context, name, row))
        time.sleep(5)
        return

    log("[grader.save_grader_results] saving result for jobid=%s, name=%s, user=%s, path=%s" % (jobid, name, row.get('username'), row.get('path')))
    # csqueue.initialize()			# http://api.mongodb.org/python/current/faq.html#is-pymongo-fork-safe
    # cslog.initialize()
    csqueue.save_results(context, jobid, row)
    try:
        os.close(_)
    except:
        pass
    # finally, update the appropriate problemstate log
    logpath = (row["username"], row["path"], "problemstate")

    def transform_func(x):
        if row["action"] == "submit":
            x.setdefault("scores", {})[name] = row["score"]
        x.setdefault("score_displays", {})[name] = row["score_box"]
        x.setdefault("cached_responses", {})[name] = row["response"]
        x.setdefault("extra_data", {})[name] = row["extra_data"]
        return x

    log("[grader.save_grader_results] updating problemstate log")
    cslog.modify_most_recent(*logpath, default={},
                             transform_func=transform_func,
                             method="overwrite")


def do_check(row, result_queue=None):
    """
    Check submission, dispatching to appropriate question handler

    row: (dict) action to take, with input data

    This is run by multiprocessing, so it should be a plain function
    """
    cslog.initialize()		# http://api.mongodb.org/python/current/faq.html#is-pymongo-fork-safe
    csqueue.initialize()	# http://api.mongodb.org/python/current/faq.html#is-pymongo-fork-safe

    os.setpgrp()  # make this part of its own process group
    set_pdeathsig()()  # but make it die if the parent dies.  will this work?

    jobid = row['magic']
    log("[grader.do_check] started on job_id=%s, result_queue=%s" % (jobid, result_queue))

    context = loader.generate_context(row["path"])
    context["cs_course"] = row["path"][0]
    context["cs_path_info"] = row["path"]
    context["cs_username"] = row["username"]
    context["cs_user_info"] = {"username": row["username"]}
    context["cs_user_info"] = auth.get_user_information(context)
    context["cs_now"] = datetime.fromtimestamp(row["time"])

    have_lti = ("cs_lti_config" in context) and ("lti_data" in row)
    if have_lti:
        push_scores_to_lti_consumer = context.get("cs_lti_config", {}).get("push_scores_to_lti_consumer", False)	# flag for whether or not to send scores to LTI consumer
        lti_verbose_debug = context.get("cs_lti_config", {}).get("verbose_debug", False)
        lti_data = row["lti_data"]
        lti_handler = lti.lti4cs_response(
            context, lti_data
        )  # LTI response handler, from row['lti_data']
        log("lti_handler.have_data=%s" % lti_handler.have_data)
        if lti_handler.have_data and lti_verbose_debug:
            log("lti_data=%s" % lti_handler.lti_data)
            if not "cs_session_data" in context:
                context["cs_session_data"] = {}
            context["cs_session_data"][
                "is_lti_user"
            ] = True  # so that course preload.py knows

    cfile = dispatch.content_file_location(context, row["path"])
    log("[%s] Loading grader python code course=%s, cfile=%s" % (jobid, context["cs_course"], cfile) )
    loader.load_content(
        context, context["cs_course"], context["cs_path_info"], context, cfile
    )

    namemap = collections.OrderedDict()
    cnt = 0
    total_possible_npoints = 0
    npoints_by_name = {}
    for elt in context["cs_problem_spec"]:
        if isinstance(elt, tuple):  # each elt is (problem_context, problem_kwargs)
            m = elt[1]
            namemap[m["csq_name"]] = elt
            csq_npoints = m.get("csq_npoints", 0)
            npoints_by_name[str(m['csq_name'])] = float(csq_npoints)
            total_possible_npoints += (
                csq_npoints
            )  # used to compute total aggregate score pct
            if DEBUG:
                question = elt[0]["handle_submission"]
                dn = m.get("csq_display_name")
                if (DEBUG > 10):
                    log("Map: %s (%s) -> %s" % (m["csq_name"], dn, question))
                    log(
                        "%s csq_npoints=%s, total_points=%s"
                        % (dn, csq_npoints, elt[0]["total_points"]())
                    )
            cnt += 1
    if DEBUG:
        log(
            "[%s] Loaded %d procedures into question namemap (total_possible_npoints=%s)"
            % (jobid, cnt, total_possible_npoints)
        )

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
                log("[%s] submit name=%s, row=%s" % (jobid, name, str(row)[:50]))
            try:
                handler = question["handle_submission"]
                if DEBUG > 10:
                    log("handler=%s" % handler)
                resp = handler(row["form"], **args)
                score = resp["score"]
                msg = resp["msg"]
                extra = resp.get("extra_data", None)
            except Exception as err:
                resp = {}
                score = 0.0
                log("[%s] Failed to handle submission, err=%s" % (jobid, str(err)))
                log("Traceback=%s" % traceback.format_exc())
                msg = exc_message(context)
                extra = None

            if DEBUG:
                log("[%s] submit resp=%s, msg=%s" % (jobid, str(resp)[:50], str(msg)[:50]))

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
                log("[%s] check name=%s, msg=%s" % (jobid, name, msg))

        row["score"] = score
        row["score_box"] = score_box
        row["response"] = language.handle_custom_tags(context, msg)
        row["extra_data"] = extra

        # save results and remove job from running
        log("[grader.do_check] jobid=%s: saving results for name=%s" % (jobid, name))
        save_grader_results(result_queue, context, name, row)        

    # update LTI tool consumer with new aggregate score (after for loop over names)
    # do this only if "push_scores_to_lti_consumer" is True in the cs_lti_config dict
    if have_lti and lti_handler.have_data and push_scores_to_lti_consumer and row["action"] == "submit":
        logpath = (row["username"], row["path"], "problemstate")
        x = context["csm_cslog"].most_recent(*logpath)
        update_lti(lti_handler, row, x, total_possible_npoints, npoints_by_name)


def watch_queue_and_run(max_finished=None):
    '''
    This is the main loop for the grader, which checks for queue entries and processes the
    latest entry.  

    This procedure runs forever.

    max_finished = number of finished jobs, afer which this procedure returns ; used for unit testing
    '''
    nstarted = 0
    nfinished = 0
    nresults = 0
    running = []
    result_queue = multiprocessing.Queue()
    context = base_context.__dict__
    # if anything is in the "running" dir when we start, that's an error.  turn
    # those back to queued to force them to run again (put them at the front of the
    # queue).
    csqueue.move_running_back_to_queued(context)
    csqueue.update_current_job_status()
    log("=====> Current number of jobs in queue waiting for execution = %s" % csqueue.current_queue_length())

    # and now actually start running
    if DEBUG:
        log("starting main loop")
    nrunning = None
    
    while True:
        # check for dead processes
        dead = set()
        if DEBUG and not (len(running) == nrunning):  # output debug message when nrunning changes
            nrunning = len(running)
            log("have %d running (%s)" % (nrunning, [ str(x)[:100] for x in running ]))

        for i in range(len(running)):
            id_, row, p = running[i]

            if not p.is_alive():
                log("    Process %s is dead" % p)
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
                            "<font color='red'><b>An unknown error (exit=%s) occurred when "
                            "processing your submission</b></font>"
                        ) % p.exitcode
                    magic = row["magic"]
                    LOGGER.error("    Process %s died with exitcode %s, response=%s" % (p, p.exitcode, row['response']))
                    csqueue.save_results(context, magic, row)
                dead.add(i)
                nfinished += 1

            elif time.time() - p._started > REAL_TIMEOUT:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except:
                    pass
        if dead:
            log("Removing %s" % dead)
        for i in sorted(dead, reverse=True):
            running.pop(i)
    
        # if result sent from grader check process via queue, then handle it
        try:
            result = result_queue.get(block=False)
        except Exception as err:
            # log("no result, err=%s" % str(err))
            result = None
        if result:
            # log("got result!  %s" % str(result))
            save_grader_results(None, *result)
            nresults += 1
            if max_finished is not None and nresults >= max_finished:
                return

        if base_context.cs_checker_parallel_checks - len(running) > 0:
            # otherwise, add an entry to running.
            row = csqueue.get_oldest_from_queue(context, move_to_running=True)
            if row:
                # start a worker for it
                log("=====> Current number of jobs in queue waiting for execution = %s" % csqueue.current_queue_length())
                jobid = row["magic"]
                log("Starting checker on jobid=%s, user=%s, path=%s, names=%s" % (jobid, row.get('username'), row.get('path'), str(row.get('names'))[:50]))
                row['job_started'] = time.time()		# record grader job computation start time
                nstarted += 1
                p = multiprocessing.Process(target=do_check, args=(row, result_queue))
                p.start()
                running.append((jobid, row, p))
                p._started = time.time()
                p._entry = row
                log("Process pid = %s" % p.pid)
    
        time.sleep(0.1)
