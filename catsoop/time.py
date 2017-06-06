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
import time
from datetime import datetime, timedelta, MAXYEAR, MINYEAR

days = ['M', 'T', 'W', 'R', 'F', 'S', 'U']
"List used for mapping weekday numbers to weekday letters"


def realize_time(context, timestring):
    """
    Return an appropriate datetimebased on timestring
    """
    if timestring == 'NEVER':
        return datetime(year=MAXYEAR,
                        month=12,
                        day=31,
                        hour=23,
                        minute=59,
                        second=59)
    elif timestring == 'ALWAYS':
        return datetime(year=1900, month=1, day=1, hour=0, minute=0, second=0)
    elif timestring[0].isdigit():
        # absolute times are specified as strings 'YYYY-MM-DD:HH:MM'
        return datetime.strptime(timestring, '%Y-%m-%d:%H:%M')
    elif timestring[0].isalpha():
        # this is a day and a time
        day, hour, minute = timestring.split(':')
        while len(hour) > 1 and all(i == '0' for i in hour):
            hour = hour[1:]
        while len(minute) > 1 and all(i == '0' for i in minute):
            minute = minute[1:]
        start_date = context['cs_first_monday']
        wknum = context['cs_week_number']
        while len(day) > 1:
            if day[-1] == '+':
                wknum += 1
            elif day[-1] == '-':
                wknum -= 1
            day = day[:-1]
        start = realize_time(context, start_date)
        return start + timedelta(weeks=(wknum - 1),
                                 days=days.index(day),
                                 hours=int(hour),
                                 minutes=int(minute))
    else:
        raise Exception("invalid time style: %s" % timestring)


def unix(dt):
    """
    Generate a UNIX timestamp from an instance of datetime.
    """
    return time.mktime(dt.timetuple())


def now():
    """
    Wraps datetime.now.
    """
    return datetime.now()


def long_timestamp(time):
    """
    Generate a (long) human-readable timestamp.
    (e.g., "Wednesday June 05, 2013; 02:58:21 PM")
    """
    return time.strftime("%A %B %d, %Y; %I:%M:%S %p")


def short_timestamp(time):
    """
    Generate a (short) human-readable timestamp.
    (e.g. "Jun 05, 2013; 02:58 PM")
    """
    return time.strftime("%b %d, %Y; %I:%M %p")


def detailed_timestamp(time=None):
    """
    Generate a detailed timestamp.
    (e.g. "2013-06-05:14:58:21.024717")
    """
    return time.strftime('%Y-%m-%d:%H:%M:%S.%f')


def from_detailed_timestamp(time):
    """
    Generate an instance of datetime from a detailed timestamp.
    """
    return datetime.strptime(time, '%Y-%m-%d:%H:%M:%S.%f')
