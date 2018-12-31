
import os
import tempfile

#-----------------------------------------------------------------------------

def setup_data_dir():
    mydir = os.path.dirname(__file__)
    test_course_dir = os.path.join(os.path.dirname(mydir), "__TEST_COURSE__")
    # tdir = tempfile.mkdtemp('catsoop_test')
    tdir = '/tmp/catsoop_test'
    if not os.path.exists(tdir):
        os.mkdir(tdir)
    cdir = os.path.join(tdir, "courses")
    if not os.path.exists(cdir):
        os.mkdir(cdir)
    tcdir = os.path.join(cdir, "test_course")
    if not os.path.exists(tcdir):
        os.symlink(test_course_dir, tcdir)
    os.environ['CAT_SOOP_DATA_DIR'] = tdir
    os.environ['CAT_SOOP_CONFIG'] = os.path.join(mydir, "test_config.py")
    print("setup cs_data_dir -> %s" % os.environ['CAT_SOOP_DATA_DIR'])
    print("setup cs config -> %s" % os.environ['CAT_SOOP_CONFIG'])

setup_data_dir()
