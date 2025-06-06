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
Common Test Cases for all CSLog Backends
"""

import os
import math
import time
import pickle
import random
import shutil
import hashlib
import unittest
import multiprocessing

from collections import Counter

from ..test import CATSOOPTest

from .. import cslog
from .. import loader


# -----------------------------------------------------------------------------


class CSLogBackend:
    def test_logging_basic_ops(self):
        user = "testuser"
        path1 = ["test_subject", "some", "page"]
        name = "problemstate"
        self.cslog.update_log(user, path1, name, "HEY")
        self.assertEqual(self.cslog.most_recent(user, path1, name, {}), "HEY")

        self.cslog.update_log(user, path1, name, "HELLO")
        self.assertEqual(self.cslog.read_log(user, path1, name), ["HEY", "HELLO"])

        for i in range(50):
            self.cslog.update_log(user, path1, name, i)

        self.assertEqual(
            self.cslog.read_log(user, path1, name), ["HEY", "HELLO"] + list(range(50))
        )
        self.assertEqual(self.cslog.most_recent(user, path1, name), 49)

        self.cslog.overwrite_log(user, path1, name, 42)
        self.assertEqual(self.cslog.read_log(user, path1, name), [42])

        self.cslog.modify_most_recent(user, path1, name, transform_func=lambda x: x + 9)
        self.assertEqual(self.cslog.read_log(user, path1, name), [42, 51])

        self.cslog.modify_most_recent(user, path1, name, transform_func=lambda x: x + 8)
        self.assertEqual(self.cslog.read_log(user, path1, name), [42, 51, 59])

        self.cslog.modify_most_recent(
            user, path1, name, transform_func=lambda x: x + 7, method="overwrite"
        )
        self.assertEqual(self.cslog.most_recent(user, path1, name), 66)
        self.assertTrue(len(self.cslog.read_log(user, path1, name)) < 4)

        path2 = ["test_subject", "some", "page2"]

        def _transform(x):
            x["cat"] = "miau"
            return x

        self.cslog.modify_most_recent(
            user, path2, name, transform_func=_transform, default={}
        )
        self.assertEqual(self.cslog.most_recent(user, path2, name), {"cat": "miau"})

        self.cslog.delete_log(user, path2, name)
        self.assertEqual(self.cslog.most_recent(user, path2, name, "test"), "test")

        # we'll leave it up to the logging backend whether they delete the
        # _whole_ log if it hasn't been updated since the given time, or
        # whether they only delete the old entries.
        #
        # because of this, this test is lame, as it tests only the (lame)
        # guarantee we should have: that if _all_ entreis in a log are old
        # enough, then the whole log should be deleted (and that logs on a
        # different path are unaffected)
        path3 = ["test_subject", "some", "page3"]
        names = "test1", "test2", "test3"
        users = "user1", "user2"
        for user in users:
            for n in names:
                for i in range(3):
                    self.cslog.update_log(user, path3, n, i)
                self.assertEqual(self.cslog.read_log(user, path3, n), [0, 1, 2])
            for n in names:
                for i in range(3):
                    self.cslog.update_log(user, path2, n, i)
                self.assertEqual(self.cslog.read_log(user, path2, n), [0, 1, 2])

        time.sleep(1)
        self.cslog.clear_old_logs(users[0], path3, 1)
        for n in names:
            self.assertEqual(self.cslog.read_log(users[0], path3, n), [])
            self.assertEqual(self.cslog.read_log(users[1], path3, n), [0, 1, 2])
        for n in names:
            self.assertEqual(self.cslog.read_log(users[0], path2, n), [0, 1, 2])
            self.assertEqual(self.cslog.read_log(users[1], path2, n), [0, 1, 2])

        self.assertTrue(os.path.isdir(self.lock_loc))

    def test_logging_stress_update(self):
        user = "testuser"
        path1 = ["test_subject", "some", "page"]
        name = "problemstate"

        procs = []

        def append_a_bunch():
            for i in range(100):
                self.cslog.update_log(user, path1, name, i)

        for i in range(50):
            p = multiprocessing.Process(target=append_a_bunch, args=())
            procs.append(p)

        for p in procs:
            p.start()

        for p in procs:
            p.join()  # wait for updaters to finish

        entries = self.cslog.read_log(user, path1, name)
        self.assertEqual(len(entries), 5000)
        self.assertEqual(dict(Counter(entries)), {i: 50 for i in range(100)})

    def test_logging_stress_overwrite(self):
        user = "testuser"
        path1 = ["test_subject", "some", "page"]
        name = "problemstate"

        procs = []

        self.cslog.update_log(user, path1, name, 8)

        def overwrite_a_bunch():
            for i in range(100):
                self.cslog.overwrite_log(user, path1, name, 7)

        for i in range(50):
            p = multiprocessing.Process(target=overwrite_a_bunch, args=())
            procs.append(p)

        for p in procs:
            p.start()

        for p in procs:
            p.join()  # wait for updaters to finish

        entries = self.cslog.read_log(user, path1, name)
        self.assertEqual(entries, [7])

    def test_logging_stress_modify(self):
        user = "testuser"
        path1 = ["test_subject", "some", "page"]
        name = "problemstate"

        procs = []

        self.cslog.update_log(user, path1, name, 0)

        def modify_a_bunch():
            for i in range(500):
                self.cslog.modify_most_recent(
                    user,
                    path1,
                    name,
                    transform_func=lambda x: x + 1,
                    method="overwrite",
                )

        for i in range(50):
            p = multiprocessing.Process(target=modify_a_bunch, args=())
            procs.append(p)

        for p in procs:
            p.start()

        for p in procs:
            p.join()  # wait for updaters to finish

        entries = self.cslog.read_log(user, path1, name)
        self.assertEqual(entries, [25000])

    def test_logging_uploads(self):
        content = "hello 🐈".encode("utf-8")
        h = hashlib.sha256(content).hexdigest()
        id_ = cslog.store_upload("testuser", content, "cat.txt")

        ret_info, ret_data = self.cslog.retrieve_upload(id_)
        self.assertEqual(ret_data, content)
        self.assertEqual(self.cslog.retrieve_upload(id_[::-1]), None)


class TestFS(CATSOOPTest, CSLogBackend):
    def setUp(
        self,
    ):
        CATSOOPTest.setUp(self)

        context = {}
        loader.load_global_data(context)
        self.cslog = cslog

        self.log_loc = os.path.join(context["cs_data_root"], "_logs")
        self.lock_loc = os.path.join(context["cs_data_root"], "_locks")
        shutil.rmtree(self.log_loc, ignore_errors=True)
        shutil.rmtree(self.lock_loc, ignore_errors=True)


class TestFSTempDir(CATSOOPTest, CSLogBackend):
    def setUp(
        self,
    ):
        CATSOOPTest.setUp(self)

        context = {}
        loader.load_global_data(context)
        self.cslog = cslog
        self.log_loc = os.path.join(context["cs_data_root"], "_logs")
        self.lock_loc = "/tmp/catsoop_locks"
        context["csm_base_context"].cs_log_lock_location = self.lock_loc

        shutil.rmtree(self.log_loc, ignore_errors=True)
        shutil.rmtree(self.lock_loc, ignore_errors=True)
