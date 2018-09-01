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
"""
Utilities for managing courses (questions, handlers, statistics, etc)
"""

import os
import re
import json
import random
import string
import sqlite3
import importlib
import collections

from datetime import timedelta
from collections import OrderedDict

from . import auth
from . import time
from . import loader
from . import cslog
from . import base_context

importlib.reload(base_context)

_nodoc = {"timedelta"}


def _get(context, key, default, cast=lambda x: x):
    v = context.get(key, default)
    return cast(v(context) if isinstance(v, collections.Callable) else v)


def get_manual_grading_entry(context, name):
    """
    Return the most recent manual grading entry associated with a given
    question

    **Parameters:**

    * `context`: the context associated with this request (from which the
        current user is retrieved)
    * `name`: the name of the question whose grades we want

    **Returns:** the most recent manual grading entry associated with the given
    question, or `None` if no grading entries exist.  If a dictionary is
    returned, it will have the following keys:

    * `'qname'`: the name of the question being graded (will be the same as the
        given `name`)
    * `'grader'`: the name of the user who submitted the grade
    * `'score'`: a floating-point number between 0 and 1, representing the
        score
    * `'comments'`: a string containing the grader's comments, if any
    * `'timestamp'`: the time at which the grade was submitted, as a string
        from `catsoop.time.detailed_timestamp`

    """
    uname = context["cs_user_info"].get("username", "None")
    log = context["csm_cslog"].read_log(uname, context["cs_path_info"], "problemgrades")
    out = None
    for i in log:
        if i["qname"] == name:
            out = i
    return out


def make_score_display(
    context, args, name, score=None, assume_submit=False, last_log=None
):
    """
    Helper function to generate the display that users should see for their
    score.

    The output depends on a number of constraints:

    If `csq_show_score` is `False`, then no score is displayed.  In this case,
    if the user has submitted something, they will see a message indicating
    that a submission has been received.  Otherwise, they will see nothing.

    If no score is given, the most recent score is looked up (either from the
    manual grading entries log or from the problem state log) and used.

    After determining the score, if a `csq_score_message` function is defined,
    it is called with the current score (a `float` between 0 and 1) passed in
    as its sole argument, and the result is returned.  Otherwise, a default
    value is used.

    **Parameters:**

    * `context`: the context associated with this request
    * `args`: a dictionary representing the environment associated with this
        question (including variables defined within the &lt;question&gt; tag)
    * `name`: the name of the question
    * `score`: a float between 0 and ` representing the score we want to
        render, or `None` if we should look up a value from the logs

    **Optional Parameters:**

    * `assume_submit` (default `False`): if `True`, assume that the user has
        made a submission for purposes of rendering a response, even if the
        logs say otherwise

    **Returns:** a string containing HTML representing the rendered score
    """
    last_log = last_log or {}
    if not _get(args, "csq_show_score", True, bool):
        if name in last_log.get("scores", {}) or assume_submit:
            return "Submission received."
        else:
            return ""
    gmode = _get(args, "csq_grading_mode", "auto", str)
    if gmode == "manual" and score is None:
        log = get_manual_grading_entry(context, name)
        if log is not None:
            score = log["score"]
    elif score is None:
        score = last_log.get("scores", {}).get(name, None)
    if score is None:
        if name in last_log.get("scores", {}) or assume_submit:
            return "Grade not available."
        else:
            return ""
    c = args.get("csq_score_message", args.get("cs_score_message", None))
    try:
        return c(score)
    except:
        colorthing = 255 * score
        r = max(0, 200 - colorthing)
        g = min(200, colorthing)
        s = score * 100
        return (
            '<span style="color:rgb(%d,%d,0);font-weight:bolder;">' "%.02f%%</span>"
        ) % (r, g, s)


def read_checker_result(context, magic):
    """
    Helper function to load a "results" file from the checker and return the
    associated dictionary.

    **Parameters:**

    * `context`: the context associated with this request
    * `magic`: the ID of the checker result to look up

    **Returns:** a dictionary representing the checker's results; this
    dictionary will contain the following keys:

    * _Input information_:

        * `'path'`: a list of string representing the path associated with this
            result
        * `'username'`: the user who submitted the request
        * `'names'`: a list containing the names of the questions that were
            submitted
        * `'form'`: a dictionary containing the values given in the form (among
            them, the values that were submitted)
        * `'time'`: a Unix timestamp, when this request was submitted
        * `'action'`: either `'check'` or `'submit'`, depending on which button
            was clicked to initiate the submission

    * _Output information_:

        * `'score'`: a `float` between 0 and 1 indicating the score given to
            this submission
        * `'score_box'`: a string containing the HTML-rendered version of the
            score (to be displayed to the user
        * `'response'`: the HTML that should be displayed back to the user
            about their submission (test results, etc)
        * `'extra_data'`: any extra data returned by the checker, or `None` for
            question types that don't return extra data
    """
    with open(
        os.path.join(
            context["cs_data_root"],
            "__LOGS__",
            "_checker",
            "results",
            magic[0],
            magic[1],
            magic,
        ),
        "rb",
    ) as f:
        out = context["csm_cslog"].unprep(f.read())
    return out


