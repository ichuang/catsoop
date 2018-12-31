# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
Functions for loading page specifications into dictionaries

This file contains functions that do a lot of the "heavy lifting" associated
with loading pages, including handling preload, managing parsing/evaluation of
code in content files, and evaluation of plugins.
"""

import os
import re
import sys
import shutil
import random
import marshal
import importlib
import traceback

from collections import OrderedDict

from . import time
from . import language
from . import debug_log
from . import base_context

importlib.reload(base_context)


def get_file_data(context, form, name):
    """
    Load the contents of a submission to the question with the given name in
    the given form, taking file upload preferences into account.

    Depending on the value of `cs_upload_management`, the data for a file might
    be stored directly on disk, or as part of a CAT-SOOP log.  This function
    grabs the associated data as a bytestring.

    **Parameters:**

    * `context`: the context associated with this request
    * `form`: a dictionary mapping names to values, as in `cs_form`
    * `name`: the name of the question whose data we should grab

    **Returns:** a bytestring containing the data
    """
    data = form[name]
    up = context["cs_upload_management"]
    if isinstance(data, list):
        if up == "file":
            path = os.path.join(
                context["cs_data_root"], "__LOGS__", "_uploads", data[1], "content"
            )
            with open(path, "rb") as f:
                data = f.read()
            return data
        elif up == "db":
            return context["csm_thirdparty"].data_uri.DataURI(data[1]).data
        else:
            raise Exception("unknown upload management style: %r" % up)
    elif isinstance(data, str):
        return data.encode()
    else:  # bytes
        return data


def clean_builtins(d):
    """
    Removes the `'__builtins__'` key from a dictionary to make it serializable

    **Parameters:**

    * `d`: the dictionary to clean

    **Returns:** `None`
    """
    try:
        del d["__builtins__"]
    except:
        pass


def plugin_locations(context, course):
    """
    Look up the directories from which plugins should be loaded

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course from which plugins should be loaded (or `None` if no
        course).

    **Returns:** a list of directories from which plugins should be loaded.
    """
    out = [
        os.path.join(context.get("cs_fs_root", base_context.cs_fs_root), "__PLUGINS__")
    ]
    if course is not None:
        out.append(
            os.path.join(
                context.get("cs_data_root", base_context.cs_data_root),
                "courses",
                course,
                "__PLUGINS__",
            )
        )
    return out


def available_plugins(context, course):
    """
    Determine all the plugins that can be loaded

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course from which plugins should be loaded (or `None` if no
        course).

    **Returns:** a list of the full paths to all available plugins' directories
    """
    out = []
    for loc in plugin_locations(context, course):
        try:
            p = list(sorted(os.listdir(loc)))
        except:
            p = []
        for i in p:
            fullname = os.path.join(loc, i)
            if os.path.isdir(fullname):
                out.append(fullname)
    return out


def get_plugin_code_file(plugin, type_):
    """
    Return the filename of a particular hook from the given plugin

    **Parameters:**

    * `plugin`: a string containing the name of a directory containing a plugin
    * `type_`: the name of a plugin hook as a string (e.g., `'post_load'`)

    **Returns:** a string containing the full path to the given hook for the
    given plugin if it exists, or `None` otherwise
    """
    full_fname = os.path.join(plugin, "%s.py" % type_)
    if os.path.isfile(full_fname):
        return full_fname
    return None


def run_plugins(context, course, type_, into):
    """
    Run the given hook for all plugins

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course from which plugins should be loaded (or `None` if no
        course).
    * `type_`: the name of a plugin hook as a string (e.g., `'post_load'`)
    * `into`: the context in which the plugins should be run

    **Returns:** `None`
    """
    plugins = available_plugins(context, course)
    for p in plugins:
        codefile = get_plugin_code_file(p, type_)
        if codefile is None:
            continue
        exec(cs_compile(codefile), into)


def load_global_data(into, check_values=True):
    """
    Load global data into the specified dictionary

    Includes anything specified in `base_context.py` and `config.py`, as well
    as all of the modules in the catsoop directory.

    **Parameters:**

    * `into`: a dictionary into which the built-in values should be loaded

    **Optional Parameters:**

    * `check_values` (default `True`): whether to error on invalid
        configuration values

    **Returns:** `None` on success, or a string containing an error message on
    failure
    """
    into["cs_time"] = time.now()
    into["cs_timestamp"] = time.detailed_timestamp(into["cs_time"])
    if check_values and len(base_context._cs_config_errors) > 0:
        m = "ERROR while loading global CAT-SOOP configuration:\n\n" + "\n".join(
            base_context._cs_config_errors
        )
        debug_log.LOGGER.error(m)
        return m
    try:
        thisdir = os.path.dirname(__file__)
        sys.path.insert(0, thisdir)
        into["sys"] = sys
        fname = os.path.join(thisdir, "base_context.py")
        into["__file__"] = fname
        with open(fname) as f:
            t = f.read()
            t = '__name__ = "catsoop.base_context"\n' + t
            c = compile(t, fname, "exec")
        exec(c, into)
        into["cs_random"] = random.Random()
        into["csm_base_context"] = into["base_context"] = base_context
        clean_builtins(into)
        into["csm_loader"] = sys.modules[__name__]
        debug_log.setup_logging(into)		# setup global log levels
        into['cs_debug_logger'] = debug_log.LOGGER
    except Exception as e:
        debug_log.LOGGER.error("Exception encountered when trying to load global context: %s" % str(e))
        debug_log.LOGGER.error("traceback: %s" % traceback.format_exc())
        return traceback.format_exc(e)


def get_course_fs_location(context, course, join=True):
    """
    Returns the base location of the specified course on disk, including
    "special" courses (`_util`, `_qtype`, etc).

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the name of the course

    **Optional Parameters:**

    * `join` (default `True`): controls the return type.  If `True`, the
        elements in the path will be joined together and the return value will
        be a string.  If `False`, the return value will be a list of directory
        names.

    **Returns:** depends on the value of `join` (see above).
    """
    fs_root = context.get("cs_fs_root", base_context.cs_fs_root)
    if course == "_util":
        rtn = [fs_root, "__UTIL__"]
    elif course == "_qtype":
        rtn = [fs_root, "__QTYPES__"]
    elif course == "_auth":
        rtn = [fs_root, "__AUTH__"]
    else:
        data_root = context.get("cs_data_root", base_context.cs_data_root)
        rtn = [data_root, "courses", course]
    if join:
        return os.path.join(*rtn)
    return rtn


def spoof_early_load(path):
    """
    Generate a new context, loading the global data and running the
    `preload.py` files for the specified path.

    This function is particularly useful in scripts, as many of the functions
    in CAT-SOOP require a "context" in which to run.

    **Parameters:**

    * `path`: a list of strings (starting with a course name) representing the
        path whose preload context should be spoofed

    **Returns:** a context dictionary containing the global values and those
    defined in the `preload.py` files along the specified path
    """
    ctx = {}
    load_global_data(ctx)
    opath = path
    ctx["cs_course"] = path[0]
    ctx["cs_path_info"] = opath
    path = path[1:]
    cfile = ctx["csm_dispatch"].content_file_location(ctx, opath)
    do_early_load(ctx, ctx["cs_course"], path, ctx, cfile)
    return ctx


def do_early_load(context, course, path, into, content_file=None):
    """
    Load data from `preload.py` files in the appropriate directories for this
    request.

    The `preload.py` file from the course will be executed first, followed by
    the next level down the path, and so on until the file from this request's
    path has been run.  The preload files will also be run from this page's
    children, though they will be executed into separate directories, and
    stored in the 'children' key of the supplied dictionary.

    This function is run before loading user data, so the code in `preload.py`
    cannot make use of user information, though it can make use of any
    variables specified in the base context or in preload files from higher up
    the tree.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course associated with this request
    * `path`: the path associated with this request, as a list of strings _not_
        including the course
    * `into`: the dictionary in which the code should be executed

    **Optional Parameters:**

    * `content_file` (default `None`): the name of the content file associated
        with this page load.  We need to know this because the behavior is
        slightly different depending on whether the associated content file is
        indeed a `content.xx` file (in which case we can run a `preload.py` for
        _every element in the given path_) or whether it is an arbitrary file
        (in which case we cannot run a `preload.py` for the last element in the
        list).

    **Returns:** `None` on success, or the string `'missing'` on failure
    """
    into["cs_course"] = course
    directory = get_course_fs_location(context, course)
    if content_file is None:
        return "missing"
    breadcrumbs = []
    run_plugins(context, course, "pre_preload", into)
    if os.path.basename(content_file).rsplit(".", 1)[0] != "content":
        path = path[:-1]
    for ix, i in enumerate(path):
        new_name = os.path.join(directory, "preload.py")
        if os.path.isfile(new_name):
            exec(cs_compile(new_name), into)
        breadcrumbs.append(dict(into))
        try:
            newdir = get_directory_name(context, course, path[:ix], i)
        except FileNotFoundError:
            return "missing"
        if newdir is None:
            return "missing"
        directory = os.path.join(directory, newdir)
    new_name = os.path.join(directory, "preload.py")
    if os.path.isfile(new_name):
        exec(cs_compile(os.path.join(directory, "preload.py")), into)
    breadcrumbs.append(dict(into))
    into["cs_loader_states"] = breadcrumbs
    run_plugins(context, course, "pre_auth", into)


_code_replacements = [
    ("tutor.question(", "tutor.question(globals(),"),
    ("tutor.qtype_inherit(", "tutor.qtype_inherit(globals(),"),
    ("tutor.init_random()", "tutor.init_random(globals())"),
]


def _atomic_write(fname, contents):
    tname = fname + ".temp"
    with open(tname, "w") as f:
        f.write(contents)
    shutil.move(tname, fname)


def cs_compile(fname, pre_code="", post_code=""):
    """
    Return a code object representing the code in the specified file, after
    making a few CAT-SOOP-specific modifications.

    As a side-effect, store on disk a file containing the updated code, and
    another containing information about how many new lines were added to the
    top of the given file, for use in error reporting.  These pieces are only
    updated if the contents of the given file have changed (based on the
    modification time).

    **Parameters:**

    * `fname`: the name of the file to be compiled

    **Optional Parameters:**

    * `pre_code` (default `''`): a string containing code to be inserted at the
        start of the file
    * `post_code` (default `''`): a string containing code to be inserted at the
        end of the file

    **Returns:** a bytestring containing the compiled code
    """
    base_fname = fname.rsplit(".", 1)[0]
    cache_tag = sys.implementation.cache_tag
    fdirs = os.path.dirname(fname).split(os.sep)
    if fdirs and fdirs[0] == "":
        fdirs.pop(0)
    cname = ".".join([os.path.basename(base_fname), "py"])
    cdir = os.path.join(base_context.cs_data_root, "_cached", *fdirs)
    os.makedirs(cdir, exist_ok=True)
    cname = os.path.join(cdir, cname)
    with open(fname) as _f:
        real_code = _f.read()
    code = "\n\n".join([pre_code, real_code, post_code])
    for i, j in _code_replacements:
        code = code.replace(i, j)
    try:
        # this is a 'try' block instead of a straight conditional to account
        # for cases where, e.g., cname doesn't exist.
        assert os.stat(cname).st_mtime > os.stat(fname).st_mtime
    except:
        _atomic_write(cname, code)
        _atomic_write(cname + ".line_offset", str(len(pre_code) + 2))
    return compile(code, cname, "exec")


def get_directory_name(context, course, path, name):
    """
    Return the actual name of a subdirectory of the given path (including
    sorting numbers) given the shortname of the resource it represents.

    Directories for pages can optionally begin with a series of digits and a
    period, in which case the name of the associated page is the piece
    following that period, and the numbers that come before it are used for
    sorting.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course associated with this request
    * `path`: the path associated with this request, as a list of strings _not_
        including the course
    * `name`: the name of the page being requested (a known child of `path`)

    **Returns:** the appropriate directory name if `name` is indeed a child of
    `path`, or `None` otherwise
    """
    s = get_subdirs(context, course, path)
    for i in s:
        if (i == name and not i.startswith("_") and not i.startswith(".")) or (
            "." in i and ".".join(i.split(".")[1:]) == name
        ):
            return i
    return None


def get_subdirs(context, course, path):
    """
    Return all subdirectories of the given path that represent pages.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course associated with this request
    * `path`: the path associated with this request, as a list of strings _not_
        including the course

    **Returns:** a list of all directory names under `path` that represent
    pages.
    """
    path_pieces = get_course_fs_location(context, course, join=False)
    for ix, i in enumerate(path):
        d = get_directory_name(context, course, path[:ix], i)
        if d is None:
            return []
        path_pieces.append(d)
    directory = os.path.join(*path_pieces)
    return [
        i
        for i in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, i))
        and re.match("[^_\.].*", i) is not None
    ]


def do_late_load(context, course, path, into, content_file=None):
    """
    Load data from the Python file specified by the content file in the
    appropriate directory for this request.

    This function is run after loading user data, so the code in the content
    file can make use of that information, which includes user permissions.

    This function also populates the `cs_children` variable by executing the
    `preload.py` files of this page's children into the given context.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course associated with this request
    * `path`: the path associated with this request, as a list of strings _not_
        including the course
    * `into`: the dictionary in which the code should be executed

    **Optional Parameters:**

    * `content_file` (default `None`): the name of the content file associated
        with this page load.  We need to know this because the behavior is
        slightly different depending on whether the associated content file is
        indeed a `content.xx` file or whether it is an arbitrary file.

    **Returns:** `None`
    """
    run_plugins(context, course, "post_auth", into)
    directory = os.path.dirname(content_file)
    if os.path.basename(content_file).rsplit(".", 1)[0] == "content":
        subdirs = get_subdirs(context, course, path)
        shortnames = [
            (".".join(i.split(".")[1:]) if re.match("\d*\..*", i) else i)
            for i in subdirs
        ]
        children = dict([(i, dict(into)) for i in shortnames])
        for d, name in zip(subdirs, shortnames):
            new_name = os.path.join(directory, d, "preload.py")
            if os.path.isfile(new_name):
                exec(cs_compile(new_name), children[name])
            children[name]["directory"] = d
        into["cs_children"] = children
    else:
        into["cs_children"] = {}
    into["cs_source_format"] = content_file.rsplit(".", 1)[-1]
    with open(content_file) as f:
        into["cs_content"] = f.read()
    if into["cs_source_format"] != "py":
        into["cs_content"] = language.handle_includes(into, into["cs_content"])
        into["cs_content"] = language.handle_python_tags(into, into["cs_content"])
    else:
        exec(context["cs_content"], context)
    if "cs_post_load" in into:
        into["cs_post_load"](into)
    run_plugins(context, course, "post_load", into)
    language.source_formats[into["cs_source_format"]](into)

    if "cs_pre_handle" in into:
        into["cs_pre_handle"](into)
    run_plugins(context, course, "pre_handle", into)

    last_mod = os.stat(content_file).st_mtime
    cache = into["csm_cslog"].most_recent(
        "_question_info", [course] + path, "question_info", None
    )
    if (
        course not in {None, "_util"}
        and (cache is None or last_mod > cache["timestamp"])
        and "cs_problem_spec" in into
    ):
        qs = OrderedDict()
        for i in into["cs_problem_spec"]:
            if isinstance(i, tuple):
                x = qs[i[1]["csq_name"]] = {}
                x["csq_npoints"] = i[0]["total_points"](**i[1])
                x["csq_name"] = i[1]["csq_name"]
                x["csq_display_name"] = i[1].get("csq_display_name", x["csq_name"])
                x["qtype"] = i[0]["qtype"]
                x["csq_grading_mode"] = i[1].get("csq_grading_mode", "auto")
        into["csm_cslog"].overwrite_log(
            "_question_info",
            [course] + path,
            "question_info",
            {"timestamp": last_mod, "questions": qs},
        )
