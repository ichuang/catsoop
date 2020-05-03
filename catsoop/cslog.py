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
import time
import base64
import pickle
import struct
import hashlib
import importlib
import contextlib
from . import debug_log

from collections import OrderedDict
from datetime import datetime, timedelta

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from .fernet import RawFernet

LOGGER = debug_log.LOGGER
#LOGGER.setLevel(1)

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
    lock_loc = os.path.join(base_context.cs_data_root, "_locks", *path) + ".lock"
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

#-----------------------------------------------------------------------------

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



#-----------------------------------------------------------------------------

class CatsoopLogsWithFilesystem:
    
    def __init__(self):
        return

    @staticmethod
    def _modify_log(fname, new, mode):
        '''
        Update log file
        '''
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        entry = prep(new)
        length = struct.pack("<Q", len(entry))
        with open(fname, mode) as f:
            f.write(length)
            f.write(entry)
            f.write(length)

    @staticmethod
    def read_log_file(fn, default=None):
        '''
        Read log file with a specific filename-path
        Used by session.py
        '''
        dname = os.path.dirname(fn)
        sid = os.path.basename(fn)
        os.makedirs(dname, exist_ok=True)
        lockname = os.path.basename(dname)
        with log_lock([lockname, sid]):
            try:
                with open(fn, "rb") as f:
                    out = unprep(f.read())
            except:
                out = default or {}  # default to returning empty session
            return out
    
    @staticmethod
    def write_log_file(fn, data):
        '''
        Write provided data to specified filename-path
        '''
        dname = os.path.dirname(fn)
        sid = os.path.basename(fn)
        os.makedirs(dname, exist_ok=True)
        lockname = os.path.basename(dname)
        with log_lock([lockname, sid]):
            with open(fn, "wb") as f:
                f.write(prep(data))

    @staticmethod
    def clear_old_log_files(dname, expire):
        '''
        Delete log files older than specified now - expire
        '''
        now = time.time()
        os.makedirs(dname, exist_ok=True)
        for i in os.listdir(dname):
            fullname = os.path.join(dname, i)
            try:
                if os.stat(fullname).st_mtime < now - expire:
                    os.unlink(fullname)
            except:
                pass

    @staticmethod
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
    
    @staticmethod
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
    
    
    @staticmethod
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
    
    def init_db(self):
        '''
        Initializae database connection
        '''
        return

#-----------------------------------------------------------------------------

