# -*- coding: utf-8 -*-

from __future__ import unicode_literals

try:
    from configparser import RawConfigParser, NoOptionError
except ImportError:
    from ConfigParser import RawConfigParser, NoOptionError

try:
    from StringIO import StringIO
except:
    from io import StringIO


import argparse
import os
import warnings
import re
import sre_constants
import subprocess
import io
from string import Formatter
from datetime import datetime

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

__VERSION__ = '0.3.5'

DESCRIPTION = 'Bumpversion: v{} (using Python v{})'.format(
    __VERSION__,
    sys.version.split("\n")[0].split(" ")[0],
)


class Git(object):

    @classmethod
    def is_usable(cls):
        return os.path.isdir(".git")

    @classmethod
    def assert_nondirty(cls):
        lines = [
            line.strip() for line in
            subprocess.check_output(
                ["git", "status", "--porcelain"]).splitlines()
            if not line.strip().startswith(b"??")
        ]

        if lines:
            assert False, "Git working directory not clean:\n{}".format(
                b"\n".join(lines))

    @classmethod
    def latest_tag_info(cls):
        try:
            # git-describe doesn't update the git-index, so we do that
            subprocess.check_call(["git", "update-index", "--refresh"])

            # get info about the latest tag in git
            describe_out = subprocess.check_output([
                "git",
                "describe",
                "--dirty",
                "--tags",
                "--long",
                "--abbrev=40",
                "--match=v*",
            ], stderr=subprocess.STDOUT
            ).decode().split("-")
        except subprocess.CalledProcessError:
            # logging.warn("Error when running git describe")
            return {}

        info = {}

        if describe_out[-1] is "dirty":
            info["dirty"] = True
            describe_out.pop()

        info["commit_sha"] = describe_out.pop().lstrip("g")
        info["distance_to_latest_tag"] = int(describe_out.pop())
        info["current_version"] = describe_out.pop().lstrip("v")

        # assert type(info["current_version"]) == str
        assert 0 == len(describe_out)

        return info

    @classmethod
    def add_path(cls, path):
        subprocess.check_call(["git", "add", path])

    @classmethod
    def commit(cls, message):
        subprocess.check_call(["git", "commit", "-m", message.encode('utf-8')])

    @classmethod
    def tag(cls, name):
        subprocess.check_call(["git", "tag", name])


class Mercurial(object):

    @classmethod
    def is_usable(cls):
        return os.path.isdir(".hg")

    @classmethod
    def latest_tag_info(cls):
        return {}

    @classmethod
    def assert_nondirty(cls):
        lines = [
            line.strip() for line in
            subprocess.check_output(
                ["hg", "status", "-mard"]).splitlines()
            if not line.strip().startswith(b"??")
        ]

        if lines:
            assert False, "Mercurial working directory not clean:\n{}".format(
                b"\n".join(lines))

    @classmethod
    def add_path(cls, path):
        pass

    @classmethod
    def commit(cls, message):
        subprocess.check_call(["hg", "commit", "-m", message.encode('utf-8')])

    @classmethod
    def tag(cls, name):
        subprocess.check_call(["hg", "tag", name])

VCS = [Git, Mercurial]


def prefixed_environ():
    return dict((("${}".format(key), value) for key, value in os.environ.items()))


class VersionPart(object):

    FIRST_NUMERIC = re.compile('([^\d]*)(\d+)(.*)')

    def __init__(self, value):
        self.value = value

    def bump(self):
        part_prefix, numeric_version, part_suffix = self.FIRST_NUMERIC.search(self.value).groups()
        bumped_numeric = str(int(numeric_version) + 1)
        self.value = "".join([part_prefix, bumped_numeric, part_suffix])

    def __format__(self, format_spec):
        return self.value

    def zero(self):
        self.value = "0"


class Version(object):

    """
    Holds a complete representation of a version string
    """

    def __init__(self, parse_regex, serialize_format, context=None):

        try:
            self.parse_regex = re.compile(parse_regex)
        except:
            warnings.warn("--patch '{}' is not a valid regex".format(parse_regex))

        self.serialize_format = serialize_format

        if not context:
            context = {}

        self.context = context

    def order(self):
        return (label for _, label, _, _ in Formatter().parse(self.serialize_format))

    def register_part(self, part):
        pass

    def parse(self, version_string):
        match = self.parse_regex.search(version_string)

        self._parsed = {}
        if not match:
            warnings.warn("'{}' does not parse current version".format(self.parse_regex.pattern))
            return

        for key, value in match.groupdict().items():
            self._parsed[key] = VersionPart(value)

    def serialize(self):
        values = self.context.copy()
        values.update(self._parsed)
        try:
            return self.serialize_format.format(**values)
        except KeyError as e:
            assert hasattr(e, 'message'), dir(e)
            warnings.warn("Did not find key {} in {} when serializing version number".format(
                repr(e.message), repr(self._parsed)))
            return

    def bump(self, part_name):
        bumped = False

        for label in self.order():
            if not label in self._parsed:
                continue
            elif label == part_name:
                self._parsed[part_name].bump()
                bumped = True
            elif bumped:
                self._parsed[label].zero()


