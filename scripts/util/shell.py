import os
import sys

this_dir = os.path.dirname(__file__)
catsoop_root = os.path.abspath(os.path.join(this_dir, '..', '..'))
sys.path.append(catsoop_root)

import catsoop.cslog as cslog
