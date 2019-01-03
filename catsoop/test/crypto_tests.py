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
Tests for CAT-SOOP's crypto
"""

import os
import cgi
import time
import base64
import random
import string
import logging
import calendar
import unittest

from datetime import datetime
from contextlib import contextmanager

from catsoop.fernet import RawFernet, InvalidToken
from cryptography.fernet import Fernet

logging.getLogger("cs").setLevel(1)
LOGGER = logging.getLogger("cs")

_random = random.Random()

# -----------------------------------------------------------------------------


@contextmanager
def spoof_time(current_time=None):
    if current_time == None:
        current_time = random.uniform(0, 4102444800)

    old_time_func = time.time
    time.time = lambda: current_time
    yield current_time
    time.time = old_time_func


@contextmanager
def spoof_urandom(pattern=None):
    if pattern == None:
        pattern = os.urandom(1000)

    def _spoofed(x):
        out = bytearray(pattern)
        while len(out) < x:
            out.extend(pattern)
        return bytes(out[:x])

    old_urandom = os.urandom
    os.urandom = _spoofed
    yield pattern
    os.urandom = old_urandom


class Test_Fernet(unittest.TestCase):
    """
    Test for the RawFernet class
    """

    test_key = (
        b"s\x0f\xf4\xc7\xaf=F\x92>\x8e\xd4Q\xee\x81<\x87\xf7\x90\xb0"
        b"\xa2&\xbc\x96\xa9-\xe4\x9b^\x9c\x05\xe1\xee"
    )
    test_tok = (
        b"\x80\x00\x00\x00\x00\x1d\xc0\x9e\xb0\x00\x01\x02\x03\x04\x05"
        b"\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f-6\xd5\xcaFUb\x99\xfd\xe10"
        b"\x08c8\x04\xb2\xc5\xff\x90\x95\xf5\xd3\x8f\x9a\xb8nUC\xe0&"
        b"\x86\xf0;>\xc9q\xb9\xabG\xae#VjT\xe0\x8c*\x0c"
    )
    test_msg = b"hello"
    test_ctime = 499162800
    test_iv = bytes(range(16))
    test_ttl = 60

    def test_generate(self):
        """
        Test that the proper token is generated in a specific case
        """
        r = RawFernet(self.test_key)
        tok = r._encrypt_from_parts(self.test_msg, self.test_ctime, self.test_iv)
        self.assertEqual(tok, self.test_tok)
        with spoof_time(self.test_ctime):
            with spoof_urandom(self.test_iv):
                self.assertEqual(r.encrypt(self.test_msg), self.test_tok)

    def test_verify(self):
        """
        Test proper verification of a token
        """
        with spoof_time(self.test_ctime):
            r = RawFernet(self.test_key)
            out = r.decrypt(self.test_tok, ttl=self.test_ttl)
            self.assertEqual(out, self.test_msg)

    def test_ttl_handling(self):
        """
        Try a couple of verifications to
        """
        with spoof_time(self.test_ctime + 61):
            # try to decrypt with expire message
            r = RawFernet(self.test_key)
            with self.assertRaises(InvalidToken):
                out = r.decrypt(self.test_tok, ttl=self.test_ttl)

            # now decrypt with no ttl
            out = r.decrypt(self.test_tok)
            self.assertEqual(out, self.test_msg)

    def test_compare_fernet(self):
        """
        A test to compare our binary Fernet implementation against the base
        Fernet implementation from the cryptography library.  50 times, encrypt
        a random message with a random key and make sure our result matches
        that of the regular Fernet implementation.
        """
        chars = (
            string.ascii_lowercase + string.ascii_uppercase + string.digits
        ).encode("utf-8")
        for i in range(50):
            message = bytes(
                random.choice(chars) for i in range(random.randint(100, 10000))
            )
            with spoof_time() as t:
                with spoof_urandom() as u:
                    key = Fernet.generate_key()
                    raw_key = base64.urlsafe_b64decode(key)
                    LOGGER.info("[unit_tests] fernet key=%s" % raw_key)
                    LOGGER.info("[unit_tests] fernet message=%s" % message)
                    LOGGER.info("[unit_tests] fernet time=%s" % t)
                    LOGGER.info("[unit_tests] fernet urandom pattern=%s" % u)
                    secret_base = Fernet(key).encrypt(message)
                    secret_catsoop = RawFernet(raw_key).encrypt(message)
                    self.assertEqual(
                        base64.urlsafe_b64decode(secret_base), secret_catsoop
                    )


if __name__ == "__main__":
    unittest.main()