def main(args=None):

    parser1 = argparse.ArgumentParser(add_help=False)

    parser1.add_argument(
        '--config-file', default='.bumpversion.cfg', metavar='FILE',
        help='Config file to read most of the variables from', required=False)

    known_args, remaining_argv = parser1.parse_known_args(args)

    defaults = {}
    vcs_info = {}

    for vcs in VCS:
        if vcs.is_usable():
            vcs_info.update(vcs.latest_tag_info())

    if 'current_version' in vcs_info:
        defaults['current_version'] = vcs_info['current_version']

    config = None
    if os.path.exists(known_args.config_file):
        config = RawConfigParser()
        config.readfp(io.open(known_args.config_file, 'rt', encoding='utf-8'))

        defaults.update(dict(config.items("bumpversion")))

        for boolvaluename in ("commit", "tag", "dry_run"):
            try:
                defaults[boolvaluename] = config.getboolean(
                    "bumpversion", boolvaluename)
            except NoOptionError:
                pass  # no default value then ;)

    elif known_args.config_file != parser1.get_default('config_file'):
        raise argparse.ArgumentTypeError("Could not read config file at {}".format(
            known_args.config_file))

    parser2 = argparse.ArgumentParser(add_help=False, parents=[parser1])
    parser2.set_defaults(**defaults)

    parser2.add_argument('--current-version', metavar='VERSION',
                         help='Version that needs to be updated', required=False)
    parser2.add_argument('--parse', metavar='REGEX',
                         help='Regex parsing the version string',
                         default='(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)')
    parser2.add_argument('--serialize', metavar='FORMAT',
                         help='How to format what is parsed back to a version',
                         default='{major}.{minor}.{patch}')

    parser2_2 = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        conflict_handler='resolve',
        add_help=False,
        parents=[parser2],
    )
    parser2_2.add_argument('part', help='Part of the version to be bumped.', nargs='?')

    known_args, remaining_argv = parser2_2.parse_known_args(remaining_argv)

    if known_args.part:
        remaining_argv[0:0] = [known_args.part]

    defaults.update(vars(known_args))

    time_context = {
        'now': datetime.now(),
        'utcnow': datetime.utcnow(),
    }

    v = Version(
        known_args.parse,
        known_args.serialize,
        context=dict(list(time_context.items()) + list(prefixed_environ().items()) + list(vcs_info.items()))
    )

    if not 'new_version' in defaults and known_args.current_version:
        v.parse(known_args.current_version)
        v.bump(known_args.part)
        defaults['new_version'] = v.serialize()

    parser3 = argparse.ArgumentParser(
        description=DESCRIPTION,
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

    commitgroup = parser3.add_mutually_exclusive_group()

    commitgroup.add_argument('--commit', action='store_true', dest="commit",
                             help='Commit to version control', default=defaults.get("commit", False))
    commitgroup.add_argument('--no-commit', action='store_false', dest="commit",
                             help='Do not commit to version control', default=argparse.SUPPRESS)

    taggroup = parser3.add_mutually_exclusive_group()

    taggroup.add_argument('--tag', action='store_true', dest="tag", default=defaults.get("commit", False),
                          help='Create a tag in version control')
    taggroup.add_argument('--no-tag', action='store_false', dest="tag",
                          help='Do not create a tag in version control', default=argparse.SUPPRESS)

    parser3.add_argument('--tag-name', metavar='TAG_NAME',
                         help='Tag name (only works with --tag)',
                         default=defaults.get('tag_name', 'v{new_version}'))

    parser3.add_argument('--message', '-m', metavar='COMMIT_MSG',
                         help='Commit message',
                         default=defaults.get('message', 'Bump version: {current_version} → {new_version}'))

    files = []
    if 'files' in defaults:
        assert defaults['files'] != None
        files = defaults['files'].split(' ')

    parser3.add_argument('part',
                         help='Part of the version to be bumped.')
    parser3.add_argument('files', metavar='file',
                         nargs='+' if len(files) == 0 else '*',
                         help='Files to change', default=files)

    args = parser3.parse_args(remaining_argv)

    if len(args.files) is 0:
        warnings.warn("No files specified")

    for vcs in VCS:
        if vcs.is_usable():
            vcs.assert_nondirty()
            break

    # make sure files exist and contain version string
    for path in args.files:
        with io.open(path, 'rb') as f:
            before = f.read().decode('utf-8')

        assert args.current_version in before, 'Did not find string {} in file {}'.format(
            args.current_version, path)

    # change version string in files
    for path in args.files:
        with io.open(path, 'rb') as f:
            before = f.read().decode('utf-8')

        # assert type(args.current_version) == bytes
        # assert type(args.new_version) == bytes

        after = before.replace(args.current_version, args.new_version)

        if not args.dry_run:
            with io.open(path, 'wt', encoding='utf-8') as f:
                f.write(after)

    commit_files = args.files

    if config:
        config.remove_option('bumpversion', 'new_version')

        config.set('bumpversion', 'current_version', args.new_version)

        if not args.dry_run:
            s = StringIO()

            try:
                config.write(s)
                with io.open(known_args.config_file, 'wb') as f:
                    f.write(s.getvalue().encode('utf-8'))
            except UnicodeEncodeError:
                warnings.warn(
                    "Unable to write UTF-8 to config file, because of an old configparser version. "
                    "Update with `pip install --upgrade configparser`."
                )

            commit_files.append(known_args.config_file)

    if args.commit:
        if not args.dry_run:
            for path in commit_files:
                vcs.add_path(path)

            vcs_context = {
                "current_version": args.current_version,
                "new_version": args.new_version,
            }
            vcs_context.update(time_context)
            vcs_context.update(prefixed_environ())

            vcs.commit(message=args.message.format(**vcs_context))

            if args.tag:
                vcs.tag(args.tag_name.format(**vcs_context))
