#!/usr/bin/env python3

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
import sys
import math
import getpass
import hashlib


def style(txt, sty):
    return sty + txt + "\x1B[0m"


def OKAY(txt):
    return style(txt, "\x1B[1;32m")  # bold green


def WARNING(txt):
    return style(txt, "\x1B[1;31m")  # bold red


def ERROR(txt):
    return style(txt, "\x1B[1;31m")  # bold red


def DIR(txt):
    return style(txt, "\x1B[1;33m")  # bold yellow


def FILE(txt):
    return style(txt, "\x1B[1;35m")  # bold magenta


def QUESTION(txt):
    return style(txt, "\x1B[1;36m")  # bold cyan


def ask(prompt, default="", transform=lambda x: x, check_ok=lambda x: None):
    out = None
    while (not out) or (not check_ok(out)):
        defstr = ("\n[default: %s]" % default) if default else ""
        try:
            out = input("%s%s\n> " % (prompt, defstr)).strip()
        except EOFError:
            print()
            print(ERROR("Caught EOF.  Exiting."))
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
            print(ERROR("ERROR: %s" % check_res))
            out = None
    print()
    return out


def yesno(question, default="Y"):
    res = ask(
        question,
        default,
        lambda x: x.lower(),
        lambda x: None
        if x in {"y", "n", "yes", "no"}
        else WARNING("Please answer Yes or No"),
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
            print(ERROR("Caught EOF.  Exiting."))
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            out = None
            continue
    return out


def is_catsoop_installation(x):
    # this isn't really a great check, but it's likely okay
    if not os.path.isdir(x):
        return ERROR("No such directory:") + " " + DIR(x)
    elif not os.path.exists(os.path.join(x, "base_context.py")):
        return DIR(x) + " " + ERROR("does not seem to contain a CAT-SOOP installation.")


cs_logo = r"""
\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_"""


default_config_location = os.environ.get(
    "XDG_CONFIG_HOME", os.path.expanduser(os.path.join("~", ".config"))
)
default_storage_location = os.environ.get(
    "XDG_DATA_HOME", os.path.expanduser(os.path.join("~", ".local", "share"))
)


def main():
    # print welcome message
    print(cs_logo)
    print("Welcome to the CAT-SOOP setup wizard.")
    print("Answer the questions below to get started.")
    print("To accept the default values, hit enter.")
    print("To exit, hit Crtl+d.")
    print()

    def _server_transform(x):
        x = x.strip().lower().replace(" ", "")
        if x in {"1", "localcopy", "local"}:
            return False
        elif x in {"2", "productioninstance", "production"}:
            return True

    is_production = ask(
        QUESTION("Are you setting up a production CAT-SOOP instance, or a local copy?")
        + "\n\n1. Local Copy\n2. Production Instance",
        default="1",
        transform=_server_transform,
        check_ok=lambda x: None if x is not None else ERROR("Invalid entry: %s" % x),
    )

    if is_production:
        configure_production()
    else:
        configure_local()


# -----------------------------------------------------------------------------


def configure_local():
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    base_dir = os.path.abspath(os.path.join(scripts_dir, ".."))

    if is_catsoop_installation(base_dir) is not None:
        print(ERROR("This does not appear to be a CAT-SOOP source tree.  Exiting."))
        sys.exit(1)

    print("Setting up for CAT-SOOP using installation at %s" % DIR(base_dir))
    cs_fs_root = base_dir

    config_loc = os.path.abspath(
        os.path.join(default_config_location, "catsoop", "config.py")
    )
    if os.path.isfile(config_loc):
        res = yesno(
            (
                "CAT-SOOP configuration at %s already exists.\n"
                "Continuing will overwrite it.\n" % FILE(config_loc)
            )
            + QUESTION("Do you wish to continue?"),
            default="N",
        )
        if not res:
            print("Okay.  Exiting.")
            sys.exit(1)

    # determine cs_data_root and logging info (encryption, etc)

    default_log_dir = os.path.abspath(os.path.join(default_storage_location, "catsoop"))
    cs_data_root = ask(
        QUESTION("Where should CAT-SOOP store its logs?")
        + "\n(this directory will be created if it does not exist)",
        transform=lambda x: os.path.abspath(os.path.expanduser(x)),
        default=default_log_dir,
    )

    # Authentication
    print(
        'Some courses set up local copies to use "dummy" authentication that always logs you in with a particular username.'
    )
    cs_dummy_username = ask(
        QUESTION(
            'For courses that use "dummy" authentication, what username should be used?'
        ),
        default="",
        check_ok=lambda x: None if x else WARNING("Please enter a username."),
    )

    # write config file
    config_file_content = """cs_data_root = %r

cs_dummy_username = %r
    """ % (
        cs_data_root,
        cs_dummy_username,
    )

    while True:
        config_loc = ask(
            QUESTION("Where should this configuration be saved?"), default=config_loc
        )

        requested_path = os.path.realpath(config_loc)
        split_data_path = os.path.realpath(os.path.join(cs_data_root, "courses")).split(
            os.sep
        )
        conflict = False

        ancestor = ""
        for d in split_data_path:
            ancestor = os.path.join(ancestor, d)
            if requested_path == ancestor:
                conflict = True

        if os.path.isdir(config_loc) or conflict:
            proposed_file = os.path.join(config_loc, "config.py")
            if yesno(
                DIR(config_loc)
                + " is a directory. "
                + QUESTION("OK to save the configuration as ")
                + FILE(proposed_file)
                + QUESTION("?")
            ):
                config_loc = proposed_file
                break
        else:
            break

    if yesno(
        "This configuration will be written to "
        + FILE(config_loc)
        + ". "
        + QUESTION("OK?")
    ):
        os.makedirs(os.path.join(cs_data_root, "courses"), exist_ok=True)

        os.makedirs(os.path.dirname(config_loc), exist_ok=True)
        with open(config_loc, "w") as f:
            f.write(config_file_content)
        _enc_salt_file = os.path.join(os.path.dirname(config_loc), "encryption_salt")
        _enc_hash_file = os.path.join(
            os.path.dirname(config_loc), "encryption_passphrase_hash"
        )
        try:
            os.unlink(_enc_salt_file)
        except:
            pass
        try:
            os.unlink(_enc_hash_file)
        except:
            pass
        print()
        print("Configuration written to " + FILE(config_loc))
        print(
            "You can check that this configuration information by opening this file in a text editor."
        )
        print(cs_logo)
        print(
            OKAY("Setup is complete.")
            + "  You can now start CAT-SOOP by running:\n    catsoop start"
        )
    else:
        print(WARNING("Configuration not written.  Exiting."))


# -----------------------------------------------------------------------------


def configure_production():
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    base_dir = os.path.abspath(os.path.join(scripts_dir, ".."))

    if is_catsoop_installation(base_dir) is not None:
        print(ERROR("This does not appear to be a CAT-SOOP source tree.  Exiting."))
        sys.exit(1)

    print("Setting up for CAT-SOOP at %s" % DIR(base_dir))
    cs_fs_root = base_dir

    config_loc = os.path.abspath(
        os.path.join(default_config_location, "catsoop", "config.py")
    )
    if os.path.isfile(config_loc):
        res = yesno(
            (
                "CAT-SOOP configuration at %s already exists.\n"
                "Continuing will overwrite it.\n" % FILE(config_loc)
            )
            + QUESTION("Do you wish to continue?"),
            default="N",
        )
        if not res:
            print("Okay.  Exiting.")
            sys.exit(1)

    # determine cs_data_root and logging info (encryption, etc)

    default_log_dir = os.path.abspath(os.path.join(default_storage_location, "catsoop"))
    cs_data_root = ask(
        QUESTION("Where should CAT-SOOP store its logs?")
        + "\n(this directory will be created if it does not exist)",
        transform=lambda x: os.path.abspath(os.path.expanduser(x)),
        default=default_log_dir,
    )

    print()
    print("By default, CAT-SOOP logs are not encrypted.")
    print(
        "Encryption can improve the privacy of people using CAT-SOOP by making"
        " the logs difficult to read for anyone without a particular passphrase."
        " Encrypted logs also mitigate the risks associated with backing up"
        " CAT-SOOP logs to servers you don't control.  Encryption comes with the"
        " downside that encrypted logs are not human readable, and that reading"
        " and writing encrypted logs is slower."
    )

    should_encrypt = yesno(
        "Since CAT-SOOP logs can store personally identifiable "
        "student information, you are strongly encouraged to "
        "encrypt the logs if you are running CAT-SOOP on a "
        "machine where logs are not already encrypted through "
        "some other means.\n" + QUESTION("Should CAT-SOOP encrypt its logs?"),
        default="N",
    )

    if should_encrypt:
        is_restore = yesno(
            QUESTION(
                "Will this instance use an encryption password/salt from a previous installation?"
            ),
            default="N",
        )

        if is_restore:
            restore_salt_str = input(
                "Please enter the salt used for the encrypted logs: "
            )
            cs_log_encryption_salt = bytes.fromhex(restore_salt_str)
            restore_passphrase_hash_str = input(
                "Please enter the password hash used for the encrypted logs: "
            )
            restore_passphrase_hash = bytes.fromhex(restore_passphrase_hash_str)
            should_encrypt = True
        # choose encryption passphrase
        print(
            "Files are encrypted using a passphrase of your choosing.  You will "
            "need to enter this passphrase whenever you start the CAT-SOOP "
            "server."
        )
        if is_restore:
            print("Please verify that your encryption passphrase is valid.")
        while True:
            cs_log_encryption_passphrase = password(
                "Enter %sencryption passphrase: " % ("" if is_restore else "an ")
            )
            if is_restore:
                passphrase_hash = hashlib.pbkdf2_hmac(
                    "sha512",
                    cs_log_encryption_passphrase.encode("utf8"),
                    cs_log_encryption_salt,
                    100000,
                )
                if restore_passphrase_hash != passphrase_hash:
                    print(
                        WARNING("Passphrase is not valid for this backup; try again.")
                    )
                    print()
                else:
                    break
            else:
                cs_log_encryption_passphrase_2 = password(
                    "Confirm encryption passphrase: "
                )
                if cs_log_encryption_passphrase != cs_log_encryption_passphrase_2:
                    print(WARNING("Passphrases do not match; try again."))
                    print()
                else:
                    break

        if not is_restore:
            cs_log_encryption_salt = os.urandom(32)
        cs_log_encryption_salt_printable = cs_log_encryption_salt.hex()
        cs_log_encryption_passphrase_hash = hashlib.pbkdf2_hmac(
            "sha512",
            cs_log_encryption_passphrase.encode("utf8"),
            cs_log_encryption_salt,
            100000,
        )
        cs_log_encryption_passphrase_hash_printable = (
            cs_log_encryption_passphrase_hash.hex()
        )

    print()
    print("By default, CAT-SOOP logs are not compressed.")
    print(
        "Compression can save disk space, with the downside that reading and"
        " writing compressed logs is slower."
    )

    should_compress = yesno(
        QUESTION("Should CAT-SOOP compress its logs?"),
        default="Y" if should_encrypt else "N",
    )

    # Web Stuff
    cs_url_root = ask(
        QUESTION("What is the root public-facing URL associated with this instance?"),
        default="http://localhost:6010",
        transform=lambda x: x.rstrip("/"),
    )
    cs_checker_websocket = ask(
        QUESTION(
            "What is the public-facing URL associated with the checker's websocket connection?"
        ),
        default="ws://localhost:6011",
        transform=lambda x: x.rstrip("/"),
    )

    ncpus = os.cpu_count() or 1
    guess_proc_min = math.ceil(ncpus / 2)
    guess_proc_max = max(guess_proc_min, math.floor(ncpus * 3/4))
    guess_nchecks = math.floor(max((ncpus-guess_proc_max)/2, 1))

    def _transform_int(x):
        try:
            return int(x)
        except:
            return x

    def _check_int(x):
        return None if isinstance(x, int) and x > 0 else WARNING("Please enter a positive integer.")

    cs_wsgi_server_min_processes = ask(
        QUESTION("What is the minimum number of processes catsoop should use for the web server?"),
        transform=_transform_int,
        check_ok=_check_int,
        default=guess_proc_min,
    )
    cs_wsgi_server_max_processes = ask(
        QUESTION("What is the maximum number of processes catsoop should use for the web server?"),
        transform=_transform_int,
        check_ok=_check_int,
        default=guess_proc_max,
    )
    cs_checker_parallel_checks = ask(
        QUESTION("How many submissions should be checked in parallel?"),
        transform=_transform_int,
        check_ok=_check_int,
        default=guess_nchecks,
    )

    # write config file
    config_file_content = """cs_data_root = %r

cs_log_compression = %r
cs_log_encryption = %r

cs_url_root = %r
cs_checker_websocket = %r

cs_wsgi_server = "uwsgi"
cs_wsgi_server_min_processes = %d
cs_wsgi_server_max_processes = %d

cs_checker_parallel_checks = %d
    """ % (
        cs_data_root,
        should_compress,
        should_encrypt,
        cs_url_root,
        cs_checker_websocket,
        cs_wsgi_server_min_processes,
        cs_wsgi_server_max_processes,
        cs_checker_parallel_checks,
    )

    while True:
        config_loc = ask(
            QUESTION("Where should this configuration be saved?"), default=config_loc
        )

        requested_path = os.path.realpath(config_loc)
        split_data_path = os.path.realpath(os.path.join(cs_data_root, "courses")).split(
            os.sep
        )
        conflict = False

        ancestor = ""
        for d in split_data_path:
            ancestor = os.path.join(ancestor, d)
            if requested_path == ancestor:
                conflict = True

        if os.path.isdir(config_loc) or conflict:
            proposed_file = os.path.join(config_loc, "config.py")
            if yesno(
                DIR(config_loc)
                + " is a directory. "
                + QUESTION("OK to save the configuration as ")
                + FILE(proposed_file)
                + QUESTION("?")
            ):
                config_loc = proposed_file
                break
        else:
            break

    if yesno(
        "This configuration will be written to "
        + FILE(config_loc)
        + ". "
        + QUESTION("OK?")
    ):
        os.makedirs(os.path.join(cs_data_root, "courses"), exist_ok=True)

        os.makedirs(os.path.dirname(config_loc), exist_ok=True)
        with open(config_loc, "w") as f:
            f.write(config_file_content)
        _enc_salt_file = os.path.join(os.path.dirname(config_loc), "encryption_salt")
        _enc_hash_file = os.path.join(
            os.path.dirname(config_loc), "encryption_passphrase_hash"
        )
        if should_encrypt:
            with open(_enc_salt_file, "wb") as f:
                f.write(cs_log_encryption_salt)
            with open(_enc_hash_file, "wb") as f:
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
        print("Configuration written to " + FILE(config_loc))
        print(
            "You can check that this configuration information by opening this file in a text editor."
        )
        print(cs_logo)
        print(
            OKAY("Setup is complete.")
            + "  You can now start CAT-SOOP by running:\n    catsoop start"
        )
        print()
        if should_encrypt and not is_restore:
            print(
                WARNING(
                    "Please save the following two pieces of information, which are necessary in case you need another CAT-SOOP instance to read logs encrypted by this instance."
                )
            )
            print()
            print("Encryption salt:", cs_log_encryption_salt_printable)
            print(
                "Encryption passphrase hash:",
                cs_log_encryption_passphrase_hash_printable,
            )
    else:
        print(WARNING("Configuration not written.  Exiting."))


# -----------------------------------------------------------------------------


if __name__ == "__main__":
    main()
