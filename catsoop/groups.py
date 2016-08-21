# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.


def get_group_log_name(course, path):
    """
    Returns the relevant log name for groups associated with the given path
    """
    return '.'.join(['groups'] + path)


def list_groups(context, course, path):
    """
    Returns a dictionary mapping group names to lists of group members
    """
    log = context['csm_cslog']
    return log.most_recent(None, course,
                           get_group_log_name(path), {})


def get_section(context, course, username):
    if context.get('cs_groups_per_section', False):
        uinfo = read_user_file(context, course, username, {})
        return uinfo.get('section', None)
    else:
        return None


def get_group(context, course, path, username):
    """
    Returns the section number and group to which the given user belongs, or
    None if they have not been assigned a group.
    """
    groups = list_groups(context, course, path)
    secnum = get_section(context, course, username)
    for group in groups[secnum]:
        if username in groups[secnum][group]:
            return (secnum, group)
    return None, None


def add_to_group(context, course, path, username, group):
    """
    Adds the given user to the given group.  Returns None on success, or an
    error message on failure.
    """
    log = context['csm_cslog']
    section = get_section(context, course, username)
    preexisting_group = get_group(context, path, username)
    if preexisting_group != (None, None):
        return "%s is already assigned to a group (section %s group %s)" % ((username,) + preexisting_group)
    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = x[section].get(group, []) + [username]
        return x
    try:
        log.modify_most_recent(course, username,
                               get_group_log_name(course, path),
                               {}, _transformer)
    except:
        return 'An error occured when assigning to group.'


def new_group(context, course, path, section, group):
    """
    Adds a new (empty) group to the list of groups.
    """
    log = context['csm_cslog']
    section = get_section(context, course, username)
    groups = list_groups(context, course, path)
    if group in groups.get(section, {}):
        return "%r is already a group for section %s." % (group, section)
    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = [] 
        return x
    try:
        log.modify_most_recent(course, username,
                               get_group_log_name(course, path),
                               {}, _transformer)
    except:
        return 'An error occured when creating new group.'


def remove_from_group(context, course, path, username, group):
    """
    Removes the given user to the given group.  Returns None on success, or an
    error message on failure.
    """
    log = context['csm_cslog']
    section = get_section(context, course, username)
    preexisting_group = get_group(context, path, username)
    if preexisting_group != (section, group):
        return "%s is not assigned to section %s group %s." % (username, section, group)
    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = [i for i in x[section].get(group, [])
                             if i != username]
        return x
    try:
        log.modify_most_recent(course, username,
                               get_group_log_name(course, path),
                               {}, _transformer)
    except:
        return 'An error occured when removing from group.'


def update_groups(context, course, path, section, group, newdict):
    """
    Updates group assignments for the given group and section to match those
    provided in newdict
    """
    log = context['csm_cslog']
    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = x[section].get(group, {})
        x[section][group].update(newdict)
        return x
    try:
        log.modify_most_recent(course, username,
                               get_group_log_name(course, path),
                               {}, _transformer)
    except:
        return 'An error occured when updating groups.'


def overwrite_groups(context, course, path, section, group, newdict):
    """
    Overwrites group assignments for the given group and section to be those
    provided in newdict
    """
    log = context['csm_cslog']
    def _transformer(x):
        x[section] = x.get(section, {})
        x[section][group] = newdict
        return x
    try:
        log.modify_most_recent(course, username,
                               get_group_log_name(course, path),
                               {}, _transformer)
    except:
        return 'An error occured when overwriting groups.'
