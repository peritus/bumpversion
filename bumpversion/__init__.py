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
import re
import sre_constants
import subprocess
import io
from string import Formatter
from datetime import datetime
from difflib import unified_diff

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

__VERSION__ = '0.4.0'

DESCRIPTION = 'bumpversion: v{} (using Python v{})'.format(
    __VERSION__,
    sys.version.split("\n")[0].split(" ")[0],
)

import logging
logger = logging.getLogger("bumpversion")

from argparse import _AppendAction
class DiscardDefaultIfSpecifiedAppendAction(_AppendAction):

    '''
    Fixes bug http://bugs.python.org/issue16399 for 'append' action
    '''

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(self, "_discarded_default", None) is None:
            setattr(namespace, self.dest, [])
            self._discarded_default = True

        super(DiscardDefaultIfSpecifiedAppendAction, self).__call__(
                parser, namespace, values, option_string=None)

class BaseVCS(object):

    @classmethod
    def is_usable(cls):
        try:
            return subprocess.call(
                cls._TEST_USABLE_COMMAND,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            ) == 0
        except OSError as e:
            if e.errno == 2:
                # mercurial is not installed then, ok.
                return False
            raise


class Git(BaseVCS):

    _TEST_USABLE_COMMAND = ["git", "rev-parse", "--git-dir"]

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
            subprocess.check_output(["git", "update-index", "--refresh"])

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
            # logger.warn("Error when running git describe")
            return {}

        info = {}

        if describe_out[-1].strip() == "dirty":
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
        subprocess.check_output(["git", "add", "--update", path])

    @classmethod
    def commit(cls, message):
        subprocess.check_output(["git", "commit", "-m", message.encode('utf-8')])

    @classmethod
    def tag(cls, name):
        subprocess.check_output(["git", "tag", name])


class Mercurial(BaseVCS):

    _TEST_USABLE_COMMAND = ["hg", "root"]

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
        subprocess.check_output(["hg", "commit", "-m", message.encode('utf-8')])

    @classmethod
    def tag(cls, name):
        subprocess.check_output(["hg", "tag", name])

VCS = [Git, Mercurial]


def prefixed_environ():
    return dict((("${}".format(key), value) for key, value in os.environ.items()))


class VersionPart(object):

    FIRST_NUMERIC = re.compile('([^\d]*)(\d+)(.*)')

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value or "0"

    def bump(self):
        part_prefix, numeric_version, part_suffix = self.FIRST_NUMERIC.search(self.value).groups()
        bumped_numeric = str(int(numeric_version) + 1)
        self._value = "".join([part_prefix, bumped_numeric, part_suffix])

    def is_optional(self):
        return self.value == "0"

    def __format__(self, format_spec):
        return self.value

    def __repr__(self):
        return '<bumpversion.VersionPart:{}>'.format(self.value)

    def zero(self):
        self._value = "0"

class IncompleteVersionRepresenationException(Exception):
    def __init__(self, message):
        self.message = message

class MissingValueForSerializationException(Exception):
    def __init__(self, message):
        self.message = message