def compute_page_stats(context, user, path, keys=None):
    """
    Compute statistics about the given user and page.

    This function is designed to provide all the information one could want to
    know about a given page, including both information about the page itself
    and about the given user's activities on the page.

    Exactly what values are computed and included in the result depends on the
    value of the optional parameter `keys`.  If no value is provided, all of
    the following keys are included in the resulting dictionary.  Otherwise,
    only the keys given by `keys` are included.

    Possible keys are:

    * `'context'`: an approximation of the context the user would see if they
        loaded the page, after the entire page load completes (including the
        handler)
    * `'questions'`: an `OrderedDict` mapping question names to tuples, in the
        same order they are specified on the page.  each value is a tuple of
        the form outputted by `catsoop.tutor.question`
    * `'question_info'`: an ordered dictionary mapping question names to
        dictionaries with information about those questions
    * `'state'`: the user's most recent "problemstate" log entry for this page
    * `'actions'`: a list containing all the user's actions on this page
    * `'manual_grades'`: a list containing all manual grading entries for the
        user on this page (i.e., all grades assigned _to them_)

    If the function is simply used to look up logs, it can be reasonably
    efficient.  If it is used to inspect the context, it will be a bit slower,
    as it must then simulate the entire process associated with the given user
    loading the given page.

    **Parameters:**

    * `context`: the context associated with this request
    * `user`: the name of the user whose stats we want to compute
    * `path`: a list of strings representing the path of interest

    **Optional Parameters:**

    * `keys` (default `None`): a list of strings representing the keys of
    * interest.  if no value is specified, all possible keys are included

    **Returns:** a dictionary containing the information detailed above
    """
    logging = cslog
    if keys is None:
        keys = ["context", "question_info", "state", "actions", "manual_grades"]
    keys = list(keys)

    out = {}
    if "state" in keys:
        keys.remove("state")
        out["state"] = logging.most_recent(user, path, "problemstate", {})
    if "actions" in keys:
        keys.remove("actions")
        out["actions"] = logging.read_log(user, path, "problemactions")
    if "manual_grades" in keys:
        keys.remove("manual_grades")
        out["manual_grades"] = logging.read_log(user, path, "problemgrades")
    if "question_info" in keys and "context" not in keys:
        qi_log = logging.most_recent("_question_info", path, "question_info", None)
        if qi_log is not None:
            keys.remove("question_info")
            out["question_info"] = qi_log["questions"]

    if len(keys) == 0:
        return out

    # spoof loading the page for the user in question
    new = dict(context)
    loader.load_global_data(new)
    new["cs_path_info"] = path
    cfile = context["csm_dispatch"].content_file_location(context, new["cs_path_info"])
    loader.do_early_load(context, path[0], path[1:], new, cfile)
    new["cs_course"] = path[0]
    new["cs_username"] = user
    new["cs_form"] = {"action": "passthrough"}
    new["cs_user_info"] = {"username": user}
    new["cs_user_info"] = auth.get_user_information(new)
    loader.do_late_load(context, path[0], path[1:], new, cfile)
    if "cs_post_load" in new:
        new["cs_post_load"](new)
    handle_page(new)
    if "cs_post_handle" in new:
        new["cs_post_handle"](new)

    if "context" in keys:
        keys.remove("context")
        out["context"] = new
    if "question_info" in keys:
        keys.remove("question_info")
        items = new["cs_defaulthandler_name_map"].items()
        out["question_info"] = OrderedDict()
        for (n, (q, a)) in items:
            qi = out["question_info"][n] = {}
            qi["csq_name"] = n
            qi["csq_npoints"] = q["total_points"](**a)
            qi["csq_display_name"] = a.get("csq_display_name", "csq_name")
            qi["qtype"] = q["qtype"]
            qi["csq_grading_mode"] = a.get("csq_grading_mode", "auto")
    for k in keys:
        out[k] = None
    return out


