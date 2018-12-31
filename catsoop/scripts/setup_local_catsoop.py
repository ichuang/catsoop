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


def ask(prompt, default="", transform=lambda x: x, check_ok=lambda x: None):
    out = None
    while (not out) or (not check_ok(out)):
        defstr = ("\n[default: %s]" % default) if default else ""
        try:
            out = input("%s%s\n> " % (prompt, defstr)).strip()
        except EOFError:
            print()
            print("Caught EOF.  Exiting.")
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            out = None
            continue
        if out == "" and default:
            out = default
        out = transform(out)
        check_res = check_ok(out)
        if check_res is None:
            break
        else:
            print("ERROR: %s" % check_res)
            out = None
    print()
    return out


def yesno(question, default="Y"):
    res = ask(
        question,
        default,
        lambda x: x.lower(),
        lambda x: None if x in {"y", "n", "yes", "no"} else "Please answer Yes or No",
    )
    if res.startswith("y"):
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
            print("Caught EOF.  Exiting.")
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            out = None
            continue
    return out


def main():
    # print welcome message
    
    cs_logo = r"""
    
    \
    /    /\__/\
    \__=(  o_O )=
    (__________)
     |_ |_ |_ |_"""
    
    print(cs_logo)
    print("Welcome to the CAT-SOOP setup wizard.")
    print("Answer the questions below to get started.")
    print("To accept the default values, hit enter.")
    print()
    
    
    # determine cs_fs_root
    
    
    def is_catsoop_installation(x):
        # this isn't really a great check, but it's likely okay
        if not os.path.isdir(x):
            return "No such directory: %s" % x
        elif not os.path.exists(os.path.join(x, "base_context.py")):
            return "%s does not seem to contain a CAT-SOOP installation." % x
    
    
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    base_dir = os.path.abspath(os.path.join(scripts_dir, ".."))
    
    if is_catsoop_installation(base_dir) is not None:
        print("This does not appear to be a CAT-SOOP source tree.  Exiting.")
        sys.exit(1)
    
    print("Setting up for CAT-SOOP using installation at %s" % base_dir)
    cs_fs_root = base_dir
    
    config_loc = os.path.abspath("./config.py")
    if os.path.isfile(config_loc):
        res = yesno(
            "CAT-SOOP configuration at %s already exists.\n"
            "Continuing will overwrite it.\n"
            "Do you wish to continue?" % config_loc,
            default="N",
        )
        if not res:
            print("Okay.  Exiting.")
            sys.exit(1)
    
    # determine cs_data_root and logging info (encryption, etc)
    
    old_default_log_dir = os.path.abspath(os.path.join(base_dir, "..", "cat-soop-data"))
    default_log_dir = os.path.abspath("./cat-soop-data")
    cs_data_root = ask(
        "Where should CAT-SOOP store its logs?\n(this directory will be created if it does not exist)",
        transform=lambda x: os.path.abspath(os.path.expanduser(x)),
        default=default_log_dir,
       )
    
    
    # Authentication
    print(cs_logo)
    print(
        'Some courses set up local copies to use "dummy" authentication that always logs you in with a particular username.'
       )
    cs_dummy_username = ask(
        'For courses that use "dummy" authentication, what username should be used?',
        default="",
        check_ok=lambda x: None if x else "Please enter a username.",
       )
    
    
    # write config file
    config_file_content = """cs_fs_root = %r
    cs_data_root = %r
    
    cs_dummy_username = %r
    """ % (
        cs_fs_root,
        cs_data_root,
        cs_dummy_username,
       )
    
    config_path = config_loc
    if yesno("This configuration will be written to %s.  OK?" % config_path):
        with open(config_path, "w") as f:
            f.write(config_file_content)
        os.makedirs(os.path.join(cs_data_root, "courses"), exist_ok=True)
        _enc_salt_file = os.path.join(cs_fs_root, ".encryption_salt")
        _enc_hash_file = os.path.join(cs_fs_root, ".encryption_passphrase_hash")
        print()
        print("Configuration written to %s" % config_path)
        print(
            "You can check that this configuration information by opening this file in a text editor."
        )
        print(cs_logo)
        print(
            "Setup is complete.  You can now start CAT-SOOP by running the start_catsoop.py script."
        )
    else:
        print("Configuration not written.  Exiting.")

#-----------------------------------------------------------------------------

if __name__=="__main__":
    main()
    
