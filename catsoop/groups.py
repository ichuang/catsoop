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
Utilities for handling grouping of students
"""

import random

from . import util


def list_groups(context, path):
    """
    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of strings representing the path we're interested in

    **Returns:** a dictionary mapping group names to lists of group members
    """
    log = context["csm_cslog"]
    return log.most_recent("_groups", path, "groups", {})


def get_section(context, course, username):
    """
    Helper function to determine a user's section, if any.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the course
    * `username`: the user whose section we want to find

    **Returns:** a string; the user's section, or `'default'` if the user has
    no section
    """
    uinfo = util.read_user_file(context, course, username, {})
    return str(uinfo.get("section", "default"))


def get_group(context, path, username, groups=None, secnum=None):
    """
    Get a user's group for a page

    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of strings representing the path we're interested in
    * `username`: the user whose group we want to find

    **Optional Parameters:**

    * `groups` (default `None`): a listing of groups (of the same form as the
        output from `catsoop.groups.list_groups`).  If none is specified,
        `catsoop.groups.list_groups` is invoked.
    * `secnum` (default `None`): the section in which to look for groups.  If
        none is specified, `catsoop.groups.get_section` is invoked).

    **Returns:** the section number and group to which the given user belongs, or
    None if they have not been assigned a group.
    """
    course = path[0]
    if groups is None:
        groups = list_groups(context, path)
    if secnum is None:
        secnum = get_section(context, course, username)
    for group in groups.get(secnum, {}):
        if username in groups[secnum][group]:
            return (secnum, group, groups[secnum][group])
    return None, None, None


def add_to_group(context, path, username, group):
    """
    Adds the given user to the given group.

    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of strings representing the path we're interested in
    * `username`: the user whose group we want to find
    * `group`: the name of the group to which the student should be added

    **Returns:** `None` on success, or an error message on failure.
    """
    course = path[0]
    log = context["csm_cslog"]
    section = get_section(context, course, username)
    preexisting_group = get_group(context, path, username)
    if preexisting_group != (None, None, None):
        return "%s is already assigned to a group (section %s group %s)" % (
            (username,) + preexisting_group[:2]
        )

    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = x[section].get(group, []) + [username]
        return x

    try:
        log.modify_most_recent("_groups", path, "groups", {}, _transformer)
    except:
        return "An error occured when assigning to group."


def remove_from_group(context, path, username, group):
    """
    Removes the given user from the given group.

    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of strings representing the path we're interested in
    * `username`: the user whose group we want to find
    * `group`: the name of the group from which the student should be removed

    **Returns:** `None` on success, or an error message on failure.
    """
    course = path[0]
    log = context["csm_cslog"]
    section = get_section(context, course, username)
    preexisting_group = get_group(context, path, username)
    if preexisting_group[:-1] != (section, group):
        return "%s is not assigned to section %s group %s." % (username, section, group)

    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = [i for i in x[section].get(group, []) if i != username]
        if len(x[section][group]) == 0:
            del x[section][group]
        return x

    try:
        log.modify_most_recent("_groups", path, "groups", {}, _transformer)
    except:
        return "An error occured when removing from group."


def overwrite_groups(context, path, section, newdict):
    """
    Overwrites group assignments for the given section

    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of strings representing the path we're interested in
    * `section`: the section whose groups should be replaced
    * `newdict`: the new group assignments, as a dictionary mapping group names
        to lists of group members' usernames

    **Returns:** `None` on success, or an error message on failure.
    """
    log = context["csm_cslog"]

    def _transformer(x):
        x[section] = newdict
        return x

    try:
        log.modify_most_recent("_groups", path, "groups", {}, _transformer)
    except:
        return "An error occured when overwriting groups."


def make_all_groups(context, path, section):
    """
    Randomly assigns groups within the given section for the given page,
    overwriting any existing groups for that section and page.

    All users with a file in `__USERS__` who are members of the given section
    are considered.

    Several variables in the given `context` affect the way groups are
    assigned:

    * The students can optionally be separated into subcategories (such that
        each student will only be partnered with other within their
        subcategory) by specifying a function `cs_group_category(path,
        username) => category_name`.

    * The names to be given to the various groups can be specified in
        `cs_group_names`, which should be a list of strings.

    * Within each subcategory, students are randomly shuffled, and groups of
        size `cs_group_size` are made from the shuffled list.  Students will
        _never_ be paired with students outside their subcategory, even is
        `cs_group_size` does not evenly divide the number of students in a
        category.

    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of strings representing the path we're interested in
    * `section`: the section whose groups should be replaced

    **Returns:** `None` on success, or an error message on failure.
    """
    course = path[0]
    util = context["csm_util"]
    size = context.get("cs_group_size", 2)

    def cat(uname):
        f = context.get("cs_group_category", lambda path, uname: "all")
        return f(path, uname)

    group_names = context.get("cs_group_names", list(map(str, range(1000))))
    group_names = list(group_names)
    students = util.list_all_users(context, course)

    def filt(uinfo):
        return uinfo.get("role", None) == "Student" and str(
            uinfo.get("section", None)
        ) == str(section)

    cats = {}
    for s in students:
        if not filt(util.read_user_file(context, course, s, {})):
            continue
        c = cat(s)
        cats[c] = cats.get(c, []) + [s]

    output = {}
    for c in sorted(cats):
        if c is None:
            continue
        random.shuffle(cats[c])
        while len(cats[c]) > 0:
            out, cats[c] = cats[c][:size], cats[c][size:]
            g = group_names[len(output)]
            output[g] = out

    err = overwrite_groups(context, path, section, output)
    return err
