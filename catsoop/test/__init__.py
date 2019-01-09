import unittest
import warnings
import logging

from . import setup_data

logging.getLogger("cs").disabled = True


class CATSOOPTest(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ImportWarning)
