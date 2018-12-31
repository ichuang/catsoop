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

import os
import tempfile

#-----------------------------------------------------------------------------

def setup_data_dir():
    mydir = os.path.dirname(__file__)
    test_course_dir = os.path.join(os.path.dirname(mydir), "__TEST_COURSE__")
    # tdir = tempfile.mkdtemp('catsoop_test')
    tdir = '/tmp/catsoop_test'
    cdir = os.path.join(tdir, "courses")
    os.makedirs(cdir, exist_ok=True)

    tcdir = os.path.join(cdir, "test_course")
    if not os.path.exists(tcdir):
        os.symlink(test_course_dir, tcdir)
    os.environ['CATSOOP_DATA_DIR'] = tdir
    os.environ['CATSOOP_CONFIG'] = os.path.join(mydir, "test_config.py")
    print("setup cs_data_dir -> %s" % os.environ['CATSOOP_DATA_DIR'])
    print("setup cs config -> %s" % os.environ['CATSOOP_CONFIG'])

setup_data_dir()
