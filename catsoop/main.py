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
import argparse
import pkg_resources

# -----------------------------------------------------------------------------


def command_line_interface(args=None, arglist=None):
    """
    Main catsoop command line entry point
    args, arglist are used for unit testing
    """

    version = pkg_resources.require("catsoop")[0].version
    if "dev" in version:
        gitfile = os.path.join(os.path.dirname(__file__), "dev.githash")
        if os.path.isfile(gitfile):
            with open(gitfile, "r") as f:
                try:
                    hash_, date = f.read().split("|")
                    version = "%s\nGit revision: %s\n%s" % (version, hash_, date)
                except:
                    pass

    help_text = """
Example commands:

    runserver      : starts the CAT-SOOP webserver
    start          : alias for runserver
    configure      : generate CAT-SOOP configuration file using an interactive wizard
    logread        : show the content of a given log
    logwrite       : overwrite the content of a given log
    logedit        : edit the content of a given log in a text editor

"""
    cmd_help = """A variety of commands are available, each with different arguments:

runserver      : starts the CAT-SOOP webserver
start          : alias for runserver
configure      : generate CAT-SOOP configuration file using an interactive wizard
logread        : show the content of a given log
logwrite       : overwrite the content of a given log
logedit        : edit the content of a given log in a text editor

"""

    parser = argparse.ArgumentParser(
        description=help_text, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", help=cmd_help)
    parser.add_argument("args", nargs="*", help="arguments for the given command")
    parser.add_argument(
        "-v", "--verbose", help="increase debug output verbosity", action="store_true"
    )
    parser.add_argument(
        "--quiet", help="decrease debug output verbosity", action="store_true"
    )
    parser.add_argument(
        "--log-level", type=int, help="force log level to that specified", default=None
    )
    default_config_location = os.environ.get(
        "XDG_CONFIG_HOME", os.path.expanduser(os.path.join("~", ".config"))
    )
    parser.add_argument("--version", action="version", version="catsoop v%s" % version)
    default_config_location = os.path.abspath(
        os.path.join(default_config_location, "catsoop", "config.py")
    )
    parser.add_argument(
        "-c",
        "--config-file",
        help="name of configuration file to use",
        default=default_config_location,
    )

    if not args:
        args = parser.parse_args(arglist)

    cfn = os.path.abspath(args.config_file)

    if args.verbose:
        os.environ["CATSOOP_DEBUG_LEVEL"] = "1"

    if args.quiet:
        os.environ["CATSOOP_DEBUG_LEVEL"] = "20"

    if args.log_level:
        os.environ["CATSOOP_DEBUG_LEVEL"] = str(args.log_level)
        print(
            "Forcing catsoop debug log level to %s" % os.environ["CATSOOP_DEBUG_LEVEL"]
        )

    if args.command == "configure":
        from .scripts import configure

        configure.main()

    elif args.command in {"runserver", "start"}:
        from .scripts import start_catsoop

        print("cfn=%s" % cfn)
        start_catsoop.startup_catsoop(cfn)

    elif args.command == "logread":
        from .scripts import log_scripts

        log_scripts.log_read(args.args)

    elif args.command == "logwrite":
        from .scripts import log_scripts

        log_scripts.log_write(args.args)

    elif args.command == "logedit":
        from .scripts import log_scripts

        log_scripts.log_edit(args.args)

    else:
        print("Unknown command %s" % args.command)
        sys.exit(-1)
