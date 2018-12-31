import os
import sys
import argparse
import pkg_resources

#-----------------------------------------------------------------------------

def CommandLine(args=None, arglist=None):
    '''
    Main catsoop command line entry point
    args, arglist are used for unit testing
    '''

    version = pkg_resources.require("catsoop")[0].version

    help_text = """
Example commands:

    runserver      : starts the CAT-SOOP webserver
    configure      : generate CAT-SOOP configuration file using an interactive wizard

"""
    cmd_help = """A variety of commands are available, each with different arguments:

runserver      : starts the CAT-SOOP webserver
configure      : generate CAT-SOOP configuration file using an interactive wizard

"""

    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("command", help=cmd_help)
    parser.add_argument("-v", "--verbose", help="increase debug output verbosity", action="store_true")
    parser.add_argument("-c", "--config-file", help="name of configuration file to use", default="./config.py")

    if not args:
        args = parser.parse_args(arglist)

    cfn = os.path.abspath(args.config_file)

    if args.verbose:
        os.environ['CATSOOP_DEBUG_LEVEL'] = "1"

    if args.command=="configure":
        from .scripts import setup_local_catsoop
        setup_local_catsoop.main()
        
    elif args.command=="runserver":
        from .scripts import start_catsoop
        print("cfn=%s" % cfn)
        start_catsoop.startup_catsoop(cfn)

    else:
        print("Unknown command %s" % args.command)
        sys.exit(-1)

