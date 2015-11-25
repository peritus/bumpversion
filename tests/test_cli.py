# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest
import sys
import logging
import mock

import argparse
import subprocess
from os import curdir, makedirs, chdir, environ
from os.path import join, curdir, dirname
from shlex import split as shlex_split
from textwrap import dedent
from functools import partial

import bumpversion

from bumpversion import main, DESCRIPTION, WorkingDirectoryIsDirtyException, \
    split_args_in_optional_and_positional

SUBPROCESS_ENV = dict(
    list(environ.items()) + [(b'HGENCODING', b'utf-8')]
)

call = partial(subprocess.call, env=SUBPROCESS_ENV)
check_call = partial(subprocess.check_call, env=SUBPROCESS_ENV)
check_output = partial(subprocess.check_output,  env=SUBPROCESS_ENV)

xfail_if_no_git = pytest.mark.xfail(
  call(["git", "help"]) != 0,
  reason="git is not installed"
)

xfail_if_no_hg = pytest.mark.xfail(
  call(["hg", "help"]) != 0,
  reason="hg is not installed"
)

@pytest.fixture(params=['.bumpversion.cfg', 'setup.cfg'])
def configfile(request):
    return request.param


try:
    bumpversion.RawConfigParser(empty_lines_in_values=False)
    using_old_configparser = False
except TypeError:
    using_old_configparser = True

xfail_if_old_configparser = pytest.mark.xfail(
  using_old_configparser,
  reason="configparser doesn't support empty_lines_in_values"
)

def _mock_calls_to_string(called_mock):
    return ["{}|{}|{}".format(
        name,
        args[0] if len(args) > 0  else args,
        repr(kwargs) if len(kwargs) > 0 else ""
    ) for name, args, kwargs in called_mock.mock_calls]



EXPECTED_OPTIONS = """
[-h]
[--config-file FILE]
[--verbose]
[--list]
[--allow-dirty]
[--parse REGEX]
[--serialize FORMAT]
[--search SEARCH]
[--replace REPLACE]
[--current-version VERSION]
[--dry-run]
--new-version VERSION
[--commit | --no-commit]
[--tag | --no-tag]
[--tag-name TAG_NAME]
[--tag-message TAG_MESSAGE]
[--message COMMIT_MSG]
part
[file [file ...]]
""".strip().splitlines()

EXPECTED_USAGE = ("""

%s

positional arguments:
  part                  Part of the version to be bumped.
  file                  Files to change (default: [])

optional arguments:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --verbose             Print verbose logging to stderr (default: 0)
  --list                List machine readable information (default: False)
  --allow-dirty         Don't abort if working directory is dirty (default:
                        False)
  --parse REGEX         Regex parsing the version string (default:
                        (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))
  --serialize FORMAT    How to format what is parsed back to a version
                        (default: ['{major}.{minor}.{patch}'])
  --search SEARCH       Template for complete string to search (default:
                        {current_version})
  --replace REPLACE     Template for complete string to replace (default:
                        {new_version})
  --current-version VERSION
                        Version that needs to be updated (default: None)
  --dry-run, -n         Don't write any files, just pretend. (default: False)
  --new-version VERSION
                        New version that should be in the files (default:
                        None)
  --commit              Commit to version control (default: False)
  --no-commit           Do not commit to version control
  --tag                 Create a tag in version control (default: False)
  --no-tag              Do not create a tag in version control
  --tag-name TAG_NAME   Tag name (only works with --tag) (default:
                        v{new_version})
  --tag-message TAG_MESSAGE
                        Tag message (default: Bump version: {current_version}
                        → {new_version})
  --message COMMIT_MSG, -m COMMIT_MSG
                        Commit message (default: Bump version:
                        {current_version} → {new_version})
""" % DESCRIPTION).lstrip()


def test_usage_string(tmpdir, capsys):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    assert err == ""

    for option_line in EXPECTED_OPTIONS:
        assert option_line in out, "Usage string is missing {}".format(option_line)

    assert EXPECTED_USAGE in out

