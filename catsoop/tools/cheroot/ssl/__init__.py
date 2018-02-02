"""Implementation of the SSL adapter base interface."""

from abc import ABCMeta, abstractmethod


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass.
    Grabbed from six (https://pypi.python.org/pypi/six/)"""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


@add_metaclass(ABCMeta)
class Adapter(object):
    """Base class for SSL driver library adapters.

    Required methods:

        * ``wrap(sock) -> (wrapped socket, ssl environ dict)``
        * ``makefile(sock, mode='r', bufsize=DEFAULT_BUFFER_SIZE) ->
          socket file object``
    """

    @abstractmethod
    def __init__(
            self, certificate, private_key, certificate_chain=None,
            ciphers=None):
        """Set up certificates, private key ciphers and reset context."""
        self.certificate = certificate
        self.private_key = private_key
        self.certificate_chain = certificate_chain
        self.ciphers = ciphers
        self.context = None

    @abstractmethod
    def bind(self, sock):
        """Wrap and return the given socket."""
        return sock

    @abstractmethod
    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        raise NotImplementedError

    @abstractmethod
    def get_environ(self):
        """Return WSGI environ entries to be merged into each request."""
        raise NotImplementedError

    @abstractmethod
    def makefile(self, sock, mode='r', bufsize=-1):
        """Return socket file object."""
        raise NotImplementedError