class CatsoopLogsWithFirestore:
    '''
    Logs based on google firestore cloud database
    '''
    COLLECTION = "LOGS"

    def __init__(self):
        self.init_db()
        return

    def fname_to_doc(self, fn):
        '''
        Return collection name and document name, for a given filename-path
        '''
        if fn.startswith(base_context.cs_data_root):	# remove cs_data_root if used
            fn = fn[len(base_context.cs_data_root):]
        dname = os.path.dirname(fn)
        fnb = os.path.basename(fn)
        dname = dname.replace("/", "__")
        return dname, fnb

    def read_log_file(self, fn, default=None):
        '''
        Read log file, as specified by filename-path
        '''
        (dname, fnb) = self.fname_to_doc(fn)
        # LOGGER.debug("[catsoop.cslog] reading collection %s, docid %sS"  % (dname, fnb))
        doc_ref = self.db.collection(dname).document(fnb)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict().get('data')
            return unprep(data)
        return default or {}

    def write_log_file(self, fn, data):
        '''
        Write provided data to log file, as specified by filename-path
        '''
        (dname, fnb) = self.fname_to_doc(fn)
        doc_ref = self.db.collection(dname).document(fnb)
        doc = {'data': prep(data),
               'mtime': time.time(),
        }
        doc_ref.set(doc)

    def clear_old_log_files(self, dname, expire):
        '''
        Remove log files in specified directory / collection, if older than specified expiration delta (from now)
        '''
        fn = os.path.join(dname, "none")
        (dname, fnb) = self.fname_to_doc(fn)
        now = time.time()
        ref = self.db.collection(dname).where("mtime", "<", now - expire)
        for doc in ref.stream():
            LOGGER.warning("[catsoop.cslog] deleting %s from %s" % (doc.id, dname))
            doc.reference.delete()

    def _modify_log(self, fname, new, mode):
        '''
        Update log file on cloud.  Use CLOUD_COLLECTION as the collection name,
        an fname as the document name.  Each document has to be a dict, so we make
        it {'data': [...]}, where the actual data is stored in the data list.
    
        If mode starts with 'a' then append <new> to the data list.
        Else set data to be  [<new>]
        '''
        fname = fname.replace("/", '__')
        new = prep(new)
        
        if mode[0]=='a':
            transaction = self.db.transaction()
            ref = self.db.collection(self.COLLECTION).document(fname)
    
            @firestore.transactional
            def update_in_transaction(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                if not snapshot.get("data"):
                    transaction.set(ref, { 'data': [new] })
                else:
                    transaction.update(ref, { 'data': (snapshot.get('data') or []) + [new] })	# append to existing data
                
            update_in_transaction(transaction, ref)
        else:
            ref = self.db.collection(self.COLLECTION).document(fname)
            ref.set({'data': [new]})
            
    def _read_log(self, db_name, path, logname, lock=True, most_recent=False):
        fname = get_log_filename(db_name, path, logname)
        fname = fname.replace("/", '__')
        ref = self.db.collection(self.COLLECTION).document(fname)
        doc = ref.get()
        if doc.exists:
            raw_data = doc.to_dict().get("data")
            if most_recent:
                return unprep(raw_data[-1])
            data = [ unprep(x) for x in raw_data ]
        else:
            data = []
        return data
    
    def most_recent(self, db_name, path, logname, default=None, lock=True):
        data = self._read_log(db_name, path, logname, most_recent=True)
        if not data:
            return default
        return data
    
    def init_db(self):
        '''
        Initializae database connection
        '''
        self.db = firestore.Client()		# document database

    def modify_most_recent(self,
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

#-----------------------------------------------------------------------------

class CatsoopLogsWithMongoDB:
    '''
    Logs based on mongo DB
    '''
    COLLECTION = "LOGS"

    def __init__(self):
        self.init_db()
        return

    def fname_to_doc(self, fn):
        '''
        Return collection name and document name, for a given filename-path
        '''
        if fn.endswith(".log"):
            fn = fn[:-4]
        if fn.startswith(base_context.cs_data_root):	# remove cs_data_root if used
            fn = fn[len(base_context.cs_data_root):]
        dname = os.path.dirname(fn)
        fnb = os.path.basename(fn)
        dname = dname.replace("/", "__")
        if dname.startswith("___"):
            dname = dname[3:]
        col = "%s__%s" % (dname, fnb)
        return dname, fnb, col

    def read_log_file(self, fn, default=None):
        '''
        Read log file, as specified by filename-path
        '''
        (dname, fnb, col) = self.fname_to_doc(fn)
        # LOGGER.debug("[catsoop.cslog] reading collection %s, docid %sS"  % (dname, fnb))
        doc = self.db[dname].find_one({"_id": fnb})
        if doc:
            data = doc.get('data')
            return unprep(data)
        return default or {}

    def write_log_file(self, fn, data):
        '''
        Write provided data to log file, as specified by filename-path
        '''
        (dname, fnb, col) = self.fname_to_doc(fn)
        doc = {'data': prep(data),
               'mtime': time.time(),
               "_id": fnb,
        }
        self.db[dname].replace_one({"_id": fnb}, doc, upsert=True)

    def clear_old_log_files(self, dname, expire):
        '''
        Remove log files in specified directory / collection, if older than specified expiration delta (from now)
        '''
        fn = os.path.join(dname, "none")
        (dname, fnb, col) = self.fname_to_doc(fn)
        now = time.time()
        ref = self.db[dname].find({"mtime": {"$lt": now - expire}})
        for doc in ref:
            LOGGER.warning("[catsoop.cslog] deleting %s from %s" % (doc['_id'], dname))
            self.db[dname].delete_one({"_id": doc['_id']})


    def _modify_log(self, fname, new, mode):
        '''
        Update log file on cloud.  Each document has to be a dict, so we make
        it {'data': [...], 'fn': fnb}, where the actual data.  One document is stored for each
        log instance.  Appending just adds a new document.  
    
        If mode[0] is not 'a' then replace any existing document with the new data,
        or create new document with new data, if none existing.
        '''
        (dname, fnb, col) = self.fname_to_doc(fname)
        new = prep(new)
        
        newdoc = {'fn': fnb,
                  'data': new,
                  'time': time.time(),
        }

        if mode[0]=='a':
            ref = self.db[dname].insert_one(newdoc)	# mongodb: just make new doc
        else:
            doc = self.db[dname].find_one_and_update({'fn': fnb},
                                                     {"$set": newdoc},
                                                     sort = [('$natural', -1)],
                                                     upsert=True,
            )
            
    def _read_log(self, db_name, path, logname, lock=True, most_recent=False, include_id=False):
        fname = get_log_filename(db_name, path, logname)
        (dname, fnb, col) = self.fname_to_doc(fname)

        if most_recent:
            # return only data from most recent document
            doc = self.db[dname].find_one({'fn': fnb}, sort=[('$natural', -1)])
            if doc:
                docid = doc.get("_id")
                data = unprep(doc.get('data'))
            else:
                docid = None
                data = None
            if include_id:
                return data, docid
            return data

        # return list of data from all documents
        data = []
        for doc in self.db[dname].find({'fn': fnb}):
            data.append( unprep(doc.get("data")) )
        return data
    
    def most_recent(self, db_name, path, logname, default=None, lock=True):
        data = self._read_log(db_name, path, logname, most_recent=True)
        if not data:
            return default
        return data
    
    def init_db(self):
        '''
        Initializae database connection
        '''
        mongourl = os.environ.get("MONGODB", None)
        self.client = pymongo.MongoClient(mongourl)
        self.db = self.client.catsoop

    def modify_most_recent(self,
        db_name,
        path,
        logname,
        default=None,
        transform_func=lambda x: x,
        method="update",
        lock=True,
       ):
        fname = get_log_filename(db_name, path, logname)
        (dname, fnb, col) = self.fname_to_doc(fname)
        
        update_data = {}
        update_data = transform_func(update_data)
        def make_update_op(data):
            '''
            Return list of (key1.key2.key3, value) for all fields set in the dict data, e.g.
            { a: { b: 3 }, c: 2} should return [ ("a.b", 3), ("c", 2) ]

            This provides an atomic update action for mongodb.
            '''
            op = []
            for k, v in data.items():
                if type(v)==dict:
                    op += [ ("%s.%s" % (k, vk), vv) for (vk, vv) in make_update_op(v) ]
                op.append( (k, v) )
            return op

        ops = { "data.%s" % k: v for (k,v) in make_update_op(update_data) }
        update_op = {"$set": ops}

        old_val, docid = self._read_log(db_name, path, logname, most_recent=True, include_id=True)
        old_val = old_val or {}
        new_val = transform_func(old_val)

        if method == "update" and docid:
            dfilter = {'_id': doc['_id']}
            ref = self.db[dname].update_one(dfilter, update_op)
            LOGGER.debug("[catsoop.cslog.modify_most_recent] updated %s with %s" % (dfilter, update_op))
        else:
            overwrite_log(db_name, path, logname, new_val, lock=False)
            LOGGER.debug("[catsoop.cslog.modify_most_recent] overwrote log collection %s with new_val=%s" % (dname, new_val))

        return new_val

#-----------------------------------------------------------------------------

procs = ["_modify_log", "_read_log", "most_recent", "modify_most_recent", "init_db",
         "read_log_file", "write_log_file", "clear_old_log_files"]

USE_CLOUD_DB = os.environ.get("USE_CLOUD_DB")
if USE_CLOUD_DB=="mongodb":
    import pymongo
    LOGS = CatsoopLogsWithMongoDB()
    
elif USE_CLOUD_DB:
    from google.cloud import firestore
    LOGS = CatsoopLogsWithFirestore()

else:
    LOGS = CatsoopLogsWithFilesystem()

for pname in procs:
    exec("%s = LOGS.%s" % (pname, pname))
