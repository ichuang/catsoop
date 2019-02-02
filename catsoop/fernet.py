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

# This file is a modified version of the file available at:
# https://github.com/pyca/cryptography/blob/master/src/cryptography/fernet.py

# This original file, part of the cryptography Python3 package
# (https://cryptography.io/en/latest/) was dual licensed under the terms of the
# Apache License, Version 2.0, and the BSD License. See
# https://github.com/pyca/cryptography/blob/master/LICENSE for complete
# details.
"""
Fernet-style encryption forked from the
[`cryptography`](https://cryptography.io/en/latest/) package.  Implements
Fernet encryption, but without the bade64-encoding step (produces raw binary
data).
"""

import binascii
import os
import struct
import time

import six

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hmac import HMAC

_nodoc = {
    "InvalidSignature",
    "default_backend",
    "hashes",
    "padding",
    "Cipher",
    "algorithms",
    "modes",
    "HMAC",
    "InvalidToken",
}


class InvalidToken(Exception):
    pass


_MAX_CLOCK_SKEW = 60


class RawFernet(object):
    """
    Class (forked from the `Fernet` class in the `cryptography` package) that
    implements a raw binary form of Fernet encryption.
    """

    def __init__(self, key, backend=None):
        if backend is None:
            backend = default_backend()

        if len(key) != 32:
            raise ValueError("Fernet key must be 32 bytes.")

        self._signing_key = key[:16]
        self._encryption_key = key[16:]
        self._backend = backend

    @classmethod
    def generate_key(cls):
        return os.urandom(32)

    def encrypt(self, data):
        current_time = int(time.time())
        iv = os.urandom(16)
        return self._encrypt_from_parts(data, current_time, iv)

    def _encrypt_from_parts(self, data, current_time, iv):
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes.")

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        encryptor = Cipher(
            algorithms.AES(self._encryption_key), modes.CBC(iv), self._backend
        ).encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        basic_parts = b"\x80" + struct.pack(">Q", current_time) + iv + ciphertext

        h = HMAC(self._signing_key, hashes.SHA256(), backend=self._backend)
        h.update(basic_parts)
        hmac = h.finalize()
        return basic_parts + hmac

    def decrypt(self, token, ttl=None):
        timestamp, data = RawFernet._get_unverified_token_data(token)
        return self._decrypt_data(data, timestamp, ttl)

    def extract_timestamp(self, token):
        timestamp, data = RawFernet._get_unverified_token_data(token)
        # Verify the token was not tampered with.
        self._verify_signature(data)
        return timestamp

    @staticmethod
    def _get_unverified_token_data(token):
        if not isinstance(token, bytes):
            raise TypeError("token must be bytes.")

        try:
            data = token
        except (TypeError, binascii.Error):
            raise InvalidToken

        if not data or six.indexbytes(data, 0) != 0x80:
            raise InvalidToken

        try:
            timestamp, = struct.unpack(">Q", data[1:9])
        except struct.error:
            raise InvalidToken
        return timestamp, data

    def _verify_signature(self, data):
        h = HMAC(self._signing_key, hashes.SHA256(), backend=self._backend)
        h.update(data[:-32])
        try:
            h.verify(data[-32:])
        except InvalidSignature:
            raise InvalidToken

    def _decrypt_data(self, data, timestamp, ttl):
        current_time = int(time.time())
        if ttl is not None:
            if timestamp + ttl < current_time:
                raise InvalidToken

            if current_time + _MAX_CLOCK_SKEW < timestamp:
                raise InvalidToken

        self._verify_signature(data)

        iv = data[9:25]
        ciphertext = data[25:-32]
        decryptor = Cipher(
            algorithms.AES(self._encryption_key), modes.CBC(iv), self._backend
        ).decryptor()
        plaintext_padded = decryptor.update(ciphertext)
        try:
            plaintext_padded += decryptor.finalize()
        except ValueError:
            raise InvalidToken
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

        unpadded = unpadder.update(plaintext_padded)
        try:
            unpadded += unpadder.finalize()
        except ValueError:
            raise InvalidToken
        return unpadded
