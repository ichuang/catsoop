"""Compatibility code for using Cheroot with various versions of Python."""

import re

def ntob(n, encoding='ISO-8859-1'):
    """Return the native string as bytes in the given encoding."""
    assert_native(n)
    # In Python 3, the native string type is unicode
    return n.encode(encoding)

def ntou(n, encoding='ISO-8859-1'):
    """Return the native string as unicode with the given encoding."""
    assert_native(n)
    # In Python 3, the native string type is unicode
    return n

def bton(b, encoding='ISO-8859-1'):
    """Return the byte string as native string in the given encoding."""
    return b.decode(encoding)

def assert_native(n):
    """Check whether the input is of nativ ``str`` type.

    Raises:
        TypeError: in case of failed check
    """
    if not isinstance(n, str):
        raise TypeError('n must be a native str (got %s)' % type(n).__name__)
