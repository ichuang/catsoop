# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

# Functions for loading specifications into dictionaries

import os
import re
import sys
import random
import marshal
import importlib
import traceback

from . import time
from . import language
from . import base_context

importlib.reload(base_context)

_malformed_question = "<font color='red'>malformed <tt>question</tt></font>"

def clean_builtins(d):
    """
    Cleans __builtins__ out of a dictionary to make it serializable
    """
    try:
        del d['__builtins__']
    except:
        pass


def load_global_data(into, check_values=True):
    """
    Load global data into the specified dictionary

    Includes anything specified in base_context.py and config.py, as well as
    all of the modules in the catsoop directory.
    """
    into['cs_time'] = time.now()
    into['cs_timestamp'] = time.detailed_timestamp(into['cs_time'])
    if check_values and len(base_context._cs_config_errors) > 0:
        m = ('ERROR while loading global CAT-SOOP configuration:\n\n' +
             '\n'.join(base_context._cs_config_errors))
        return m
    try:
        thisdir = os.path.dirname(__file__)
        sys.path.insert(0, thisdir)
        into['sys'] = sys
        fname = os.path.join(thisdir, 'base_context.py')
        with open(fname) as f:
            t = f.read()
            t = '__name__ = "catsoop.base_context"\n' + t
            c = compile(t, fname, 'exec')
        exec(c, into)
        into['cs_random'] = random.Random()
        into['csm_base_context'] = into['base_context'] = base_context
        into['csm_cslog'] = into['cslog'] = into['csm_logging'].get_logger(into)
        clean_builtins(into)
        into['csm_loader'] = sys.modules[__name__]
    except Exception as e:
        return traceback.format_exc(e)


def get_course_fs_location(context, course, join=True):
    """
    Returns the base location of the specified course on disk.
    """
    fs_root = context.get('cs_fs_root', base_context.cs_fs_root)
    if course == 'cs_util':
        rtn = [fs_root, '__UTIL__']
    elif course == 'cs_api':
        rtn = [fs_root, '__API__']
    elif course == '__QTYPE__':
        rtn = [fs_root, '__QTYPES__']
    else:
        data_root = context.get('cs_data_root', base_context.cs_data_root)
        rtn = [data_root, 'courses', course]
    if join:
        return os.path.join(*rtn)
    return rtn


def do_early_load(context, course, path, into, content_file=None):
    """
    Load data from preload.py in the appropriate directories for this request.

    The preload.py file from the course will be executed first, followed by
    the next level down the path, and so on until the file from this request's
    path has been run.  The preload files will also be run from this page's
    children, though they will be executed into separate directories, and
    stored in the 'children' key of the supplied dictionary.

    This function is run before loading user data, so the code in preload.py
    cannot make use of user information, though it can make use of any
    variables specified in base_context or in preload files from higher up
    the tree.
    """
    into['cs_course'] = course
    directory = get_course_fs_location(context, course)
    if content_file is None:
        return 'missing'
    if os.path.basename(content_file).rsplit('.', 1)[0] != 'content':
        path = path[:-1]
    for ix, i in enumerate(path):
        new_name = os.path.join(directory, 'preload.py')
        if os.path.isfile(new_name):
            exec(cs_compile(new_name), into)
        try:
            newdir = get_directory_name(context, course, path[:ix], i)
        except FileNotFoundError:
            return 'missing'
        if newdir is None:
            return 'missing'
        directory = os.path.join(directory, newdir)
    new_name = os.path.join(directory, 'preload.py')
    if os.path.isfile(new_name):
        exec(cs_compile(os.path.join(directory, 'preload.py')), into)


def cs_compile(fname, pre_code='', post_code=''):
    """
    Return a code object representing the code in fname.  If fname has already
    been compiled, load the code object using the marshal module.  Otherwise,
    compile the code using the built-in compile function.
    """
    base_fname = fname.rsplit('.', 1)[0]
    cache_tag = sys.implementation.cache_tag
    cname = '.'.join([base_fname, cache_tag, 'pycs'])
    try:
        # this is a 'try' block instead of a straight conditional to account
        # for cases where, e.g., cname doesn't exist.
        if os.stat(cname).st_mtime <= os.stat(fname).st_mtime:
            # if the file has been updated since it was last compiled,
            # we need to re-compile
            raise Exception
    except:
        # make some modifications to the code, and compile
        code = '\n\n'.join([pre_code, open(fname).read(), post_code])
        code = code.replace('tutor.question(', 'tutor.question(globals(),')
        x = compile(
            code.replace('tutor.init_random()',
                         'tutor.init_random(globals())').strip(), cname,
            'exec')
        try:
            # write the compiled code to disk
            ccode = open(cname, 'wb')
            marshal.dump(x, ccode)
            ccode.close()
        except:
            return x
    # grab the compiled code and return it
    ccode = open(cname, 'rb')
    out = marshal.load(ccode)
    ccode.close()
    return out


def get_directory_name(context, course, path, name):
    """
    Return the actual name of a directory (including sorting numbers)
    given the shortname of the resource it represents.
    """
    s = get_subdirs(context, course, path)
    for i in s:
        if ((i == name and not i.startswith('_') and not i.startswith('.')) or
                ('.' in i and '.'.join(i.split('.')[1:]) == name)):
            return i
    return None


def get_subdirs(context, course, path):
    """
    Return the subdirectories of path that contain resources.
    """
    path_pieces = get_course_fs_location(context, course, join=False)
    for ix, i in enumerate(path):
        d = get_directory_name(context, course, path[:ix], i)
        if d is None:
            return []
        path_pieces.append(d)
    directory = os.path.join(*path_pieces)
    return [i for i in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, i)) and re.match(
                '[^_\.].*', i) is not None]


def do_late_load(context, course, path, into, content_file=None):
    """
    Load data from the Python file specified by the content file in the
    appropriate directory for this request.

    This function is run after loading user data, so the code in the content
    file can make use of that information, which includes user permissions.
    """
    directory = os.path.dirname(content_file)
    if os.path.basename(content_file).rsplit('.', 1)[0] == 'content':
        subdirs = get_subdirs(context, course, path)
        shortnames = [('.'.join(i.split('.')[1:])
                       if re.match('\d*\..*', i) else i) for i in subdirs]
        children = dict([(i, dict(into)) for i in shortnames])
        for d, name in zip(subdirs, shortnames):
            new_name = os.path.join(directory, d, 'preload.py')
            if os.path.isfile(new_name):
                exec(cs_compile(new_name), children[name])
            children[name]['directory'] = d
        into['cs_children'] = children
    else:
        into['cs_children'] = {}
    into['cs_source_format'] = content_file.rsplit('.', 1)[-1]
    into['cs_content'] = open(content_file).read()
    if 'cs_post_load' in into:
        into['cs_post_load'](into)
    language.source_formats[into['cs_source_format']](into)
