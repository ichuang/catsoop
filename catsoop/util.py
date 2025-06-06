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
Extra utilities that don't have a home anywhere else
"""

import os
import ast
import base64
import pickle
import hashlib

import urllib.parse

from datetime import datetime, timedelta
from nacl.bindings import (
    crypto_secretbox,
    crypto_secretbox_open,
)


from . import base_context

_nodoc = {
    "crypto_secretbox",
    "crypto_secretbox_open",
    "datetime",
    "timedelta",
}


def simple_encrypt(key, msg):
    """
    Encrypt the given plaintext string with the given key using `libsodium`'s
    `secretbox` construct

    **Parameters:**

    * `key` (`bytes`): a length-32 bytestring containing the encryption key
    * `msg` (`bytes`): a bytestring of arbitrary length, containing the message
        to be encrypted

    **Returns:** a bytestring containing the resulting ciphertext, with the
    24-byte nonce preprended
    """
    nonce = os.urandom(24)
    cipher = crypto_secretbox(msg, nonce, key)
    return b"%s%s" % (nonce, cipher)


def simple_decrypt(key, cipher):
    """
    Decrypt the given ciphertext with the given key, using `libsodium`'s
    `secretbox` construct

    **Parameters:**

    * `key` (`bytes`): a length-32 bytestring containing the encryption key
    * `cipher` (`bytes`): a bytestring containing the ciphertext (with 24-byte
        nonce prepended), of the form returned by `simple_encrypt`

    **Returns:** a bytestring containing the plaintext result of decrypting the
    given input
    """
    nonce = cipher[:24]
    return crypto_secretbox_open(cipher[24:], nonce, key)


def catsoop_loc_hash():
    """
    Function to generate a hash representative of this catsoop instance (by
    hashing `cs_url_root`).  Used to generate names for the session ID, to be
    used when setting cookies.
    """
    return hashlib.md5(base_context.cs_url_root.encode("utf-8")).hexdigest()


_literal_eval_funcs = {
    "OrderedDict": dict,
    "frozenset": frozenset,
    "set": set,
    "dict": dict,
    "list": list,
    "tuple": tuple,
    "datetime": datetime,
    "timedelta": timedelta,
}


def literal_eval(node_or_string):
    """
    Helper function to read a log entry and return the associated Python
    object.  Forked from Python 3.5's ast.literal_eval function:

    Safely evaluate an expression node or a string containing a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings, bytes, numbers, tuples, lists, dicts,
    sets, booleans, and None.
    """
    if isinstance(node_or_string, str):
        node_or_string = ast.parse(node_or_string, mode="eval")
    if isinstance(node_or_string, ast.Expression):
        node_or_string = node_or_string.body

    def _convert(node):
        if isinstance(node, (ast.Str, ast.Bytes)):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Tuple):
            return tuple(map(_convert, node.elts))
        elif isinstance(node, ast.List):
            return list(map(_convert, node.elts))
        elif isinstance(node, ast.Set):
            return set(map(_convert, node.elts))
        elif isinstance(node, ast.Dict):
            return dict(
                (_convert(k), _convert(v)) for k, v in zip(node.keys, node.values)
            )
        elif isinstance(node, ast.NameConstant):
            return node.value
        elif (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.UAdd, ast.USub))
            and isinstance(node.operand, (ast.Num, ast.UnaryOp, ast.BinOp))
        ):
            operand = _convert(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            else:
                return -operand
        elif (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, (ast.Add, ast.Sub))
            and isinstance(node.right, (ast.Num, ast.UnaryOp, ast.BinOp))
            and isinstance(node.left, (ast.Num, ast.UnaryOp, ast.BinOp))
        ):
            left = _convert(node.left)
            right = _convert(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            else:
                return left - right
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _literal_eval_funcs
        ):
            return _literal_eval_funcs[node.func.id](*(_convert(i) for i in node.args))
        raise ValueError("malformed node or string: " + repr(node))

    return _convert(node_or_string)
