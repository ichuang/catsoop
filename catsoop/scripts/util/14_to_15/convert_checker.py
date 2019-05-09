import os
import sys
import zlib
import pickle
import shutil

this_dir = os.path.dirname(__file__)
catsoop_root = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
sys.path.append(catsoop_root)

import catsoop.cslog as cslog
import catsoop.base_context as bc

results = os.path.join(bc.cs_data_root, "_logs", "_checker")
for root, dirs, files in os.walk(results):
    dirs.sort()
    for fname in files:
        fn = os.path.join(root, fname)
        try:
            with open(fn, "r") as f:
                x = eval(f.read().strip())
        except:
            continue
        with open(fn, "wb") as f:
            f.write(cslog.prep(x))
        print(fn)
