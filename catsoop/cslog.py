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
"""
Logging mechanisms using RethinkDB
"""

import os
import ast
import rethinkdb as r

from datetime import datetime

from .. import base_context

prep = lambda x: repr(x).encode()
unprep = lambda x: ast.literal_eval(x.decode())


def update_log(course, db_name, logname, new):
    """
    Adds a new entry to the specified log.
    """
    course = course or '__no_course__'
    conn = r.connect(db='catsoop')
    r.table('logs').insert({'course': course, 'username': db_name,
                            'logname': logname, 'data': new,
                            'time': r.now()}).run(conn)
    conn.close()


def overwrite_log(course, db_name, logname, new):
    """
    Overwrites the most recent entry in the specified log.
    """
    course = course or '__no_course__'
    conn = r.connect(db='catsoop')
    r.table('logs').filter((r.row['course'] == course) &
                           (r.row['username'] == db_name) &
                           (r.row['logname'] == logname)).delete().run(conn)
    r.table('logs').insert({'course': course, 'username': db_name,
                            'logname': logname, 'data': new,
                            'time': r.now()}).run(conn)
    conn.close()


def read_log(course, db_name, logname):
    """
    Reads all entries of a log.
    """
    course = course or '__no_course__'
    conn = r.connect(db='catsoop')
    res = r.table('logs').get_all([db_name, course, logname], index='log').run(conn)
    out = [i['data'] for i in res]
    conn.close()
    return out


def most_recent(course, db_name, logname, default=None):
    """
    Reads the most recent entry from a log.
    """
    course = course or '__no_course__'
    conn = r.connect(db='catsoop')
    res = r.table('logs').get_all([db_name, course, logname], index='log').order_by(r.desc('time')).limit(1).run(conn)
    if len(res) == 0:
        out = default
    else:
        out = res[0]['data']
    conn.close()
    return out


def modify_most_recent(course, db_name, log, default=None, transform_func=lambda x: x, method='update'):
    course = course or '__no_course__'
    conn = r.connect(db='catsoop')
    if method == 'overwrite':
        r.table('logs').get_all([db_name, course, logname], index='log').order_by(r.desc('time')).limit(1).update(lambda post: {'data': transform_func(post['data'])}).run(conn)
    else:
        res = r.table('logs').get_all([db_name, course, logname], index='log').order_by(r.desc('time')).limit(1).run(conn)
        for row in res:
            r.table('logs').insert({'course': course, 'username': db_name,
                                    'logname': logname, 'data': transform_func(row['data']),
                                    'time': r.now()}).run(conn)
    conn.close()