class Version(object):

    """
    Holds a complete representation of a version string
    """

    def __init__(self, parse_regex, serialize_formats, context=None):

        try:
            self.parse_regex = re.compile(parse_regex)
        except sre_constants.error as e:
            logger.error("--parse '{}' is not a valid regex".format(parse_regex))
            raise e

        self.serialize_formats = serialize_formats

        if not context:
            context = {}

        self.context = context

    def _labels_for_format(self, serialize_format):
        return (label for _, label, _, _ in Formatter().parse(serialize_format))

    def order(self):
        # currently, order depends on the first given serialization format
        # this seems like a good idea because this should be the most complete format
        return self._labels_for_format(self.serialize_formats[0])

    def register_part(self, part):
        pass

    def parse(self, version_string):

        logger.info("Parsing current version '{}' with '{}'".format(version_string, self.parse_regex.pattern))

        match = self.parse_regex.search(version_string)

        self._parsed = {}
        if not match:
            logger.warn("Evaluating 'parse' option: '{}' does not parse current version '{}'".format(
                self.parse_regex.pattern, version_string))
            return

        for key, value in match.groupdict().items():
            self._parsed[key] = VersionPart(value)

        logger.info("Parsed the following values: " + self._keyvalue_string())

    def _keyvalue_string(self):
        return ", ".join("{}={}".format(k, v) for k, v in sorted(self._parsed.items()))

    def _serialize(self, serialize_format, raise_if_incomplete=False):
        """
        Attempts to serialize a version with the given serialization format.

        Raises MissingValueForSerializationException if not serializable
        """
        values = self.context.copy()
        values.update(self._parsed)

        # TODO dump complete context on debug level

        try:
            # test whether all parts required in the format have values
            serialized = serialize_format.format(**values)

        except KeyError as e:
            missing_key = getattr(e,
                'message', # Python 2
                e.args[0] # Python 3
            )
            raise MissingValueForSerializationException(
                "Did not find key {} in {} when serializing version number".format(
                    repr(missing_key), repr(self._parsed)))

        keys_needing_representation = set([k for k, v in self._parsed.items() if not v.is_optional()])

        keys_needing_representation = set([])
        found_required = False
        for k in self.order():
            v = values[k]

            if not isinstance(v, VersionPart):
                # values coming from environment variables don't need
                # representation
                continue

            if not v.is_optional():
                found_required = True
                keys_needing_representation.add(k)
            elif not found_required:
                keys_needing_representation.add(k)

        required_by_format = set(self._labels_for_format(serialize_format))

        # try whether all parsed keys are represented
        if raise_if_incomplete:
            if keys_needing_representation > required_by_format:
                raise IncompleteVersionRepresenationException(
                    "Could not represent '{}' in format '{}'".format(
                        "', '".join(keys_needing_representation - required_by_format),
                        serialize_format,
                    ))

        return serialized


    def _choose_serialize_format(self):

        chosen = None

        logger.info("Available serialization formats: '{}'".format("', '".join(self.serialize_formats)))

        for serialize_format in self.serialize_formats:
            try:
                self._serialize(serialize_format, raise_if_incomplete=True)
                chosen = serialize_format
                logger.info("Found '{}' to be a usable serialization format".format(chosen))
            except IncompleteVersionRepresenationException as e:
                logger.info(e.message)
                if not chosen:
                    chosen = serialize_format
            except MissingValueForSerializationException as e:
                logger.info(e.message)

        if not chosen:
            raise KeyError("Did not find suitable serialization format")

        logger.info("Selected serialization format '{}'".format(chosen))

        return chosen

    def serialize(self):
        serialized = self._serialize(self._choose_serialize_format())

        logger.info("Serialized to '{}'".format(serialized))

        return serialized

    def bump(self, part_name):

        logger.info("Attempting to increment part '{}'".format(part_name))

        bumped = False

        for label in self.order():
            if not label in self._parsed:
                continue
            elif label == part_name:
                self._parsed[part_name].bump()
                bumped = True
            elif bumped:
                self._parsed[label].zero()

        logger.info("Values are now: " + self._keyvalue_string())

OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES = [
    '--config-file',
    '--current-version',
    '--message',
    '--new-version',
    '--parse',
    '--serialize',
    '--tag-name',
]


def split_args_in_optional_and_positional(args):
    # manually parsing positional arguments because stupid argparse can't mix
    # positional and optional arguments

    positions = []
    for i, arg in enumerate(args):

        previous = None

        if i > 0:
            previous = args[i-1]

        if ((not arg.startswith('--'))  and
            (previous not in OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES)):
            positions.append(i)

    positionals = [arg for i, arg in enumerate(args) if i in positions]
    args = [arg for i, arg in enumerate(args) if i not in positions]

    return (positionals, args)

