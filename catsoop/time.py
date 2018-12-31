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
"""Utilities for dealing with time"""

import time
from datetime import datetime, timedelta, MAXYEAR

_nodoc = {"datetime", "timedelta", "MAXYEAR"}

days = ["M", "T", "W", "R", "F", "S", "U"]
"List used for mapping weekday numbers to weekday letters"


def realize_time(context, timestring):
    """
    Return an appropriate `datetime.datetime` object based on the given
    timestring.

    The timestring can have one of the following forms:

    * `'NEVER'`: resolves to the maximum date that `datetime` can represent
    * `'ALWAYS'`: resolves to the minimum date that `datetime can represent
    * `'YYYY-MM-DD:HH:MM'` resolves to a particular time (minute resolution)
    * `'W:HH:MM`, where `W` is a letter representing a day of the week,
        resolves to the given time in the week number given by `cs_week_number`,
        starting from `cs_first_monday`.  For example, `'T:09:00'` represents
        Tuesday morning at 9 o'clock.

    **Parameters:**

    * `context`: the context associated with this request (from which
        `cs_first_monday` and `cs_week_number` are read)
    * `timestring`: a string representing the desired time (see above)

    **Returns:** a `datetime.datetime` object corresponding to the time given
    by `timestring`
    """
    if timestring == "NEVER":
        return datetime(year=MAXYEAR, month=12, day=31, hour=23, minute=59, second=59)
    elif timestring == "ALWAYS":
        return datetime(year=1900, month=1, day=1, hour=0, minute=0, second=0)
    elif timestring[0].isdigit():
        # absolute times are specified as strings 'YYYY-MM-DD:HH:MM'
        return datetime.strptime(timestring, "%Y-%m-%d:%H:%M")
    elif timestring[0].isalpha():
        # this is a day and a time
        day, hour, minute = timestring.split(":")
        while len(hour) > 1 and all(i == "0" for i in hour):
            hour = hour[1:]
        while len(minute) > 1 and all(i == "0" for i in minute):
            minute = minute[1:]
        start_date = context["cs_first_monday"]
        wknum = context["cs_week_number"]
        while len(day) > 1:
            if day[-1] == "+":
                wknum += 1
            elif day[-1] == "-":
                wknum -= 1
            day = day[:-1]
        start = realize_time(context, start_date)
        return start + timedelta(
            weeks=(wknum - 1),
            days=days.index(day),
            hours=int(hour),
            minutes=int(minute),
        )
    else:
        raise Exception("invalid time style: %s" % timestring)


def unix(dt):
    """
    Generate a Unix timestamp from an instance of datetime.

    **Parameters:**

    * `dt`: an instance of `datetime.datetime`

    **Returns:** the Unix timestamp corresponding to the given time
    """
    return time.mktime(dt.timetuple())


def now():
    """
    Wraps datetime.now.

    **Returns:** the current time, as an instance of `datetime.datetime`
    """
    return datetime.now()


def long_timestamp(time):
    """
    Generate a (long) human-readable timestamp
    (e.g., `"Wednesday June 05, 2013; 02:58:21 PM"`)

    **Parameters:**

    * `time`: an instance of `datetime.datetime`

    **Returns:** a string containing a human-readable representation of the
    given time
    """
    return time.strftime("%A %B %d, %Y; %I:%M:%S %p")


def short_timestamp(time):
    """
    Generate a (short) human-readable timestamp
    (e.g. `"Jun 05, 2013; 02:58 PM"`)

    **Parameters:**

    * `time`: an instance of `datetime.datetime`

    **Returns:** a string containing a human-readable representation of the
    given time
    """
    return time.strftime("%b %d, %Y; %I:%M %p")


def detailed_timestamp(time=None):
    """
    Generate a detailed timestamp.
    (e.g. `"2013-06-05:14:58:21.024717"`)

    **Parameters:**

    * `time`: an instance of `datetime.datetime`

    **Returns:** a string containing a representation of the given time
    """
    return time.strftime("%Y-%m-%d:%H:%M:%S.%f")


def from_detailed_timestamp(time):
    """
    Generate an instance of datetime from a detailed timestamp.

    **Parameters:**

    * `time`: a string of the same form as the output from
        `catsoop.time.detailed_timestamp`

    **Returns:** a `datetime.datetime` instance representing the given time
    """
    return datetime.strptime(time, "%Y-%m-%d:%H:%M:%S.%f")