def test_usage_string_fork(tmpdir, capsys):
    tmpdir.chdir()

    try:
        out = check_output('bumpversion --help', shell=True, stderr=subprocess.STDOUT).decode('utf-8')
    except subprocess.CalledProcessError as e:
        out = e.output

    if not 'usage: bumpversion [-h]' in out:
        print(out)

    assert 'usage: bumpversion [-h]' in out

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_regression_help_in_workdir(tmpdir, capsys, vcs):
    tmpdir.chdir()
    tmpdir.join("somesource.txt").write("1.7.2013")
    check_call([vcs, "init"])
    check_call([vcs, "add", "somesource.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])
    check_call([vcs, "tag", "v1.7.2013"])

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()

    for option_line in EXPECTED_OPTIONS:
        assert option_line in out, "Usage string is missing {}".format(option_line)

    if vcs == "git":
        assert "Version that needs to be updated (default: 1.7.2013)" in out
    else:
        assert EXPECTED_USAGE in out


def test_defaults_in_usage_with_config(tmpdir, capsys):
    tmpdir.chdir()
    tmpdir.join("mydefaults.cfg").write("""[bumpversion]
current_version: 18
new_version: 19
files: file1 file2 file3""")
    with pytest.raises(SystemExit):
        main(['--config-file', 'mydefaults.cfg', '--help'])

    out, err = capsys.readouterr()

    assert "Version that needs to be updated (default: 18)" in out
    assert "New version that should be in the files (default: 19)" in out
    assert "[--current-version VERSION]" in out
    assert "[--new-version VERSION]" in out
    assert "[file [file ...]]" in out


def test_missing_explicit_config_file(tmpdir):
    tmpdir.chdir()
    with pytest.raises(argparse.ArgumentTypeError):
        main(['--config-file', 'missing.cfg'])


def test_simple_replacement(tmpdir):
    tmpdir.join("VERSION").write("1.2.0")
    tmpdir.chdir()
    main(shlex_split("patch --current-version 1.2.0 --new-version 1.2.1 VERSION"))
    assert "1.2.1" == tmpdir.join("VERSION").read()


def test_simple_replacement_in_utf8_file(tmpdir):
    tmpdir.join("VERSION").write("Kröt1.3.0".encode('utf-8'), 'wb')
    tmpdir.chdir()
    main(shlex_split("patch --current-version 1.3.0 --new-version 1.3.1 VERSION"))
    out = tmpdir.join("VERSION").read('rb')
    assert "'Kr\\xc3\\xb6t1.3.1'" in repr(out)


def test_config_file(tmpdir):
    tmpdir.join("file1").write("0.9.34")
    tmpdir.join("mybumpconfig.cfg").write("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
files: file1""")

    tmpdir.chdir()
    main(shlex_split("patch --config-file mybumpconfig.cfg"))

    assert "0.9.35" == tmpdir.join("file1").read()


def test_default_config_files(tmpdir, configfile):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join(configfile).write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
files: file2""")

    tmpdir.chdir()
    main(['patch'])

    assert "0.10.3" == tmpdir.join("file2").read()


def test_multiple_config_files(tmpdir):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join("setup.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
files: file2""")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.4
files: file2""")

    tmpdir.chdir()
    main(['patch'])

    assert "0.10.4" == tmpdir.join("file2").read()


def test_config_file_is_updated(tmpdir):
    tmpdir.join("file3").write("0.0.13")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 0.0.13
new_version: 0.0.14
files: file3
""")

    tmpdir.chdir()
    main(['patch', '--verbose'])

    assert """[bumpversion]
current_version = 0.0.14
files = file3

""" == tmpdir.join(".bumpversion.cfg").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_dry_run(tmpdir, vcs):
    tmpdir.chdir()

    config = """[bumpversion]
current_version = 0.12.0
files = file4
tag = True
commit = True
message = DO NOT BUMP VERSIONS WITH THIS FILE
"""

    version = "0.12.0"

    tmpdir.join("file4").write(version)
    tmpdir.join(".bumpversion.cfg").write(config)

    check_call([vcs, "init"])
    check_call([vcs, "add", "file4"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--dry-run'])

    assert config == tmpdir.join(".bumpversion.cfg").read()
    assert version == tmpdir.join("file4").read()

    vcs_log = check_output([vcs, "log"]).decode('utf-8')

    assert "initial commit" in vcs_log
    assert "DO NOT" not in vcs_log

def test_bump_version(tmpdir):

    tmpdir.join("file5").write("1.0.0")
    tmpdir.chdir()
    main(['patch', '--current-version', '1.0.0', 'file5'])

    assert '1.0.1' == tmpdir.join("file5").read()


def test_bump_version_custom_parse(tmpdir):

    tmpdir.join("file6").write("XXX1;0;0")
    tmpdir.chdir()
    main([
         '--current-version', 'XXX1;0;0',
         '--parse', 'XXX(?P<spam>\d+);(?P<garlg>\d+);(?P<slurp>\d+)',
         '--serialize', 'XXX{spam};{garlg};{slurp}',
         'garlg',
         'file6'
         ])

    assert 'XXX1;1;0' == tmpdir.join("file6").read()

def test_bump_version_custom_parse_serialize_configfile(tmpdir):

    tmpdir.join("file12").write("ZZZ8;0;0")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
files = file12
current_version = ZZZ8;0;0
serialize = ZZZ{spam};{garlg};{slurp}
parse = ZZZ(?P<spam>\d+);(?P<garlg>\d+);(?P<slurp>\d+)
""")

    main(['garlg'])

    assert 'ZZZ8;1;0' == tmpdir.join("file12").read()

def test_bumpversion_custom_parse_semver(tmpdir):
    tmpdir.join("file15").write("XXX1.1.7-master+allan1")
    tmpdir.chdir()
    main([
         '--current-version', '1.1.7-master+allan1',
         '--parse', '(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)(-(?P<prerel>[^\+]+))?(\+(?P<meta>.*))?',
         '--serialize', '{major}.{minor}.{patch}-{prerel}+{meta}',
         'meta',
         'file15'
         ])

    assert 'XXX1.1.7-master+allan2' == tmpdir.join("file15").read()

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_dirty_workdir(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("dirty").write("i'm dirty")

    check_call([vcs, "add", "dirty"])

    with pytest.raises(WorkingDirectoryIsDirtyException):
        with mock.patch("bumpversion.logger") as logger:
            main(['patch', '--current-version', '1', '--new-version', '2', 'file7'])

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    assert 'working directory is not clean' in actual_log
    assert "Use --allow-dirty to override this if you know what you're doing." in actual_log

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_force_dirty_workdir(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("dirty2").write("i'm dirty! 1.1.1")

    check_call([vcs, "add", "dirty2"])

    main([
        'patch',
        '--allow-dirty',
        '--current-version',
        '1.1.1',
        'dirty2'
    ])

    assert "i'm dirty! 1.1.2" == tmpdir.join("dirty2").read()

def test_bump_major(tmpdir):
    tmpdir.join("fileMAJORBUMP").write("4.2.8")
    tmpdir.chdir()
    main(['--current-version', '4.2.8', 'major', 'fileMAJORBUMP'])

    assert '5.0.0' == tmpdir.join("fileMAJORBUMP").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_commit_and_tag(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("47.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '47.1.1', '--commit', 'VERSION'])

    assert '47.1.2' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-47.1.1' in log
    assert '+47.1.2' in log
    assert 'Bump version: 47.1.1 → 47.1.2' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v47.1.2' not in tag_out

    main(['patch', '--current-version', '47.1.2', '--commit', '--tag', 'VERSION'])

    assert '47.1.3' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v47.1.3' in tag_out


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_commit_and_tag_with_configfile(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]\ncommit = True\ntag = True""")

    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("48.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '48.1.1', '--no-tag', 'VERSION'])

    assert '48.1.2' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-48.1.1' in log
    assert '+48.1.2' in log
    assert 'Bump version: 48.1.1 → 48.1.2' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v48.1.2' not in tag_out

    main(['patch', '--current-version', '48.1.2', 'VERSION'])

    assert '48.1.3' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v48.1.3' in tag_out


@pytest.mark.parametrize(("vcs,config"), [
    xfail_if_no_git(("git", """[bumpversion]\ncommit = True""")),
    xfail_if_no_hg(("hg",  """[bumpversion]\ncommit = True""")),
    xfail_if_no_git(("git", """[bumpversion]\ncommit = True\ntag = False""")),
    xfail_if_no_hg(("hg",  """[bumpversion]\ncommit = True\ntag = False""")),
])
def test_commit_and_not_tag_with_configfile(tmpdir, vcs, config):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(config)

    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("48.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '48.1.1', 'VERSION'])

    assert '48.1.2' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-48.1.1' in log
    assert '+48.1.2' in log
    assert 'Bump version: 48.1.1 → 48.1.2' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v48.1.2' not in tag_out


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_commit_explicitly_false(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 10.0.0
commit = False
tag = False""")

    check_call([vcs, "init"])
    tmpdir.join("trackedfile").write("10.0.0")
    check_call([vcs, "add", "trackedfile"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', 'trackedfile'])

    assert '10.0.1' == tmpdir.join("trackedfile").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "10.0.1" not in log

    diff = check_output([vcs, "diff"]).decode("utf-8")
    assert "10.0.1" in diff


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_commit_configfile_true_cli_false_override(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 27.0.0
commit = True""")

    check_call([vcs, "init"])
    tmpdir.join("dontcommitfile").write("27.0.0")
    check_call([vcs, "add", "dontcommitfile"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--no-commit', 'dontcommitfile'])

    assert '27.0.1' == tmpdir.join("dontcommitfile").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "27.0.1" not in log

    diff = check_output([vcs, "diff"]).decode("utf-8")
    assert "27.0.1" in diff


def test_bump_version_ENV(tmpdir):

    tmpdir.join("on_jenkins").write("2.3.4")
    tmpdir.chdir()
    environ['BUILD_NUMBER'] = "567"
    main([
         '--verbose',
         '--current-version', '2.3.4',
         '--parse', '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*',
         '--serialize', '{major}.{minor}.{patch}.pre{$BUILD_NUMBER}',
         'patch',
         'on_jenkins',
         ])
    del environ['BUILD_NUMBER']

    assert '2.3.5.pre567' == tmpdir.join("on_jenkins").read()

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_current_version_from_tag(tmpdir, vcs):
    # prepare
    tmpdir.join("update_from_tag").write("26.6.0")
    tmpdir.chdir()
    check_call(["git", "init"])
    check_call(["git", "add", "update_from_tag"])
    check_call(["git", "commit", "-m", "initial"])
    check_call(["git", "tag", "v26.6.0"])

    # don't give current-version, that should come from tag
    main(['patch', 'update_from_tag'])

    assert '26.6.1' == tmpdir.join("update_from_tag").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_current_version_from_tag_written_to_config_file(tmpdir, vcs):
    # prepare
    tmpdir.join("updated_also_in_config_file").write("14.6.0")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]""")

    check_call(["git", "init"])
    check_call(["git", "add", "updated_also_in_config_file"])
    check_call(["git", "commit", "-m", "initial"])
    check_call(["git", "tag", "v14.6.0"])

    # don't give current-version, that should come from tag
    main([
        'patch',
        'updated_also_in_config_file',
         '--commit',
         '--tag',
         ])

    assert '14.6.1' == tmpdir.join("updated_also_in_config_file").read()
    assert '14.6.1' in tmpdir.join(".bumpversion.cfg").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_distance_to_latest_tag_as_part_of_new_version(tmpdir, vcs):
    # prepare
    tmpdir.join("mysourcefile").write("19.6.0")
    tmpdir.chdir()

    check_call(["git", "init"])
    check_call(["git", "add", "mysourcefile"])
    check_call(["git", "commit", "-m", "initial"])
    check_call(["git", "tag", "v19.6.0"])
    check_call(["git", "commit", "--allow-empty", "-m", "Just a commit 1"])
    check_call(["git", "commit", "--allow-empty", "-m", "Just a commit 2"])
    check_call(["git", "commit", "--allow-empty", "-m", "Just a commit 3"])

    # don't give current-version, that should come from tag
    main([
         'patch',
         '--parse', '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*',
         '--serialize', '{major}.{minor}.{patch}-pre{distance_to_latest_tag}',
         'mysourcefile',
         ])

    assert '19.6.1-pre3' == tmpdir.join("mysourcefile").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_override_vcs_current_version(tmpdir, vcs):
    # prepare
    tmpdir.join("contains_actual_version").write("6.7.8")
    tmpdir.chdir()
    check_call(["git", "init"])
    check_call(["git", "add", "contains_actual_version"])
    check_call(["git", "commit", "-m", "initial"])
    check_call(["git", "tag", "v6.7.8"])

    # update file
    tmpdir.join("contains_actual_version").write("7.0.0")
    check_call(["git", "add", "contains_actual_version"])

    # but forgot to tag or forgot to push --tags
    check_call(["git", "commit", "-m", "major release"])

    # if we don't give current-version here we get
    # "AssertionError: Did not find string 6.7.8 in file contains_actual_version"
    main(['patch', '--current-version', '7.0.0', 'contains_actual_version'])

    assert '7.0.1' == tmpdir.join("contains_actual_version").read()


def test_nonexisting_file(tmpdir):
    tmpdir.chdir()
    with pytest.raises(IOError):
        main(shlex_split("patch --current-version 1.2.0 --new-version 1.2.1 doesnotexist.txt"))


def test_nonexisting_file(tmpdir):
    tmpdir.chdir()
    tmpdir.join("mysourcecode.txt").write("1.2.3")
    with pytest.raises(IOError):
        main(shlex_split("patch --current-version 1.2.3 mysourcecode.txt doesnotexist2.txt"))

    # first file is unchanged because second didn't exist
    assert '1.2.3' == tmpdir.join("mysourcecode.txt").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_read_version_tags_only(tmpdir, vcs):
    # prepare
    tmpdir.join("update_from_tag").write("29.6.0")
    tmpdir.chdir()
    check_call(["git", "init"])
    check_call(["git", "add", "update_from_tag"])
    check_call(["git", "commit", "-m", "initial"])
    check_call(["git", "tag", "v29.6.0"])
    check_call(["git", "commit", "--allow-empty", "-m", "a commit"])
    check_call(["git", "tag", "jenkins-deploy-myproject-2"])

    # don't give current-version, that should come from tag
    main(['patch', 'update_from_tag'])

    assert '29.6.1' == tmpdir.join("update_from_tag").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_tag_name(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("31.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '31.1.1', '--commit', '--tag', 'VERSION', '--tag-name', 'ReleasedVersion-{new_version}'])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'ReleasedVersion-31.1.2' in tag_out


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_message_from_config_file(tmpdir, capsys, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("400.0.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 400.0.0
new_version: 401.0.0
commit: True
tag: True
message: {current_version} was old, {new_version} is new
tag_name: from-{current_version}-to-{new_version}""")

    main(['major', 'VERSION'])

    log = check_output([vcs, "log", "-p"])

    assert b'400.0.0 was old, 401.0.0 is new' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'from-400.0.0-to-401.0.0' in tag_out


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_unannotated_tag(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("42.3.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '42.3.1', '--commit', '--tag', 'VERSION', '--tag-name', 'ReleasedVersion-{new_version}', '--tag-message', ''])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b'ReleasedVersion-42.3.2' in tag_out

    if vcs == "git":
        describe_out = subprocess.call([vcs, "describe"])
        assert 128 == describe_out

        describe_out = subprocess.check_output([vcs, "describe", "--tags"])
        assert describe_out.startswith(b'ReleasedVersion-42.3.2')


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_annotated_tag(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("42.4.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '42.4.1', '--commit', '--tag', 'VERSION', '--tag-message', 'test {new_version}-tag'])
    assert '42.4.2' == tmpdir.join("VERSION").read()

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b'v42.4.2' in tag_out

    if vcs == "git":
        describe_out = subprocess.check_output([vcs, "describe"])
        assert describe_out == b'v42.4.2\n'

        describe_out = subprocess.check_output([vcs, "show", "v42.4.2"])
        assert describe_out.startswith(b"tag v42.4.2\n")
        assert b'test 42.4.2-tag' in describe_out
    elif vcs == "hg":
        describe_out = subprocess.check_output([vcs, "log"])
        assert b'test 42.4.2-tag' in describe_out
    else:
        raise ValueError("Unknown VCS")


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_vcs_describe(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("42.5.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '42.5.1', '--commit', '--tag', 'VERSION', '--tag-message', 'test {new_version}-tag'])
    assert '42.5.2' == tmpdir.join("VERSION").read()

    describe_out = subprocess.check_output([vcs, "describe"])
    assert b'v42.5.2\n' == describe_out

    main(['patch', '--current-version', '42.5.2', '--commit', '--tag', 'VERSION', '--tag-name', 'ReleasedVersion-{new_version}', '--tag-message', ''])
    assert '42.5.3' == tmpdir.join("VERSION").read()

    describe_only_annotated_out = subprocess.check_output([vcs, "describe"])
    assert describe_only_annotated_out.startswith(b'v42.5.2-1-g')

    describe_all_out = subprocess.check_output([vcs, "describe", "--tags"])
    assert b'ReleasedVersion-42.5.3\n' == describe_all_out


config_parser_handles_utf8 = True
try:
    import configparser
except ImportError:
    config_parser_handles_utf8 = False


@pytest.mark.xfail(not config_parser_handles_utf8,
                   reason="old ConfigParser uses non-utf-8-strings internally")
@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_utf8_message_from_config_file(tmpdir, capsys, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("500.0.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    initial_config = """[bumpversion]
current_version = 500.0.0
commit = True
message = Nová verze: {current_version} ☃, {new_version} ☀

"""

    tmpdir.join(".bumpversion.cfg").write(initial_config.encode('utf-8'), mode='wb')
    main(['major', 'VERSION'])
    log = check_output([vcs, "log", "-p"])
    expected_new_config = initial_config.replace('500', '501')
    assert expected_new_config.encode('utf-8') == tmpdir.join(".bumpversion.cfg").read(mode='rb')


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_utf8_message_from_config_file(tmpdir, capsys, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("10.10.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    initial_config = """[bumpversion]
current_version = 10.10.0
commit = True
message = [{now}] [{utcnow} {utcnow:%YXX%mYY%d}]

"""
    tmpdir.join(".bumpversion.cfg").write(initial_config)

    main(['major', 'VERSION'])

    log = check_output([vcs, "log", "-p"])

    assert b'[20' in log
    assert b'] [' in log
    assert b'XX' in log
    assert b'YY' in log

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_commit_and_tag_from_below_vcs_root(tmpdir, vcs, monkeypatch):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("30.0.3")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    tmpdir.mkdir("subdir")
    monkeypatch.chdir(tmpdir.join("subdir"))

    main(['major', '--current-version', '30.0.3', '--commit', '../VERSION'])

    assert '31.0.0' == tmpdir.join("VERSION").read()

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_non_vcs_operations_if_vcs_is_not_installed(tmpdir, vcs, monkeypatch):

    monkeypatch.setenv("PATH", "")

    tmpdir.chdir()
    tmpdir.join("VERSION").write("31.0.3")

    main(['major', '--current-version', '31.0.3', 'VERSION'])

    assert '32.0.0' == tmpdir.join("VERSION").read()

def test_multiple_serialize_threepart(tmpdir):
    tmpdir.join("fileA").write("Version: 0.9")
    tmpdir.chdir()
    main([
         '--current-version', 'Version: 0.9',
         '--parse', 'Version:\ (?P<major>\d+)(\.(?P<minor>\d+)(\.(?P<patch>\d+))?)?',
         '--serialize', 'Version: {major}.{minor}.{patch}',
         '--serialize', 'Version: {major}.{minor}',
         '--serialize', 'Version: {major}',
         '--verbose',
         'major',
         'fileA'
         ])

    assert 'Version: 1' == tmpdir.join("fileA").read()

def test_multiple_serialize_twopart(tmpdir):
    tmpdir.join("fileB").write("0.9")
    tmpdir.chdir()
    main([
         '--current-version', '0.9',
         '--parse', '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?',
         '--serialize', '{major}.{minor}.{patch}',
         '--serialize', '{major}.{minor}',
         'minor',
         'fileB'
         ])

    assert '0.10' == tmpdir.join("fileB").read()

def test_multiple_serialize_twopart_patch(tmpdir):
    tmpdir.join("fileC").write("0.7")
    tmpdir.chdir()
    main([
         '--current-version', '0.7',
         '--parse', '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?',
         '--serialize', '{major}.{minor}.{patch}',
         '--serialize', '{major}.{minor}',
         'patch',
         'fileC'
         ])

    assert '0.7.1' == tmpdir.join("fileC").read()

def test_multiple_serialize_twopart_patch_configfile(tmpdir):
    tmpdir.join("fileD").write("0.6")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
files = fileD
current_version = 0.6
serialize =
  {major}.{minor}.{patch}
  {major}.{minor}
parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
""")

    main(['patch'])

    assert '0.6.1' == tmpdir.join("fileD").read()


def test_log_no_config_file_info_message(tmpdir, capsys):
    tmpdir.chdir()

    tmpdir.join("blargh.txt").write("1.0.0")

    with mock.patch("bumpversion.logger") as logger:
        main(['--verbose', '--verbose', '--current-version', '1.0.0', 'patch', 'blargh.txt'])

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    EXPECTED_LOG = dedent("""
        info|Could not read config file at .bumpversion.cfg|
        info|Parsing version '1.0.0' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=1, minor=0, patch=0|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=1, minor=0, patch=1|
        info|Parsing version '1.0.1' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=1, minor=0, patch=1|
        info|New version will be '1.0.1'|
        info|Asserting files blargh.txt contain the version string:|
        info|Found '1.0.0' in blargh.txt at line 0: 1.0.0|
        info|Changing file blargh.txt:|
        info|--- a/blargh.txt
        +++ b/blargh.txt
        @@ -1 +1 @@
        -1.0.0
        +1.0.1|
        info|Would write to config file .bumpversion.cfg:|
        info|[bumpversion]
        current_version = 1.0.1

        |
    """).strip()

    assert actual_log == EXPECTED_LOG

def test_log_parse_doesnt_parse_current_version(tmpdir):
    tmpdir.chdir()

    with mock.patch("bumpversion.logger") as logger:
        main(['--parse', 'xxx', '--current-version', '12', '--new-version', '13', 'patch'])

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    EXPECTED_LOG = dedent("""
        info|Could not read config file at .bumpversion.cfg|
        info|Parsing version '12' using regexp 'xxx'|
        warn|Evaluating 'parse' option: 'xxx' does not parse current version '12'|
        info|Parsing version '13' using regexp 'xxx'|
        warn|Evaluating 'parse' option: 'xxx' does not parse current version '13'|
        info|New version will be '13'|
        info|Asserting files  contain the version string:|
        info|Would write to config file .bumpversion.cfg:|
        info|[bumpversion]
        current_version = 13

        |
    """).strip()

    assert actual_log == EXPECTED_LOG

def test_log_invalid_regex_exit(tmpdir):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        with mock.patch("bumpversion.logger") as logger:
            main(['--parse', '*kittens*', '--current-version', '12', '--new-version', '13', 'patch'])

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    EXPECTED_LOG = dedent("""
        info|Could not read config file at .bumpversion.cfg|
        error|--parse '*kittens*' is not a valid regex|
    """).strip()

    assert actual_log == EXPECTED_LOG

def test_complex_info_logging(tmpdir, capsys):
    tmpdir.join("fileE").write("0.4")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = fileE
        current_version = 0.4
        serialize =
          {major}.{minor}.{patch}
          {major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        """).strip())

    with mock.patch("bumpversion.logger") as logger:
        main(['patch'])

    # beware of the trailing space (" ") after "serialize =":
    EXPECTED_LOG = dedent("""
        info|Reading config file .bumpversion.cfg:|
        info|[bumpversion]
        files = fileE
        current_version = 0.4
        serialize =
          {major}.{minor}.{patch}
          {major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?|
        info|Parsing version '0.4' using regexp '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?'|
        info|Parsed the following values: major=0, minor=4, patch=0|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=0, minor=4, patch=1|
        info|Parsing version '0.4.1' using regexp '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?'|
        info|Parsed the following values: major=0, minor=4, patch=1|
        info|New version will be '0.4.1'|
        info|Asserting files fileE contain the version string:|
        info|Found '0.4' in fileE at line 0: 0.4|
        info|Changing file fileE:|
        info|--- a/fileE
        +++ b/fileE
        @@ -1 +1 @@
        -0.4
        +0.4.1|
        info|Writing to config file .bumpversion.cfg:|
        info|[bumpversion]
        files = fileE
        current_version = 0.4.1
        serialize = 
        	{major}.{minor}.{patch}
        	{major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        
        |
        """).strip()

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    assert actual_log == EXPECTED_LOG


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_subjunctive_dry_run_logging(tmpdir, vcs):
    tmpdir.join("dont_touch_me.txt").write("0.8")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = dont_touch_me.txt
        current_version = 0.8
        commit = True
        tag = True
        serialize =
          {major}.{minor}.{patch}
          {major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?"""
    ).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "dont_touch_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    with mock.patch("bumpversion.logger") as logger:
        main(['patch', '--dry-run'])

    # beware of the trailing space (" ") after "serialize =":
    EXPECTED_LOG = dedent("""
        info|Reading config file .bumpversion.cfg:|
        info|[bumpversion]
        files = dont_touch_me.txt
        current_version = 0.8
        commit = True
        tag = True
        serialize =
          {major}.{minor}.{patch}
          {major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?|
        info|Parsing version '0.8' using regexp '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?'|
        info|Parsed the following values: major=0, minor=8, patch=0|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=0, minor=8, patch=1|
        info|Dry run active, won't touch any files.|
        info|Parsing version '0.8.1' using regexp '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?'|
        info|Parsed the following values: major=0, minor=8, patch=1|
        info|New version will be '0.8.1'|
        info|Asserting files dont_touch_me.txt contain the version string:|
        info|Found '0.8' in dont_touch_me.txt at line 0: 0.8|
        info|Would change file dont_touch_me.txt:|
        info|--- a/dont_touch_me.txt
        +++ b/dont_touch_me.txt
        @@ -1 +1 @@
        -0.8
        +0.8.1|
        info|Would write to config file .bumpversion.cfg:|
        info|[bumpversion]
        files = dont_touch_me.txt
        current_version = 0.8.1
        commit = True
        tag = True
        serialize = 
        	{major}.{minor}.{patch}
        	{major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?

        |
        info|Would prepare Git commit|
        info|Would add changes in file 'dont_touch_me.txt' to Git|
        info|Would add changes in file '.bumpversion.cfg' to Git|
        info|Would commit to Git with message 'Bump version: 0.8 \u2192 0.8.1'|
        info|Would tag 'v0.8.1' with message 'Bump version: 0.8 \u2192 0.8.1' in Git|
        """).strip()

    if vcs == "hg":
        EXPECTED_LOG = EXPECTED_LOG.replace("Git", "Mercurial")

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    assert actual_log == EXPECTED_LOG


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_log_commitmessage_if_no_commit_tag_but_usable_vcs(tmpdir, vcs):
    tmpdir.join("please_touch_me.txt").write("0.3.3")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = please_touch_me.txt
        current_version = 0.3.3
        commit = False
        tag = False
        """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_touch_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    with mock.patch("bumpversion.logger") as logger:
        main(['patch'])

    # beware of the trailing space (" ") after "serialize =":
    EXPECTED_LOG = dedent("""
        info|Reading config file .bumpversion.cfg:|
        info|[bumpversion]
        files = please_touch_me.txt
        current_version = 0.3.3
        commit = False
        tag = False|
        info|Parsing version '0.3.3' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=0, minor=3, patch=3|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=0, minor=3, patch=4|
        info|Parsing version '0.3.4' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=0, minor=3, patch=4|
        info|New version will be '0.3.4'|
        info|Asserting files please_touch_me.txt contain the version string:|
        info|Found '0.3.3' in please_touch_me.txt at line 0: 0.3.3|
        info|Changing file please_touch_me.txt:|
        info|--- a/please_touch_me.txt
        +++ b/please_touch_me.txt
        @@ -1 +1 @@
        -0.3.3
        +0.3.4|
        info|Writing to config file .bumpversion.cfg:|
        info|[bumpversion]
        files = please_touch_me.txt
        current_version = 0.3.4
        commit = False
        tag = False
        
        |
        info|Would prepare Git commit|
        info|Would add changes in file 'please_touch_me.txt' to Git|
        info|Would add changes in file '.bumpversion.cfg' to Git|
        info|Would commit to Git with message 'Bump version: 0.3.3 \u2192 0.3.4'|
        info|Would tag 'v0.3.4' with message 'Bump version: 0.3.3 \u2192 0.3.4' in Git|
        """).strip()

    if vcs == "hg":
        EXPECTED_LOG = EXPECTED_LOG.replace("Git", "Mercurial")

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    assert actual_log == EXPECTED_LOG


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_listing(tmpdir, vcs):
    tmpdir.join("please_list_me.txt").write("0.5.5")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = please_list_me.txt
        current_version = 0.5.5
        commit = False
        tag = False
        """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_list_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    with mock.patch("bumpversion.logger_list") as logger:
        main(['--list', 'patch'])

    EXPECTED_LOG = dedent("""
        info|files=please_list_me.txt|
        info|current_version=0.5.5|
        info|commit=False|
        info|tag=False|
        info|new_version=0.5.6|
        """).strip()

    if vcs == "hg":
        EXPECTED_LOG = EXPECTED_LOG.replace("Git", "Mercurial")

    actual_log ="\n".join(_mock_calls_to_string(logger)[3:])

    assert actual_log == EXPECTED_LOG

@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_no_list_no_stdout(tmpdir, vcs):
    tmpdir.join("please_dont_list_me.txt").write("0.5.5")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = please_dont_list_me.txt
        current_version = 0.5.5
        commit = False
        tag = False
        """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_dont_list_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    out = check_output(
        'bumpversion patch; exit 0',
        shell=True,
        stderr=subprocess.STDOUT
    ).decode('utf-8')

    assert out == ""

def test_bump_non_numeric_parts(tmpdir, capsys):
    tmpdir.join("with_prereleases.txt").write("1.5.dev")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = with_prereleases.txt
        current_version = 1.5.dev
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<release>[a-z]+))?
        serialize =
          {major}.{minor}.{release}
          {major}.{minor}

        [bumpversion:part:release]
        optional_value = gamma
        values =
          dev
          gamma
        """).strip())

    main(['release', '--verbose'])

    assert '1.5' == tmpdir.join("with_prereleases.txt").read()

    main(['minor', '--verbose'])

    assert '1.6.dev' == tmpdir.join("with_prereleases.txt").read()

def test_optional_value_from_documentation(tmpdir):

    tmpdir.join("optional_value_fromdoc.txt").write("1.alpha")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
      [bumpversion]
      current_version = 1.alpha
      parse = (?P<num>\d+)(\.(?P<release>.*))?(\.)?
      serialize =
        {num}.{release}
        {num}
  
      [bumpversion:part:release]
      optional_value = gamma
      values =
        alpha
        beta
        gamma

      [bumpversion:file:optional_value_fromdoc.txt]
      """).strip())

    main(['release', '--verbose'])

    assert '1.beta' == tmpdir.join("optional_value_fromdoc.txt").read()

    main(['release', '--verbose'])

    assert '1' == tmpdir.join("optional_value_fromdoc.txt").read()

def test_python_prerelease_release_postrelease(tmpdir, capsys):
    tmpdir.join("python386.txt").write("1.0a")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = python386.txt
        current_version = 1.0a

        # adapted from http://legacy.python.org/dev/peps/pep-0386/#the-new-versioning-algorithm
        parse = ^
            (?P<major>\d+)\.(?P<minor>\d+)   # minimum 'N.N'
            (?:
                (?P<prerel>[abc]|rc|dev)     # 'a' = alpha, 'b' = beta
                                             # 'c' or 'rc' = release candidate
                (?:
                    (?P<prerelversion>\d+(?:\.\d+)*)
                )?
            )?
            (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?

        serialize =
          {major}.{minor}{prerel}{prerelversion}
          {major}.{minor}{prerel}
          {major}.{minor}

        [bumpversion:part:prerel]
        optional_value = d
        values =
          dev
          a
          b
          c
          rc
          d
        """))

    def file_content():
        return tmpdir.join("python386.txt").read()

    main(['prerel'])
    assert '1.0b' == file_content()

    main(['prerelversion'])
    assert '1.0b1' == file_content()

    main(['prerelversion'])
    assert '1.0b2' == file_content()

    main(['prerel']) # now it's 1.0c
    main(['prerel'])
    assert '1.0rc' == file_content()

    main(['prerel'])
    assert '1.0' == file_content()

    main(['minor'])
    assert '1.1dev' == file_content()

    main(['prerel', '--verbose'])
    assert '1.1a' == file_content()

def test_part_first_value(tmpdir):

    tmpdir.join("the_version.txt").write("0.9.4")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = the_version.txt
        current_version = 0.9.4

        [bumpversion:part:minor]
        first_value = 1
        """))

    main(['major', '--verbose'])

    assert '1.1.0' == tmpdir.join("the_version.txt").read()

def test_multi_file_configuration(tmpdir, capsys):
    tmpdir.join("FULL_VERSION.txt").write("1.0.3")
    tmpdir.join("MAJOR_VERSION.txt").write("1")

    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 1.0.3

        [bumpversion:file:FULL_VERSION.txt]

        [bumpversion:file:MAJOR_VERSION.txt]
        serialize = {major}
        parse = \d+

        """))

    main(['major', '--verbose'])
    assert '2.0.0' in tmpdir.join("FULL_VERSION.txt").read()
    assert '2' in tmpdir.join("MAJOR_VERSION.txt").read()

    main(['patch'])
    assert '2.0.1' in tmpdir.join("FULL_VERSION.txt").read()
    assert '2' in tmpdir.join("MAJOR_VERSION.txt").read()


def test_multi_file_configuration2(tmpdir, capsys):
    tmpdir.join("setup.cfg").write("1.6.6")
    tmpdir.join("README.txt").write("MyAwesomeSoftware(TM) v1.6")
    tmpdir.join("BUILDNUMBER").write("1.6.6+joe+38943")

    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
      [bumpversion]
      current_version = 1.6.6

      [something:else]

      [foo]

      [bumpversion:file:setup.cfg]

      [bumpversion:file:README.txt]
      parse = '(?P<major>\d+)\.(?P<minor>\d+)'
      serialize =
        {major}.{minor}

      [bumpversion:file:BUILDNUMBER]
      serialize =
        {major}.{minor}.{patch}+{$USER}+{$BUILDNUMBER}

      """))

    environ['BUILDNUMBER'] = "38944"
    environ['USER'] = "bob"
    main(['minor', '--verbose'])
    del environ['BUILDNUMBER']
    del environ['USER']

    assert '1.7.0' in tmpdir.join("setup.cfg").read()
    assert 'MyAwesomeSoftware(TM) v1.7' in tmpdir.join("README.txt").read()
    assert '1.7.0+bob+38944' in tmpdir.join("BUILDNUMBER").read()

    environ['BUILDNUMBER'] = "38945"
    environ['USER'] = "bob"
    main(['patch', '--verbose'])
    del environ['BUILDNUMBER']
    del environ['USER']

    assert '1.7.1' in tmpdir.join("setup.cfg").read()
    assert 'MyAwesomeSoftware(TM) v1.7' in tmpdir.join("README.txt").read()
    assert '1.7.1+bob+38945' in tmpdir.join("BUILDNUMBER").read()


def test_search_replace_to_avoid_updating_unconcerned_lines(tmpdir, capsys):
    tmpdir.chdir()

    tmpdir.join("requirements.txt").write("Django>=1.5.6,<1.6\nMyProject==1.5.6")

    tmpdir.join(".bumpversion.cfg").write(dedent("""
      [bumpversion]
      current_version = 1.5.6

      [bumpversion:file:requirements.txt]
      search = MyProject=={current_version}
      replace = MyProject=={new_version}
      """).strip())

    with mock.patch("bumpversion.logger") as logger:
        main(['minor', '--verbose'])

    # beware of the trailing space (" ") after "serialize =":
    EXPECTED_LOG = dedent("""
        info|Reading config file .bumpversion.cfg:|
        info|[bumpversion]
        current_version = 1.5.6

        [bumpversion:file:requirements.txt]
        search = MyProject=={current_version}
        replace = MyProject=={new_version}|
        info|Parsing version '1.5.6' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=1, minor=5, patch=6|
        info|Attempting to increment part 'minor'|
        info|Values are now: major=1, minor=6, patch=0|
        info|Parsing version '1.6.0' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=1, minor=6, patch=0|
        info|New version will be '1.6.0'|
        info|Asserting files requirements.txt contain the version string:|
        info|Found 'MyProject==1.5.6' in requirements.txt at line 1: MyProject==1.5.6|
        info|Changing file requirements.txt:|
        info|--- a/requirements.txt
        +++ b/requirements.txt
        @@ -1,2 +1,2 @@
         Django>=1.5.6,<1.6
        -MyProject==1.5.6
        +MyProject==1.6.0|
        info|Writing to config file .bumpversion.cfg:|
        info|[bumpversion]
        current_version = 1.6.0

        [bumpversion:file:requirements.txt]
        search = MyProject=={current_version}
        replace = MyProject=={new_version}

        |
        """).strip()

    actual_log ="\n".join(_mock_calls_to_string(logger)[4:])

    assert actual_log == EXPECTED_LOG

    assert 'MyProject==1.6.0' in tmpdir.join("requirements.txt").read()
    assert 'Django>=1.5.6' in tmpdir.join("requirements.txt").read()


def test_search_replace_expanding_changelog(tmpdir, capsys):

    tmpdir.chdir()

    tmpdir.join("CHANGELOG.md").write(dedent("""
    My awesome software project Changelog
    =====================================

    Unreleased
    ----------

    * Some nice feature
    * Some other nice feature

    Version v8.1.1 (2014-05-28)
    ---------------------------

    * Another old nice feature

    """))
    
    config_content = dedent("""
      [bumpversion]
      current_version = 8.1.1

      [bumpversion:file:CHANGELOG.md]
      search =
        Unreleased
        ----------
      replace =
        Unreleased
        ----------
        Version v{new_version} ({now:%Y-%m-%d})
        ---------------------------
    """)

    tmpdir.join(".bumpversion.cfg").write(config_content)

    with mock.patch("bumpversion.logger") as logger:
        main(['minor', '--verbose'])

    predate = dedent('''
      Unreleased
      ----------
      Version v8.2.0 (20
      ''').strip()

    postdate = dedent('''
      )
      ---------------------------

      * Some nice feature
      * Some other nice feature
      ''').strip()

    assert predate in tmpdir.join("CHANGELOG.md").read()
    assert postdate in tmpdir.join("CHANGELOG.md").read()

def test_search_replace_cli(tmpdir, capsys):
    tmpdir.join("file89").write("My birthday: 3.5.98\nCurrent version: 3.5.98")
    tmpdir.chdir()
    main([
         '--current-version', '3.5.98',
         '--search', 'Current version: {current_version}',
         '--replace', 'Current version: {new_version}',
         'minor',
         'file89',
         ])

    assert 'My birthday: 3.5.98\nCurrent version: 3.6.0' == tmpdir.join("file89").read()

import warnings

def test_deprecation_warning_files_in_global_configuration(tmpdir):
    tmpdir.chdir()

    tmpdir.join("fileX").write("3.2.1")
    tmpdir.join("fileY").write("3.2.1")
    tmpdir.join("fileZ").write("3.2.1")

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version = 3.2.1
files = fileX fileY fileZ
""")

    bumpversion.__warningregistry__.clear()
    warnings.resetwarnings()
    warnings.simplefilter('always')
    with warnings.catch_warnings(record=True) as recwarn:
        main(['patch'])

    w = recwarn.pop()
    assert issubclass(w.category, PendingDeprecationWarning)
    assert "'files =' configuration is will be deprecated, please use" in str(w.message)


def test_deprecation_warning_multiple_files_cli(tmpdir):
    tmpdir.chdir()

    tmpdir.join("fileA").write("1.2.3")
    tmpdir.join("fileB").write("1.2.3")
    tmpdir.join("fileC").write("1.2.3")

    bumpversion.__warningregistry__.clear()
    warnings.resetwarnings()
    warnings.simplefilter('always')
    with warnings.catch_warnings(record=True) as recwarn:
        main(['--current-version', '1.2.3', 'patch', 'fileA', 'fileB', 'fileC'])

    w = recwarn.pop()
    assert issubclass(w.category, PendingDeprecationWarning)
    assert 'Giving multiple files on the command line will be deprecated' in str(w.message)


def test_file_specific_config_inherits_parse_serialize(tmpdir):

    tmpdir.chdir()

    tmpdir.join("todays_icecream").write("14-chocolate")
    tmpdir.join("todays_cake").write("14-chocolate")

    tmpdir.join(".bumpversion.cfg").write(dedent("""
      [bumpversion]
      current_version = 14-chocolate
      parse = (?P<major>\d+)(\-(?P<flavor>[a-z]+))?
      serialize = 
      	{major}-{flavor}
      	{major}

      [bumpversion:file:todays_icecream]
      serialize = 
      	{major}-{flavor}

      [bumpversion:file:todays_cake]

      [bumpversion:part:flavor]
      values = 
      	vanilla
      	chocolate
      	strawberry
      """))

    main(['flavor'])

    assert '14-strawberry' == tmpdir.join("todays_cake").read()
    assert '14-strawberry' == tmpdir.join("todays_icecream").read()

    main(['major'])

    assert '15-vanilla' == tmpdir.join("todays_icecream").read()
    assert '15' == tmpdir.join("todays_cake").read()


def test_multiline_search_is_found(tmpdir):

    tmpdir.chdir()

    tmpdir.join("the_alphabet.txt").write(dedent("""
      A
      B
      C
    """))

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 9.8.7

    [bumpversion:file:the_alphabet.txt]
    search =
      A
      B
      C
    replace =
      A
      B
      C
      {new_version}
      """).strip())

    main(['major'])

    assert dedent("""
      A
      B
      C
      10.0.0
    """) == tmpdir.join("the_alphabet.txt").read()

@xfail_if_old_configparser
def test_configparser_empty_lines_in_values(tmpdir):

    tmpdir.chdir()

    tmpdir.join("CHANGES.rst").write(dedent("""
    My changelog
    ============

    current
    -------

    """))

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 0.4.1

    [bumpversion:file:CHANGES.rst]
    search =
      current
      -------
    replace = current
      -------


      {new_version}
      -------
      """).strip())

    main(['patch'])
    assert dedent("""
      My changelog
      ============
      current
      -------


      0.4.2
      -------

    """) == tmpdir.join("CHANGES.rst").read()



@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git")])
def test_regression_tag_name_with_hyphens(tmpdir, capsys, vcs):
    tmpdir.chdir()
    tmpdir.join("somesource.txt").write("2014.10.22")
    check_call([vcs, "init"])
    check_call([vcs, "add", "somesource.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])
    check_call([vcs, "tag", "very-unrelated-but-containing-lots-of-hyphens"])

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 2014.10.22
    """))

    main(['patch', 'somesource.txt'])

def test_regression_characters_after_last_label_serialize_string(tmpdir, capsys):
    tmpdir.chdir()
    tmpdir.join("bower.json").write('''
    {
      "version": "1.0.0",
      "dependency1": "1.0.0",
    }
    ''')

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 1.0.0

    [bumpversion:file:bower.json]
    parse = "version": "(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    serialize = "version": "{major}.{minor}.{patch}"
    """))

    main(['patch', 'bower.json'])

def test_regression_dont_touch_capitalization_of_keys_in_config(tmpdir, capsys):

    tmpdir.chdir()
    tmpdir.join("setup.cfg").write(dedent("""
    [bumpversion]
    current_version = 0.1.0

    [other]
    DJANGO_SETTINGS = Value
    """))

    main(['patch'])

    assert dedent("""
    [bumpversion]
    current_version = 0.1.1

    [other]
    DJANGO_SETTINGS = Value
    """).strip() == tmpdir.join("setup.cfg").read().strip()

def test_regression_new_version_cli_in_files(tmpdir, capsys):
    '''
    Reported here: https://github.com/peritus/bumpversion/issues/60
    '''
    tmpdir.chdir()
    tmpdir.join("myp___init__.py").write("__version__ = '0.7.2'")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 0.7.2
        files = myp___init__.py
        message = v{new_version}
        tag_name = {new_version}
        tag = true
        commit = true
        """).strip())

    main("patch --allow-dirty --verbose --new-version 0.9.3".split(" "))

    assert "__version__ = '0.9.3'" == tmpdir.join("myp___init__.py").read()
    assert "current_version = 0.9.3" in tmpdir.join(".bumpversion.cfg").read()


class TestSplitArgsInOptionalAndPositional:
    def test_all_optional(self):
        params = ['--allow-dirty', '--verbose', '-n', '--tag-name', '"Tag"']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == []
        assert optional == params

    def test_all_positional(self):
        params = ['minor', 'setup.py']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == params
        assert optional == []

    def test_no_args(self):
        assert split_args_in_optional_and_positional([]) == \
            ([], [])

    def test_short_optionals(self):
        params = ['-m', '"Commit"', '-n']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == []
        assert optional == params

    def test_1optional_2positional(self):
        params = ['-n', 'major', 'setup.py']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == ['major', 'setup.py']
        assert optional == ['-n']

    def test_2optional_1positional(self):
        params = ['-n', '-m', '"Commit"', 'major']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == ['major']
        assert optional == ['-n', '-m', '"Commit"']

    def test_2optional_mixed_2positionl(self):
        params = ['--allow-dirty', '-m', '"Commit"', 'minor', 'setup.py']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == ['minor', 'setup.py']
        assert optional == ['--allow-dirty', '-m', '"Commit"']
