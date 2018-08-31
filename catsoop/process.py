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
Tools for controlling processes
"""

import os
import time
import ctypes
import signal
import threading
import subprocess
import multiprocessing

_nodoc = {"i"}

# libc lives in different places on different OS
libc = None
"""
The `ctypes.CDLL` object representing libc (which lives in different places on
different platforms).  Used in `catsoop.process.set_pdeathsig`.
"""
for i in ("libc.so.6", "libc.dylib", "cygwin1.dll", "msys-2.0.dll"):
    try:
        libc = ctypes.CDLL(i)
    except:
        pass
    if libc is not None:
        break
assert libc is not None


def set_pdeathsig(sig=signal.SIGTERM):
    """
    Create a function that can be used to set the signal that the calling
    process receives when its parent process dies (not supported on Mac OSX).

    This is used when starting new processes to try to make sure they die if
    CAT-SOOP is killed.

    **Optional Parameters:**

    * `sig` (default `signal.SIGTERM`): the signal to be sent to this process
        when its parent dies

    **Returns:** a function of no arguments that, when called, sets the parent
    process death signal of the calling process to the value given by `sig`.
    On Mac OSX, instead returns a function of no arguments that does nothing
    when called.
    """
    if hasattr(libc, "prctl"):

        def callable():
            return libc.prctl(1, sig)

    else:
        # on mac osx, there is no such thing as prctl.
        def callable():
            pass

    return callable
