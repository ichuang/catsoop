# This file is part of CAT-SOOP
# Copyright (c) 2011-2025 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

* 8 bytes representing the length of the entry
* a binary blob (pickled Python object, potentially encrypted and/or
    compressed)
* the 8-byte length repeated

This module provides functions for interacting with and modifying those logs.
In particular, it provides ways to retrieve the Python objects in a log, or to
add new Python objects to a log.
"""

import os
import ast
import sys
import lzma
import time
import uuid
import base64
import pickle
import struct
import hashlib
import importlib
import contextlib

from datetime import datetime, timedelta

_nodoc = {
    "passthrough",
    "FileLock",
    "SEP_CHARS",
    "get_separator",
    "good_separator",
    "modify_most_recent",
    "NoneType",
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


from . import util
from . import base_context
from . import time as cstime
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


def log_lock(path):
    lock_h = hashlib.sha3_512(pickle.dumps(path, 5)).hexdigest()
    log_lock_location = getattr(
        base_context, "cs_log_lock_location", None
    ) or os.path.join(base_context.cs_data_root, "_locks")
    lock_loc = os.path.join(
        log_lock_location, lock_h[0], lock_h[1], lock_h[2], f"{lock_h}.lock"
    )
    os.makedirs(os.path.dirname(lock_loc), exist_ok=True)
    return FileLock(lock_loc)


def compress_encrypt(x):
    if COMPRESS:
        x = lzma.compress(x)
    if ENCRYPT_KEY is not None:
        x = util.simple_encrypt(ENCRYPT_KEY, x)
    return x


def prep(x):
    """
    Helper function to serialize a Python object.
    """
    return compress_encrypt(pickle.dumps(x, 5))


def decompress_decrypt(x):
    if ENCRYPT_KEY is not None:
        x = util.simple_decrypt(ENCRYPT_KEY, x)
    if COMPRESS:
        x = lzma.decompress(x)
    return x


def unprep(x):
    """
    Helper function to deserialize a Python object.
    """
    return pickle.loads(decompress_decrypt(x))


def _e(x, person):
    p = hashlib.sha512(ENCRYPT_KEY + person.encode("utf-8")).digest()[:9]
    return (
        base64.urlsafe_b64encode(
            hashlib.blake2b(x.encode("utf-8"), person=b"catsoop%s" % p).digest()
        )
        .decode("utf-8")
        .rstrip("==")
    )


def _transform_log_info(db_name, path, logname):
    if ENCRYPT_KEY is not None:
        seed = path[0] if path else db_name
        path = [_e(p, seed + repr(path[:ix])) for ix, p in enumerate(path)]
        db_name = _e(db_name, seed + db_name)
        logname = _e(logname, seed + repr(path))
    return db_name, path, logname


def get_log_filename(db_name, path, logname):
    """
    Helper function, returns the filename where a given log is stored on disk.

    **Parameters:**

    * `db_name`: the name of the database to look in
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    """
    db_name, path, logname = _transform_log_info(db_name, path, logname)
    if path:
        course = path[0]
        return os.path.join(
            base_context.cs_data_root,
            "_logs",
            "_courses",
            course,
            db_name,
            *(path[1:]),
            f"{logname}.log",
        )
    else:
        return os.path.join(
            base_context.cs_data_root, "_logs", db_name, *path, f"{logname}.log"
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


def delete_log(db_name, path, logname, lock=True):
    """
    Deletes an entire log.

    **Parameters:**

    * `db_name`: the name of the database to overwrite
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this update
    """
    # get an exclusive lock on this file before making changes
    fname = get_log_filename(db_name, path, logname)
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        try:
            os.unlink(fname)
        except FileNotFoundError:
            pass


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
    # get an exclusive lock on this file before reading it
    cm = log_lock([db_name] + path + [logname]) if lock else passthrough()
    with cm:
        try:
            with open(fname, "rb") as f:
                f.seek(-8, os.SEEK_END)
                length = struct.unpack("<Q", f.read(8))[0]
                f.seek(-length - 8, os.SEEK_CUR)
                return unprep(f.read(length))
        except FileNotFoundError:
            return default


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


def clear_old_logs(db_name, path, expire):
    """
    Clear logs older than the given value.  Primarily used for session handling
    """
    directory = os.path.dirname(get_log_filename(db_name, path, "test"))
    try:
        logs = os.listdir(directory)
    except:
        return
    for log in logs:
        fullname = os.path.join(directory, log)
        try:
            if os.stat(fullname).st_mtime < time.time() - expire:
                os.unlink(fullname)
        except:
            pass


def store_upload(username, data, filename):
    content_hash = hashlib.blake2b(data).hexdigest()
    data = compress_encrypt(data)
    info = {
        "filename": filename,
        "username": username,
        "time": cstime.detailed_timestamp(cstime.now()),
        "hash": content_hash,
    }
    info_hash = hashlib.blake2b(pickle.dumps(info)).hexdigest()
    info = prep(info)

    for id_, name, content in (
        (info_hash, "info", info),
        (content_hash, "data", data),
    ):
        dir_ = os.path.join(
            base_context.cs_data_root, "_logs", "_uploads", name, id_[0], id_[1]
        )
        os.makedirs(dir_, exist_ok=True)
        fname = os.path.join(dir_, id_)
        if not os.path.isfile(fname):
            with open(fname, "wb") as f:
                f.write(content)

    return info_hash


def retrieve_upload(id_):
    info_file = os.path.join(
        base_context.cs_data_root, "_logs", "_uploads", "info", id_[0], id_[1], id_
    )
    try:
        with open(info_file, "rb") as f:
            info = unprep(f.read())
        content_hash = info["hash"]
        data_file = os.path.join(
            base_context.cs_data_root,
            "_logs",
            "_uploads",
            "data",
            content_hash[0],
            content_hash[1],
            content_hash,
        )
        with open(data_file, "rb") as f:
            data = decompress_decrypt(f.read())
        return info, data
    except FileNotFoundError:
        return None
