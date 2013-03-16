
import ConfigParser
import argparse
import os.path
import warnings

def main(args=None):

    configfileparser = argparse.ArgumentParser(add_help=False)

    configfileparser.add_argument('--config-file', default='.bumpversion.cfg', metavar='FILE',
        help='Config file to read most of the variables from', required=False)

    known_args, remaining_argv = configfileparser.parse_known_args(args)

    parser = argparse.ArgumentParser(
      description='Bumps version strings',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      parents=[configfileparser])

    defaults = {}

    if os.path.exists(known_args.config_file):
        config = ConfigParser.SafeConfigParser()
        config.read([known_args.config_file])
        defaults = dict(config.items("bumpversion"))
    elif known_args.config_file != parser.get_default('config_file'):
        raise argparse.ArgumentTypeError("Could not read config file at {}".format(
            known_args.config_file))
 
    parser.set_defaults(**defaults)

    parser.add_argument('--old-version', metavar='VERSION',
        help='Version that needs to be updated')
    parser.add_argument('--new-version', metavar='VERSION',
        help='New version that should be in the files')

    files = []
    if 'files' in defaults:
        assert defaults['files'] != None
        files = defaults['files'].split(' ')

    parser.add_argument('files', metavar='file',
            nargs='+' if len(files) == 0 else '*',
            help='Files to change', default=files)

    args = parser.parse_args(remaining_argv)

    do_it(args.old_version, args.new_version, args.files)

def do_it(old_version, new_version, files):

    if len(files) is 0:
        warnings.warn("No files specified")

    for path in files:
        with open(path, 'r') as f:
            before = f.read()

        assert old_version in before, 'Did not find string {} in file {}'.format(
            old_version, path)

        after = before.replace(old_version, new_version)

        with open(path, 'w') as f:
            f.write(after)

