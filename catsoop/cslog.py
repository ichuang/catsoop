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
Logging mechanisms in catsoopdb

From a high-level perspective, CAT-SOOP's logs are sequences of Python objects.

A log is identified by a `db_name` (typically a username), a `path` (a list of
strings starting with a course name), and a `logname` (a string).

On disk, each log is a file containing one or more entries, where each entry
consists of:

* 8 bits representing the length of the entry
* a binary blob (pickled Python object, potentially encrypted and/or
    compressed)
* the 8-bit length repeated

This module provides functions for interacting with and modifying those logs.
In particular, it provides ways to retrieve the Python objects in a log, or to
add new Python objects to a log.
"""

import os
import ast
import sys
import lzma
import base64
import pickle
import struct
import hashlib
import importlib
import contextlib

from collections import OrderedDict
from datetime import datetime, timedelta

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from .fernet import RawFernet

_nodoc = {
    "passthrough",
    "FileLock",
    "SEP_CHARS",
    "get_separator",
    "good_separator",
    "modify_most_recent",
    "NoneType",
    "OrderedDict",
    "datetime",
    "timedelta",
    "COMPRESS",
    "Cipher",
    "ENCRYPT_KEY",
    "ENCRYPT_PASS",
    "RawFernet",
    "compress_encrypt",
    "decompress_decrypt",
    "default_backend",
    "log_lock",
    "prep",
    "sep",
    "unprep",
}


@contextlib.contextmanager
def passthrough():
    yield


from . import base_context
from filelock import FileLock

importlib.reload(base_context)

COMPRESS = base_context.cs_log_compression

ENCRYPT_KEY = None
ENCRYPT_PASS = os.environ.get("CATSOOP_PASSPHRASE", None)
if ENCRYPT_PASS is not None:
    with open(
        os.path.join(os.path.dirname(os.environ["CATSOOP_CONFIG"]), "encryption_salt"),
        "rb",
    ) as f:
        SALT = f.read()
    ENCRYPT_KEY = hashlib.pbkdf2_hmac(
        "sha256", ENCRYPT_PASS.encode("utf8"), SALT, 100000, dklen=32
    )
    XTS_KEY = hashlib.pbkdf2_hmac("sha256", ENCRYPT_PASS.encode("utf8"), SALT, 100000)
    FERNET = RawFernet(ENCRYPT_KEY)


def log_lock(path):
    lock_loc = os.path.join(base_context.cs_data_root, "_locks", *path)
    os.makedirs(os.path.dirname(lock_loc), exist_ok=True)
    return FileLock(lock_loc)


def compress_encrypt(x):
    if COMPRESS:
        x = lzma.compress(x)
    if ENCRYPT_KEY is not None:
        x = FERNET.encrypt(x)
    return x


def prep(x):
    """
    Helper function to serialize a Python object.
    """
    return compress_encrypt(pickle.dumps(x, -1))


def decompress_decrypt(x):
    if ENCRYPT_KEY is not None:
        x = FERNET.decrypt(x)
    if COMPRESS:
        x = lzma.decompress(x)
    return x


def unprep(x):
    """
    Helper function to deserialize a Python object.
    """
    return pickle.loads(decompress_decrypt(x))


def _e(x, seed):  # not sure seed is the right term here...
    x = x.encode("utf8") + bytes([0] * (16 - len(x)))
    b = hashlib.sha512(seed.encode("utf8") + ENCRYPT_KEY + SALT).digest()[-16:]
    c = Cipher(algorithms.AES(XTS_KEY), modes.XTS(b), backend=default_backend())
    e = c.encryptor()
    return base64.urlsafe_b64encode(e.update(x) + e.finalize()).decode("utf8")


def _d(x, seed):  # not sure seed is the right term here...
    x = base64.urlsafe_b64decode(x)
    b = hashlib.sha512(seed.encode("utf8") + ENCRYPT_KEY + SALT).digest()[-16:]
    c = Cipher(algorithms.AES(XTS_KEY), modes.XTS(b), backend=default_backend())
    d = c.decryptor()
    return (d.update(x) + d.finalize()).rstrip(b"\x00").decode("utf8")


def get_log_filename(db_name, path, logname):
    """
    Helper function, returns the filename where a given log is stored on disk.

    **Parameters:**

    * `db_name`: the name of the database to look in
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    """
    if ENCRYPT_KEY is not None:
        seed = path[0] if path else db_name
        path = [_e(i, seed + i) for i in path]
        db_name = _e(db_name, seed + db_name)
        logname = _e(logname, seed + repr(path))
    if path:
        course = path[0]
        return os.path.join(
            base_context.cs_data_root,
            "_logs",
            "_courses",
            course,
            db_name,
            *(path[1:]),
            "%s.log" % logname
        )
    else:
        return os.path.join(
            base_context.cs_data_root, "_logs", db_name, *path, "%s.log" % logname
        )


def _modify_log(fname, new, mode):
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    entry = prep(new)
    length = struct.pack("<Q", len(entry))
    with open(fname, mode) as f:
        f.write(length)
        f.write(entry)
        f.write(length)


def update_log(db_name, path, logname, new, lock=True):
    """
    Adds a new entry to the end of the specified log.

    **Parameters:**

    * `db_name`: the name of the database to update
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    * `new`: the Python object that should be added to the end of the log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this update
    """
    fname = get_log_filename(db_name, path, logname)
    # get an exclusive lock on this file before making changes
    # look up the separator and the data
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        _modify_log(fname, new, "ab")


def overwrite_log(db_name, path, logname, new, lock=True):
    """
    Overwrites the entire log with a new log with a single (given) entry.

    **Parameters:**

    * `db_name`: the name of the database to overwrite
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    * `new`: the Python object that should be contained in the new log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this update
    """
    # get an exclusive lock on this file before making changes
    fname = get_log_filename(db_name, path, logname)
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        _modify_log(fname, new, "wb")


def _read_log(db_name, path, logname, lock=True):
    fname = get_log_filename(db_name, path, logname)
    # get an exclusive lock on this file before reading it
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        try:
            with open(fname, "rb") as f:
                while True:
                    try:
                        length = struct.unpack("<Q", f.read(8))[0]
                        yield unprep(f.read(length))
                    except EOFError:
                        break
                    f.seek(8, os.SEEK_CUR)
                return
        except:
            return


def read_log(db_name, path, logname, lock=True):
    """
    Reads all entries of a log.

    **Parameters:**

    * `db_name`: the name of the database to read
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this read

    **Returns:** a list containing the Python objects in the log
    """
    return list(_read_log(db_name, path, logname, lock))


def most_recent(db_name, path, logname, default=None, lock=True):
    """
    Ignoring most of the log, grab the last entry.

    This code works by reading backward through the log until the separator is
    found, treating the piece of the file after the last separator as a log
    entry, and using `unprep` to return the associated Python object.

    **Parameters:**

    * `db_name`: the name of the database to read
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log

    **Optional Parameters:**

    * `default` (default `None`): the value to be returned if the log contains
        no entries or does not exist
    * `lock` (default `True`): whether the database should be locked during
        this read

    **Returns:** a single Python object representing the most recent entry in
    the log.
    """
    fname = get_log_filename(db_name, path, logname)
    if not os.path.isfile(fname):
        return default
    # get an exclusive lock on this file before reading it
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        with open(fname, "rb") as f:
            f.seek(-8, os.SEEK_END)
            length = struct.unpack("<Q", f.read(8))[0]
            f.seek(-length - 8, os.SEEK_CUR)
            return unprep(f.read(length))


def modify_most_recent(
    db_name,
    path,
    logname,
    default=None,
    transform_func=lambda x: x,
    method="update",
    lock=True,
):
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        old_val = most_recent(db_name, path, logname, default, lock=False)
        new_val = transform_func(old_val)
        if method == "update":
            updater = update_log
        else:
            updater = overwrite_log
        updater(db_name, path, logname, new_val, lock=False)
    return new_val
