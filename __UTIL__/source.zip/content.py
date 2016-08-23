# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import os
import platform

from zipfile import ZipFile, ZIP_DEFLATED

course = cs_form.get('course', None)

def keep_file(full, base):
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
            if d.startswith('.'):
                to_remove.add(d)
        for d in to_remove:
            dirs.remove(d)
        for f in files:
            fullname = os.path.join(root, f)
            if keep_file(fullname, f):
                name = fullname.replace(base_dir, zip_base)
                zipfile.write(fullname, name)

tmp = os.environ.get('TEMP',cs_fs_root) if platform.system() == 'Windows' else '/tmp'

cache_fname = os.path.join(tmp, '.catsoop-source-%s.zip' % hash((cs_fs_root, course)))
regenerate = False
if not os.path.isfile(cache_fname):
    regenerate = True
else:
    source_modified = os.stat(cs_fs_root).st_mtime
    cache_modified = os.stat(cache_fname).st_mtime
    if source_modified > cache_modified:
        regenerate = True

if regenerate:
    with csm_tools.filelock.FileLock(cache_fname) as flock:
        outfile = ZipFile(cache_fname, 'w', ZIP_DEFLATED)
        add_files_to_zip(outfile, cs_fs_root, 'cat-soop-src/cat-soop')
        now = csm_time.from_detailed_timestamp(cs_timestamp)
        now = csm_time.long_timestamp(now).replace('; ', ' at')
        if course is None:
            outfile.writestr('cat-soop-src/README.catsoop-source',
                             SOURCE_README_NOCOURSE % (cs_url_root, now))
        else:
            ctx = {}
            csm_loader.load_global_data(ctx)
            cfile = csm_dispatch.content_file_location(ctx, [course])
            csm_loader.do_early_load(ctx, course, [], ctx, cfile)
            course_name = ctx.get('cs_long_name', course)
            outfile.writestr('cat-soop-src/README.catsoop-source',
                             SOURCE_README % (cs_url_root, now,
                                              course_name,
                                              course))
            plugins_base = os.path.join(cs_data_root, 'courses',
                                        course, '__PLUGINS__')
            add_files_to_zip(outfile,
                             plugins_base,
                             'cat-soop-src/%s/__PLUGINS__' % course)
            qtypes_base = os.path.join(cs_data_root, 'courses',
                                        course, '__QTYPES__')
            add_files_to_zip(outfile,
                             qtypes_base,
                             'cat-soop-src/%s/__QTYPES__' % course)
            handlers_base = os.path.join(cs_data_root, 'courses',
                                        course, '__HANDLERS__')
            add_files_to_zip(outfile,
                             handlers_base,
                             'cat-soop-src/%s/__HANDLERS' % course)
        outfile.close()

with csm_tools.filelock.FileLock(cache_fname) as flock:
    with open(cache_fname, 'rb') as f:
        response = f.read()

cs_handler = 'raw_response'
content_type = 'application/zip'
