#!/usr/bin/env python3

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
import sys
import getpass
import hashlib

def ask(prompt, default='', transform=lambda x: x, check_ok=lambda x: None):
    out = None
    while (not out) or (not check_ok(out)):
        defstr = ('\n[default: %s]' % default) if default else ''
        try:
            out = input('%s%s\n> ' % (prompt, defstr)).strip()
        except EOFError:
            print()
            print('Caught EOF.  Exiting.')
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            out = None
            continue
        if out == '' and default:
            out = default
        out = transform(out)
        check_res = check_ok(out)
        if check_res is None:
            break
        else:
            print('ERROR: %s' % check_res)
            out = None
    print()
    return out

def yesno(question, default='Y'):
    res = ask(question, default, lambda x: x.lower(), lambda x: None if x in {'y', 'n', 'yes', 'no'} else 'Please answer Yes or No')
    if res.startswith('y'):
        return True
    else:
        return False

def password(prompt):
    out = None
    while not out:
        try:
            out = getpass.getpass(prompt)
        except EOFError:
            print()
            print('Caught EOF.  Exiting.')
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            out = None
            continue
    return out


# print welcome message

cs_logo = r'''

\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_'''

print(cs_logo)
print('Welcome to the CAT-SOOP setup wizard.')
print('Answer the questions below to get started.')
print('To accept the default values, hit enter.')
print()


# determine cs_fs_root

def is_catsoop_installation(x):
    # this isn't really a great check, but it's likely okay
    if not os.path.isdir(x):
        return 'No such directory: %s' % x
    elif not os.path.isdir(os.path.join(x, 'catsoop')):
        return '%s does not seem to contain a CAT-SOOP installation.' % x


scripts_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(scripts_dir, '..'))

if is_catsoop_installation(base_dir) is not None:
    print('This does not appear to be a CAT-SOOP source tree.  Exiting.')
    sys.exit(1)

print('Setting up for CAT-SOOP at %s' % base_dir)
cs_fs_root = base_dir

config_loc = os.path.join(cs_fs_root, 'catsoop', 'config.py')
if os.path.isfile(config_loc):
    res = yesno('CAT-SOOP configuration at %s already exists.\n'
                'Continuing will overwrite it.\n'
                'Do you wish to continue?' % config_loc,
                default='N')
    if not res:
        print('Okay.  Exiting.')
        sys.exit(1)

# determine cs_data_root and logging info (encryption, etc)

default_log_dir = os.path.abspath(os.path.join(base_dir, '..', 'cat-soop-data'))
cs_data_root = ask('Where should CAT-SOOP store its logs?\n(this directory will be created if it does not exist)',
                   transform=lambda x:os.path.abspath(os.path.expanduser(x)),
                   default = default_log_dir)


print()
print(cs_logo)
print('By default, CAT-SOOP logs are not encrypted.')
print('Encryption can improve the privacy of people using CAT-SOOP by making'
      ' the logs difficult to read for anyone without a particular passphrase.'
      ' Encrypted logs also mitigate the risks associated with backing up'
      ' CAT-SOOP logs to servers you don\'t control.  Encryption comes with the'
      ' downside that encrypted logs are not human readable, and that reading'
      ' and writing encrypted logs is slower.')

should_encrypt = yesno('Since CAT-SOOP logs can store personally identifiable '
                       'student information, you are strongly encouraged to '
                       'encrypt the logs if you are running CAT-SOOP on a '
                       'machine where logs are not already encrypted through '
                       'some other means.\n'
                       'Should CAT-SOOP encrypt its logs?', default='Y')

if should_encrypt:
    # choose encryption passphrase
    print('Files are encrypted using a passphrase of your choosing.  You will '
          'need to enter this passphrase whenever you start the CAT-SOOP '
          'server.')
    while True:
        cs_log_encryption_passphrase = password('Enter an encryption passphrase: ')
        cs_log_encryption_passphrase_2 = password('Confirm encryption passphrase: ')
        if cs_log_encryption_passphrase == cs_log_encryption_passphrase_2:
            break
        else:
            print('Passphrases do not match; try again.')
            print()
            continue

    cs_log_encryption_salt = os.urandom(32)
    cs_log_encryption_passphrase_hash = hashlib.pbkdf2_hmac('sha512', cs_log_encryption_passphrase.encode('utf8'), cs_log_encryption_salt, 100000)

print()
print(cs_logo)
print('By default, CAT-SOOP logs are not compressed.')
if should_encrypt:
    print('Compression can save disk space, with the downside that reading and'
          ' writing compressed logs is slower.')
else:
    print('Compression can save disk space, with the downside that compressed'
          ' logs are not human readable, and that reading and writing'
          ' compressed logs is slower.')

should_compress = yesno('Should CAT-SOOP compress its logs?', default='Y' if should_encrypt else 'N')

# Web Stuff
print(cs_logo)
cs_url_root = ask('What is the root public-facing URL associated with this instance?',
                  default='http://localhost:6010',
                  transform=lambda x: x.rstrip('/'))
cs_checker_websocket = ask('What is the public-facing URL associated with the checker\'s websocket connection?',
                  default='ws://localhost:6011',
                  transform=lambda x: x.rstrip('/'))


# write config file
config_file_content = '''cs_fs_root = %r
cs_data_root = %r

cs_log_compression = %r
cs_log_encryption = %r

cs_url_root = %r
cs_checker_websocket = %r
''' % (cs_fs_root, cs_data_root, should_compress,
       should_encrypt,
       cs_url_root, cs_checker_websocket)


config_path = os.path.join(cs_fs_root, 'catsoop', 'config.py')
if yesno('This configuration will be written to %s.  OK?' % config_path):
    with open(config_path, 'w') as f:
        f.write(config_file_content)
    os.makedirs(os.path.join(cs_data_root, 'courses'), exist_ok=True)
    _enc_salt_file = os.path.join(cs_fs_root, '.encryption_salt')
    _enc_hash_file = os.path.join(cs_fs_root, '.encryption_passphrase_hash')
    if should_encrypt:
        with open(_enc_salt_file, 'wb') as f:
            f.write(cs_log_encryption_salt)
        with open(_enc_hash_file, 'wb') as f:
            f.write(cs_log_encryption_passphrase_hash)
    else:
        try:
            os.unlink(_enc_salt_file)
        except:
            pass
        try:
            os.unlink(_enc_hash_file)
        except:
            pass
    print()
    print('Configuration written to %s' % config_path)
    print('You can check that this configuration information by opening this file in a text editor.')
    print(cs_logo)
    print('Setup is complete.  You can now start CAT-SOOP by running the start_catsoop.py script.')
else:
    print('Configuration not written.  Exiting.')