def qtype_inherit(context, other_type):
    """
    Helper function for a question type to inherit from another question type.

    This loads all values from the given question type into the given context
    (typically, the environment associated with a "child" question type).

    **Parameters:**

    * `context`: the dictionary into which the inherited values should be
        placed
    * `other_type`: a string containing the name of the question type whose
        values should be inherited

    **Returns:** `None`
    """
    base, _ = question(context, other_type)
    context.update({k: v for k,v in base.items() if k != "qtype"})


def _wrapped_defaults_maker(context, name):
    orig = context[name]

    def _wrapped_func(*args, **kwargs):
        info = dict(context.get("defaults", {}))
        info.update(context["cs_question_type_defaults"].get(context["qtype"], {}))
        info.update(kwargs)
        return orig(*args, **info)

    return _wrapped_func


def question(context, qtype, **kwargs):
    """
    Generate a data structure representing a question.

    Looks for the specified question type in the course level first, and then
    in the global location.

    This function is called as `tutor.question(qtype, **kwargs)` in almost all
    cases; i.e., it is called without the first argument.  A hack in
    `catsoop.loader.cs_compile` will insert the first argument.

    **Parameters:**

    * `context`: the context associated with this request
    * `qtype`: the name of the requested question type, as a string

    **Keyword Arguments:**

    * The keyword arguments given to this function represent options for it
        (e.g., `csq_soln`).  The options that have an effect depend on the
        question type.  In the case of XML or Markdown input format, all
        variables defined in the environment associated with this question are
        passed in as keyword arguments.

    **Returns:** a tuple containing two dictionaries: the first contains the
    variables defined by the question type, and the second contains the
    environment associated with the question (including variables defined in
    the &lt;question&gt; tag).
    """
    try:
        course = context["cs_course"]
        qtypes_folder = os.path.join(
            context.get("cs_data_root", base_context.cs_data_root),
            "courses",
            course,
            "__QTYPES__",
        )
        loc = os.path.join(qtypes_folder, qtype)
        fname = os.path.join(loc, "%s.py" % qtype)
        assert os.path.isfile(fname)
    except:
        qtypes_folder = os.path.join(
            context.get("cs_fs_root", base_context.cs_fs_root), "__QTYPES__"
        )
        loc = os.path.join(qtypes_folder, qtype)
        fname = os.path.join(loc, "%s.py" % qtype)
    new = dict(context)
    new["csm_base_context"] = new["base_context"] = base_context
    pre_code = (
        "import sys\n"
        "_orig_path = sys.path\n"
        "if %r not in sys.path:\n"
        "    sys.path = [%r] + sys.path\n\n"
    ) % (loc, loc)
    new["qtype"] = qtype
    x = loader.cs_compile(fname, pre_code=pre_code, post_code="sys.path = _orig_path")
    exec(x, new)
    for i in {
        "total_points",
        "handle_submission",
        "handle_check",
        "render_html",
        "answer_display",
    }:
        if i in new:
            new[i] = _wrapped_defaults_maker(new, i)
    return (new, kwargs)


def handler(context, handler, check_course=True):
    """
    Generate a data structure representing an activity.


    **Parameters:**

    * `context`: the context associated with this request
    * `handler`: the name of the requested handler as a string

    **Optional Parameters:**

    * `check_course` (default `True)`: if `True`, look for the specified
        handler in the course level first, and then in the global location;
        otherwise, look only in the global location

    **Returns:** a dictionary containing the variables defined by the handler
    """
    new = {}
    new["csm_base_context"] = new["base_context"] = base_context
    for i in context:
        if i.startswith("csm_"):
            new[i] = new[i[4:]] = context[i]
    try:
        assert check_course
        course = context["cs_course"]
        qtypes_folder = os.path.join(
            context.get("cs_data_root", base_context.cs_data_root),
            "courses",
            course,
            "__HANDLERS__",
        )
        loc = os.path.join(qtypes_folder, handler)
        fname = os.path.join(loc, "%s.py" % handler)
        assert os.path.isfile(fname)
    except:
        fname = os.path.join(
            context.get("cs_fs_root", base_context.cs_fs_root),
            "__HANDLERS__",
            handler,
            "%s.py" % handler,
        )
    code = loader.cs_compile(fname)
    exec(code, new)
    return new


def get_release_date(context):
    """
    Get the release date of a page from the given context.

    The inspected variable is `cs_release_date`.  If `cs_release_date` has not
    been set, `'ALWAYS'` will be used (1 January 1900 at 00:00).

    Additionally, if `cs_realize_time` is defined in the given context, it will
    be used in place of `catsoop.time.realize_time` (note that it must have the
    same number and type of arguments, and the same return type).

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** an instance of `datetime.datetime` representing the page's
    release date.
    """
    rel = context.get("cs_release_date", "ALWAYS")
    if callable(rel):
        rel = rel(context)
    realize = context.get("cs_realize_time", time.realize_time)
    return realize(context, context.get("cs_release_date", "ALWAYS"))