def main(original_args=None):

    positionals, args = split_args_in_optional_and_positional(
      sys.argv[1:] if original_args is None else original_args
    )

    parser1 = argparse.ArgumentParser(add_help=False)

    parser1.add_argument(
        '--config-file', default='.bumpversion.cfg', metavar='FILE',
        help='Config file to read most of the variables from', required=False)

    parser1.add_argument(
        '--verbose', action='count', default=0,
        help='Print verbose logging to stderr', required=False)

    known_args, remaining_argv = parser1.parse_known_args(args)

    if len(logger.handlers) == 0:
        ch = logging.StreamHandler(sys.stderr)
        logformatter = logging.Formatter('%(message)s')
        ch.setFormatter(logformatter)
        logger.addHandler(ch)

    log_level = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }.get(known_args.verbose, logging.DEBUG)

    logger.setLevel(log_level)

    logger.debug("Starting {}".format(DESCRIPTION))

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

        log_config = StringIO()
        config.write(log_config)
        logger.info("Reading config file {}:".format(known_args.config_file))

        logger.info(log_config.getvalue())

        defaults.update(dict(config.items("bumpversion")))

        for listvaluename in ("serialize",):
            try:
                value = config.get("bumpversion", listvaluename)
                defaults[listvaluename] = list(filter(None, (x.strip() for x in value.splitlines())))
            except NoOptionError:
                pass  # no default value then ;)

        for boolvaluename in ("commit", "tag", "dry_run"):
            try:
                defaults[boolvaluename] = config.getboolean(
                    "bumpversion", boolvaluename)
            except NoOptionError:
                pass  # no default value then ;)

    else:
        message = "Could not read config file at {}".format(known_args.config_file)
        if known_args.config_file != parser1.get_default('config_file'):
            raise argparse.ArgumentTypeError(message)
        else:
            logger.info(message)

    parser2 = argparse.ArgumentParser(add_help=False, parents=[parser1])
    parser2.set_defaults(**defaults)

    parser2.add_argument('--current-version', metavar='VERSION',
                         help='Version that needs to be updated', required=False)
    parser2.add_argument('--parse', metavar='REGEX',
                         help='Regex parsing the version string',
                         default=defaults.get("parse", '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'))
    parser2.add_argument('--serialize', metavar='FORMAT',
                         action=DiscardDefaultIfSpecifiedAppendAction,
                         help='How to format what is parsed back to a version',
                         default=defaults.get("serialize", [str('{major}.{minor}.{patch}')]))

    known_args, remaining_argv = parser2.parse_known_args(args)

    defaults.update(vars(known_args))

    assert type(known_args.serialize) == list

    time_context = {
        'now': datetime.now(),
        'utcnow': datetime.utcnow(),
    }

    try:
        v = Version(
            known_args.parse,
            known_args.serialize,
            context=dict(list(time_context.items()) + list(prefixed_environ().items()) + list(vcs_info.items()))
        )
    except sre_constants.error as e:
        sys.exit(1)

    if not 'new_version' in defaults and known_args.current_version:
        v.parse(known_args.current_version)

        if len(positionals) > 0:
            v.bump(positionals[0])

        try:
            defaults['new_version'] = v.serialize()
        except MissingValueForSerializationException as e:
            logger.info("Opportunistic finding of new_version failed: " + e.message)
        except IncompleteVersionRepresenationException as e:
            logger.info("Opportunistic finding of new_version failed: " + e.message)
        except KeyError as e:
            logger.info("Opportunistic finding of new_version failed")

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

    taggroup.add_argument('--tag', action='store_true', dest="tag", default=defaults.get("tag", False),
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
                         nargs='*',
                         help='Files to change', default=files)

    args = parser3.parse_args(remaining_argv + positionals)

    if args.dry_run:
        logger.info("Dry run active, won't touch any files.")

    logger.info("New version will be '{}'".format(args.new_version))

    files = files or positionals[1:]


    for vcs in VCS:
        if vcs.is_usable():
            vcs.assert_nondirty()
            break

    # make sure files exist and contain version string

    logger.info("Asserting files {} contain string '{}':".format(", ".join(files), args.current_version))

    for path in files:
        with io.open(path, 'rb') as f:

            found_before = False

            for lineno, line in enumerate(f.readlines()):
                if args.current_version in line.decode('utf-8'):
                    found_before = True
                    logger.info("Found '{}' in {} at line {}: {}".format(args.current_version, path, lineno, line.decode('utf-8').rstrip()))

            assert found_before, 'Did not find string {} in file {}'.format(
                args.current_version, path)

    # change version string in files
    for path in files:
        with io.open(path, 'rb') as f:
            before = f.read().decode('utf-8')

        after = before.replace(args.current_version, args.new_version)

        logger.info("{} file {}:".format(
            "Would change" if args.dry_run else "Changing",
            path,
        ))
        logger.info("\n".join(list(unified_diff(before.splitlines(), after.splitlines(), lineterm="", fromfile="a/"+path, tofile="b/"+path))))

        if not args.dry_run:
            with io.open(path, 'wt', encoding='utf-8') as f:
                f.write(after)

    commit_files = files

    if config:
        config.remove_option('bumpversion', 'new_version')

        config.set('bumpversion', 'current_version', args.new_version)

        s = StringIO()

        try:
            config.write(s)

            logger.info("{} to config file {}:".format(
                "Would write" if args.dry_run else "Writing",
                known_args.config_file,
            ))
            logger.info(log_config.getvalue())

            if not args.dry_run:
                with io.open(known_args.config_file, 'wb') as f:
                    f.write(s.getvalue().encode('utf-8'))

        except UnicodeEncodeError:
            warnings.warn(
                "Unable to write UTF-8 to config file, because of an old configparser version. "
                "Update with `pip install --upgrade configparser`."
            )

        commit_files.append(known_args.config_file)

    if args.commit:

        assert vcs.is_usable(), "Did find '{}' unusable, unable to commit.".format(vcs.__name__)

        logger.info("Preparing {} commit".format(vcs.__name__))

        for path in commit_files:

            logger.info("{} changes in file '{}' to {}".format(
                "Would add" if args.dry_run else "Adding",
                path,
                vcs.__name__,
            ))

            if not args.dry_run:
                vcs.add_path(path)

        vcs_context = {
            "current_version": args.current_version,
            "new_version": args.new_version,
        }
        vcs_context.update(time_context)
        vcs_context.update(prefixed_environ())

        commit_message = args.message.format(**vcs_context)

        logger.info("{} to {} with message '{}'".format(
            "Would commit" if args.dry_run else "Committing",
            vcs.__name__,
            commit_message,
        ))

        if not args.dry_run:
            vcs.commit(message=commit_message)

        if args.tag:
            tag_name = args.tag_name.format(**vcs_context)
            logger.info("{} '{}' in {}".format(
                "Would tag" if args.dry_run else "Tagging",
                tag_name,
                vcs.__name__
            ))

            if not args.dry_run:
                vcs.tag(tag_name)

