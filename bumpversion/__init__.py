
import ConfigParser
import argparse
import os.path

def main(args=None):

    parser = argparse.ArgumentParser(description='Bumps version strings')

    parser.add_argument('--config-file', default='.bumpversion.cfg', metavar='FILE',
        help='Config file to read most of the variables from', required=False)

    known_args, remaining_argv = parser.parse_known_args(args)

    defaults = {}
    if known_args.config_file and os.path.exists(known_args.config_file):
        config = ConfigParser.SafeConfigParser()
        config.read([known_args.config_file])
        defaults = dict(config.items("bumpversion"))
        defaults['files'] = defaults['files'].split(" ")
        print defaults
 
    parser.set_defaults(**defaults)

    parser.add_argument('--old-version', metavar='VERSION',
        help='Version that needs to be updated')
    parser.add_argument('--new-version', metavar='VERSION',
        help='New version that should be in the files')

    parser.add_argument('files', metavar='file', nargs='*',
            help='Files to change')

    print defaults, remaining_argv

    args = parser.parse_args(remaining_argv)

    do_it(args.old_version, args.new_version, args.files)

def do_it(old_version, new_version, files):
    for path in files:
        with open(path, 'r') as f:
            before = f.read()

        assert old_version in before, 'Did not find string {} in file {}'.format(
            old_version, path)

        after = before.replace(old_version, new_version)

        with open(path, 'w') as f:
            f.write(after)