def get_due_date(context, do_extensions=False):
    """
    Get the due date of a page from the given context.

    The inspected variable is `cs_due_date`.  If `cs_due_date` is not defined,
    `'NEVER'` will be used (31 December 9999 at 23:59).

    Additionally, if `cs_realize_time` is defined in context, it will be used
    in place of `catsoop.time.realize_time`.

    **Parameters:**

    * `context`: the context associated with this request

    **Optional Parameters:**

    * `do_extensions` (default `False`): if `True`, look in the user's information for extensions and apply them

    **Returns:** an instance of `datetime.datetime` representing the page's due
    date.
    """
    due = context.get("cs_due_date", "NEVER")
    if callable(due):
        due = due(context)
    realize = context.get("cs_realize_time", time.realize_time)
    due = realize(context, due)
    try:
        if do_extensions:
            extensions = context["cs_user_info"].get("extensions", [])
            for ex in extensions:
                if all(i == j for i, j in zip(e[0], path)):
                    due += timedelta(days=ex[1])
    except:
        pass
    return due


def available_courses():
    """
    Returns a list of available courses on the system.

    This function loops over directories in the `courses` directory.  For each,
    it executes its top-level `preload.py`.  If `cs_course_available` is `True`
    (or not specified), that course is included in the listing.

    **Returns:** a list of tuples.  Each tuple contains `(shortname,
    longname)`, where `shortname` is the name to use in a URL referencing the
    course, and `longname` is a more descriptive name (governed by the value of
    `cs_long_name` in that course's `preload.py` file).
    """
    base = os.path.join(base_context.cs_data_root, "courses")
    if not os.path.isdir(base):
        return []
    out = []
    for course in os.listdir(base):
        if course.startswith("_") or course.startswith("."):
            continue
        if not os.path.isdir(os.path.join(base, course)):
            continue
        try:
            data = loader.spoof_early_load([course])
        except:
            out.append((course, None))
            continue
        if data.get("cs_course_available", True):
            t = data.get("cs_long_name", course)
            out.append((course, t))
    return out


def handle_page(context):
    """
    Determine and invoke the appropriate handler for a page.

    If `cs_handler` is defined in the given context, then the handler with that
    name is used.  Otherwise, the default handler is used.

    Regardless, the given handler's `handle` function is called on the given
    context.  The overall result of this function depends on that function's
    output:

    * if `handle` returns a 3-tuple (representing a specific HTTP response to
        send), that value is returned directly (and `catsoop.dispatch.main` will
        send that response directly).
    * otherwise, `cs_content` is replaced with the result

    **Parameters:**

    * `context`: the context associated with this request (from which
    * `cs_handler` is retrieved)

    **Returns:** a value based on the result of the chosen handler's `handle`
    function (see above).
    """
    hand = context.get("cs_handler", "default")
    h = handler(context, hand)
    result = h["handle"](context)
    if isinstance(result, tuple):
        return result
    context["cs_content"] = result


def _new_random_seed(n=100):
    try:
        return os.urandom(n)
    except:
        return "".join(random.choice(string.ascii_letters) for i in range(n))


def _get_random_seed(context, n=100, force_new=False):
    uname = context["cs_username"]
    if force_new:
        stored = None
    else:
        stored = context["csm_cslog"].most_recent(
            uname, context["cs_path_info"], "random_seed", None
        )
    if stored is None:
        stored = _new_random_seed(n)
        context["csm_cslog"].update_log(
            uname, context["cs_path_info"], "random_seed", stored
        )
    return stored


def init_random(context):
    """
    Initialize the random number generator for per-user, per-page randomness.

    Random seeds are stored in a log.  This function will try to read that log
    to determine the appropriate random seed for this user and page.  If no
    such seed exists, a new random value is generated (from `/dev/urandom` if
    possible).

    This value is then stored as `cs_random_seed` and used to seed the
    `random.Random` instance in `cs_random`.

    This function is called as `tutor.init_random()` in almost all cases; i.e.,
    it is called with no arguments.  A hack in `catsoop.loader.cs_compile` will
    insert the argument.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** `None`
    """
    try:
        seed = _get_random_seed(context)
    except:
        seed = "___".join([context["cs_username"]] + context["cs_path_info"])
    context["cs_random_seed"] = seed
    context["cs_random"].seed(seed)
    context["cs_random_inited"] = True
