# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
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
import ast
import platform
import subprocess

from zipfile import ZipFile, ZIP_DEFLATED

course = cs_form.get('course', None)

def keep_file(full, base):
    # ignore nohup output from scripts
    if base == 'nohup.out':
        return False
    # ignore compiled python files
    if base.endswith('.pyc') or '.pycs' in base:
        return False
    # ignore vim temporary files and swap files
    if base.endswith('~') or base.endswith('.swp'):
        return False
    # ignore emacs temporary files
    if base.startswith('#') and base.endswith('#'):
        return False
    # ignore Mercurial backup files
    if base.endswith('.orig'):
        return False
    # ignore dotfiles
    if base.startswith('.'):
        return False
    # ignore config.py in catsoop root
    if full == os.path.join(cs_fs_root, 'catsoop', 'config.py'):
        return False
    return True

def add_files_to_zip(zipfile, base_dir, zip_base):
    for root, dirs, files in os.walk(base_dir):
        to_remove = set()
        for d in dirs:
            if d.startswith('.') or d == 'node_modules':
                to_remove.add(d)
        for d in to_remove:
            dirs.remove(d)
        for f in files:
            fullname = os.path.join(root, f)
            if keep_file(fullname, f):
                name = fullname.replace(base_dir, zip_base)
                zipfile.write(fullname, name)

def _updated_time(x):
    if os.path.isdir(x):
        # get mtime for dirs in a roundabout way...
        try:
            # build a little pipeline to recursively find the timestamp of the
            # most recently modified file in a directory
            p = subprocess.Popen(['find', x, '-name', '__LOGS__', '-prune', '-o', '-type', 'f', '-printf', '%T@ %P\n'], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['sort', '-n'], stdin=p.stdout, stdout=subprocess.PIPE)
            p3 = subprocess.Popen(['awk', '{print $1}'], stdin=p2.stdout, stdout=subprocess.PIPE)
            p4 = subprocess.Popen(['tail', '-n', '1'], stdin=p3.stdout, stdout=subprocess.PIPE)
            return ast.literal_eval(p4.communicate()[0].decode())
        except:
            return os.stat(x).st_mtime
    return os.stat(x).st_mtime

tmp = os.environ.get('TEMP',cs_fs_root) if platform.system() == 'Windows' else '/tmp'

source_modified = _updated_time(cs_fs_root)
if course is not None:
    plugins_base = os.path.join(cs_data_root, 'courses', course, '__PLUGINS__')
    qtypes_base = os.path.join(cs_data_root, 'courses', course, '__QTYPES__')
    handlers_base = os.path.join(cs_data_root, 'courses', course, '__HANDLERS__')
    authtypes_base = os.path.join(cs_data_root, 'courses', course, '__AUTH__')
    for i in [qtypes_base, plugins_base, handlers_base, authtypes_base]:
        try:
            t = _updated_time(i)
            if t > source_modified:
                source_modified = t
        except:
            pass

cache_fname = os.path.join(tmp, '.catsoop-source-%s.zip' % hash((cs_fs_root, course)))
regenerate = False
if not os.path.isfile(cache_fname):
    regenerate = True
else:
    cache_modified = _updated_time(cache_fname)
    if source_modified > cache_modified:
        regenerate = True


if regenerate:
    with csm_tools.filelock.FileLock(cache_fname) as flock:
        outfile = ZipFile(cache_fname, 'w', ZIP_DEFLATED)
        add_files_to_zip(outfile, cs_fs_root, 'cat-soop-src/cat-soop')
        now = csm_time.from_detailed_timestamp(cs_timestamp)
        now = csm_time.long_timestamp(now).replace('; ', ' at ')
        if course is None:
            outfile.writestr('cat-soop-src/README.catsoop-source',
                             SOURCE_README_NOCOURSE % (cs_url_root, now))
        else:
            ctx = csm_loader.spoof_early_load([course])
            course_name = ctx.get('cs_long_name', course)
            course_name = course_name.replace('<br>', ' ').replace('<br/>', ' ').replace('</br>', ' ').replace('<br />', ' ')
            outfile.writestr('cat-soop-src/README.catsoop-source',
                             SOURCE_README % (cs_url_root, now,
                                              course_name,
                                              course))
            add_files_to_zip(outfile,
                             plugins_base,
                             'cat-soop-src/%s/__PLUGINS__' % course)
            add_files_to_zip(outfile,
                             qtypes_base,
                             'cat-soop-src/%s/__QTYPES__' % course)
            add_files_to_zip(outfile,
                             handlers_base,
                             'cat-soop-src/%s/__HANDLERS__' % course)
            add_files_to_zip(outfile,
                             authtypes_base,
                             'cat-soop-src/%s/__AUTH__' % course)
        outfile.close()

with csm_tools.filelock.FileLock(cache_fname) as flock:
    with open(cache_fname, 'rb') as f:
        response = f.read()

cs_handler = 'raw_response'
content_type = 'application/zip'
