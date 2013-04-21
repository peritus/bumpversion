# -*- coding: utf-8 -*-

import ConfigParser
import argparse
import os
import warnings
import re
import sre_constants
import subprocess
from string import Formatter


def prefixed_environ():
    return dict((("${}".format(key), value) for key, value in os.environ.iteritems()))


def attempt_version_bump(args):
    try:
        regex = re.compile(args.parse)
    except sre_constants.error:
        warnings.warn("--patch '{}' is not a valid regex".format(args.parse))
        return

    if args.current_version:
        match = regex.search(args.current_version)
    else:
        return

    if not match:
        warnings.warn("'{}' does not parse current version".format(args.parse))
        return

    parsed = match.groupdict()

    order = (label for _, label, _, _ in Formatter().parse(args.serialize))

    bumped = False
    for label in order:
        if label == args.bump:
            parsed[args.bump] = int(parsed[args.bump]) + 1
            bumped = True
        elif bumped:
            parsed[label] = 0

    assert bumped
    parsed.update(prefixed_environ())

    try:
        return args.serialize.format(**parsed)
    except KeyError as e:
        warnings.warn("Did not find key {} in {} when serializing version number".format(
            repr(e.message), repr(parsed)))
        return


def main(args=None):

    parser1 = argparse.ArgumentParser(add_help=False)

    parser1.add_argument(
        '--config-file', default='.bumpversion.cfg', metavar='FILE',
        help='Config file to read most of the variables from', required=False)

    known_args, remaining_argv = parser1.parse_known_args(args)

    defaults = {}

    config = None
    if os.path.exists(known_args.config_file):
        config = ConfigParser.SafeConfigParser()
        config.read([known_args.config_file])
        defaults = dict(config.items("bumpversion"))
    elif known_args.config_file != parser1.get_default('config_file'):
        raise argparse.ArgumentTypeError("Could not read config file at {}".format(
            known_args.config_file))

    parser2 = argparse.ArgumentParser(add_help=False, parents=[parser1])
    parser2.set_defaults(**defaults)

    parser2.add_argument('--current-version', metavar='VERSION',
                         help='Version that needs to be updated', required=False)
    parser2.add_argument('--bump', metavar='PART',
                         help='Part of the version to be bumped.',
                         default='patch')
    parser2.add_argument('--parse', metavar='REGEX',
                         help='Regex parsing the version string',
                         default='(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)')
    parser2.add_argument('--serialize', metavar='FORMAT',
                         help='How to format what is parsed back to a version',
                         default='{major}.{minor}.{patch}')

    known_args, remaining_argv = parser2.parse_known_args(remaining_argv)

    defaults.update(vars(known_args))

    _attempted_new_version = attempt_version_bump(known_args)
    if not ('new_version' in defaults) and _attempted_new_version != None:
        defaults['new_version'] = _attempted_new_version

    parser3 = argparse.ArgumentParser(
        description='Bumps version strings',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        conflict_handler='resolve',
        parents=[parser2],
    )

    parser3.set_defaults(**defaults)

    parser3.add_argument('--current-version', metavar='VERSION',
                         help='Version that needs to be updated',
                         required=not 'current_version' in defaults)
    parser3.add_argument('--dry-run', '-n', action='store_true',
                         default=False, help="Don't write any files, just pretend.")
    parser3.add_argument('--new-version', metavar='VERSION',
                         help='New version that should be in the files',
                         required=not 'new_version' in defaults)
    parser3.add_argument('--commit', action='store_true',
                         help='Create a commit in version control')
    parser3.add_argument('--tag', action='store_true',
                         help='Create a tag in version control')
    parser3.add_argument('--message', '-m', metavar='COMMIT_MSG',
                         help='Commit message',
                         default='Bump version: {current_version} → {new_version}')

    files = []
    if 'files' in defaults:
        assert defaults['files'] != None
        files = defaults['files'].split(' ')

    parser3.add_argument('files', metavar='file',
                         nargs='+' if len(files) == 0 else '*',
                         help='Files to change', default=files)

    args = parser3.parse_args(remaining_argv)

    if len(args.files) is 0:
        warnings.warn("No files specified")

    if os.path.isdir(".git"):
        lines = [
            line.strip() for line in
            subprocess.check_output(
                ["git", "status", "--porcelain"]).splitlines()
            if not line.strip().startswith("??")
        ]

        if lines:
            assert False, "Git working directory not clean:\n{}".format(
                "\n".join(lines))

    for path in args.files:
        with open(path, 'r') as f:
            before = f.read()

        assert args.current_version in before, 'Did not find string {} in file {}'.format(
            args.current_version, path)

        after = before.replace(args.current_version, args.new_version)

        if not args.dry_run:
            with open(path, 'w') as f:
                f.write(after)

    commit_files = args.files

    if config:
        config.remove_option('bumpversion', 'new_version')
        config.set('bumpversion', 'current_version', args.new_version)

        if not args.dry_run:
            config.write(open(known_args.config_file, 'wb'))
            commit_files.append(known_args.config_file)

    if args.commit:
        if not args.dry_run:
            for path in commit_files:
                subprocess.check_call(["git", "add", path])

            formatargs = {
                "current_version": args.current_version,
                "new_version": args.new_version,
            }
            formatargs.update(prefixed_environ())

            subprocess.check_call(
                ["git", "commit", "-m", args.message.format(**formatargs)])
            if args.tag:
                subprocess.check_call(
                    ["git", "tag", "v{new_version}".format(**formatargs)])
