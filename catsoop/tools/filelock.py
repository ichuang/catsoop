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
Cross-platform file locking solution, mainly used for logging.

Based on and modified from an implementation by Evan Fosmark:
http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python/
"""

import os
import time
import errno
import tempfile

FILELOCK_DIR = os.path.join(tempfile.gettempdir(), 'catsoop_filelocks')
"""
The directory where file locks will be stored.
"""


class FileLock(object):
    """
    Class representing an exclusive lock on a file.
    """
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR

    def __init__(self, file_name, delay=.05):
        if not os.path.isdir(FILELOCK_DIR):
            os.makedirs(FILELOCK_DIR)
        self.is_locked = False
        self.file_name = file_name
        self.lockfile = os.path.join(
            FILELOCK_DIR, "%s.pyfilelock" %
            (file_name.replace('/', '__S__').replace('\\', '__BS__')))
        self.delay = delay

    def acquire(self):
        if self.is_locked:
            return

        while True:
            try:
                self.fd = os.open(self.lockfile, self.flags)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise Exception("Could not acquire lock for file: %s" % self.file_name)
                time.sleep(self.delay)
        self.is_locked = True

    def release(self):
        if self.is_locked:
            os.close(self.fd)
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        if self.is_locked:
            self.release()

    def __del__(self):
        self.release()
