import os
import sys
import shutil

this_dir = os.path.dirname(__file__)
catsoop_root = os.path.abspath(os.path.join(this_dir, '..', '..', '..'))
sys.path.append(catsoop_root)

import catsoop.cslog as cslog
import catsoop.base_context as bc

results = os.path.join(bc.cs_data_root, '__LOGS__', '_checker', 'results')
for fname in os.listdir(results):
    print(fname)
    newdir = os.path.join(results, fname[0], fname[1])
    os.makedirs(newdir, exist_ok=True)
    shutil.move(os.path.join(results, fname), os.path.join(newdir, fname))
