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

from bumpversion import main, DESCRIPTION

SUBPROCESS_ENV = dict(
    list(environ.items()) + [('HGENCODING', 'utf-8')]
)

call = partial(subprocess.call, env=SUBPROCESS_ENV)
check_call = partial(subprocess.check_call, env=SUBPROCESS_ENV)
check_output = partial(subprocess.check_output,  env=SUBPROCESS_ENV)

xfail_if_no_git = pytest.mark.xfail(
  call(["git", "--help"], shell=True) != 1,
  reason="git is not installed"
)

xfail_if_no_hg = pytest.mark.xfail(
  call(["hg", "--help"], shell=True) != 0,
  reason="hg is not installed"
)

def _mock_calls_to_string(called_mock):
    return ["{}|{}|{}".format(
        name,
        args[0] if len(args) > 0  else args,
        repr(kwargs) if len(kwargs) > 0 else ""
    ) for name, args, kwargs in called_mock.mock_calls]


EXPECTED_USAGE = ("""
usage: py.test [-h] [--config-file FILE] [--verbose] [--list] [--parse REGEX]
               [--serialize FORMAT] [--current-version VERSION] [--dry-run]
               --new-version VERSION [--allow-dirty] [--commit | --no-commit]
               [--tag | --no-tag] [--tag-name TAG_NAME] [--message COMMIT_MSG]
               part [file [file ...]]

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
  --parse REGEX         Regex parsing the version string (default:
                        (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))
  --serialize FORMAT    How to format what is parsed back to a version
                        (default: ['{major}.{minor}.{patch}'])
  --current-version VERSION
                        Version that needs to be updated (default: None)
  --dry-run, -n         Don't write any files, just pretend. (default: False)
  --new-version VERSION
                        New version that should be in the files (default:
                        None)
  --allow-dirty         Do not check that version control is non-dirty
                        (default: False)
  --commit              Commit to version control (default: False)
  --no-commit           Do not commit to version control
  --tag                 Create a tag in version control (default: False)
  --no-tag              Do not create a tag in version control
  --tag-name TAG_NAME   Tag name (only works with --tag) (default:
                        v{new_version})
  --message COMMIT_MSG, -m COMMIT_MSG
                        Commit message (default: Bump version:
                        {current_version} → {new_version})
""" % DESCRIPTION).lstrip()

def _unidiff_output(expected, actual):
    """
    Helper function. Returns a string containing the unified diff of two multiline strings.
    """

    import difflib
    expected=expected.splitlines(1)
    actual=actual.splitlines(1)

    diff=difflib.unified_diff(expected, actual)

    return ''.join(diff)

def test_usage_string(tmpdir, capsys):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    import pdb; pdb.set_trace()

    s = _unidiff_output(out, EXPECTED_USAGE)
    assert err == ""
    assert out == EXPECTED_USAGE, "Usage string changed to \n\n\n{}\n\n\n".format(out)

def test_usage_string_fork(tmpdir, capsys):
    tmpdir.chdir()

    out = check_output('bumpversion --help; exit 0', shell=True, stderr=subprocess.STDOUT).decode('utf-8')

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

    if vcs == "git":
        assert "usage: py.test [-h] [--config-file FILE] [--verbose] [--list] [--parse REGEX]" in out
        assert "Version that needs to be updated (default: 1.7.2013)" in out
    else:
        assert out == EXPECTED_USAGE


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


def test_default_config_file(tmpdir):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
files: file2""")

    tmpdir.chdir()
    main(['patch'])

    assert "0.10.3" == tmpdir.join("file2").read()


def test_config_file_is_updated(tmpdir):
    tmpdir.join("file3").write("13")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 13
new_version: 14
files: file3""")

    tmpdir.chdir()
    main(['patch'])

    assert """[bumpversion]
current_version = 14
files = file3

""" == tmpdir.join(".bumpversion.cfg").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_dry_run(tmpdir, vcs):
    tmpdir.chdir()

    config = """[bumpversion]
current_version = 12
new_version = 12.2
files = file4
tag = True
commit = True
message = DO NOT BUMP VERSIONS WITH THIS FILE
"""

    version = "12"

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


def test_bumpversion_serialize_only_parts(tmpdir):
    tmpdir.join("file51").write("XXX1.1.8-master+allan1")
    tmpdir.chdir()
    main([
         '--current-version', '1.1.8-master+allan1',
         '--parse', '(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)(-(?P<prerel>[^\+]+))?(\+(?P<meta>.*))?',
         '--serialize', 'v{major}.{minor}',
         'meta',
         'file51'
         ])

    assert 'XXXv1.1' == tmpdir.join("file51").read()


@pytest.mark.parametrize(("vcs"), [xfail_if_no_git("git"), xfail_if_no_hg("hg")])
def test_dirty_workdir(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("dirty").write("i'm dirty")

    check_call([vcs, "add", "dirty"])

    with pytest.raises(AssertionError):
        main(['patch', '--current-version', '1', '--new-version', '2', 'file7'])


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
    tmpdir.join("fileA").write("0.9")
    tmpdir.chdir()
    main([
         '--current-version', '0.9',
         '--parse', '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?',
         '--serialize', 'Version: {major}.{minor}.{patch}',
         '--serialize', 'Version: {major}.{minor}',
         '--serialize', 'Version: {major}',
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
        info|Available serialization formats: '{major}.{minor}.{patch}'|
        info|Found '{major}.{minor}.{patch}' to be a usable serialization format|
        info|Selected serialization format '{major}.{minor}.{patch}'|
        info|Serialized to '1.0.1'|
        info|New version will be '1.0.1'|
        info|Asserting files blargh.txt contain string '1.0.0':|
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
        info|New version will be '13'|
        info|Asserting files  contain string '12':|
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
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?"""))

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
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        
        |
        info|Parsing version '0.4' using regexp '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?'|
        info|Parsed the following values: major=0, minor=4, patch=0|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=0, minor=4, patch=1|
        info|Available serialization formats: '{major}.{minor}.{patch}', '{major}.{minor}'|
        info|Found '{major}.{minor}.{patch}' to be a usable serialization format|
        info|Could not represent 'patch' in format '{major}.{minor}'|
        info|Selected serialization format '{major}.{minor}.{patch}'|
        info|Serialized to '0.4.1'|
        info|New version will be '0.4.1'|
        info|Asserting files fileE contain string '0.4':|
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
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?"""))

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
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?

        |
        info|Parsing version '0.8' using regexp '(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?'|
        info|Parsed the following values: major=0, minor=8, patch=0|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=0, minor=8, patch=1|
        info|Available serialization formats: '{major}.{minor}.{patch}', '{major}.{minor}'|
        info|Found '{major}.{minor}.{patch}' to be a usable serialization format|
        info|Could not represent 'patch' in format '{major}.{minor}'|
        info|Selected serialization format '{major}.{minor}.{patch}'|
        info|Serialized to '0.8.1'|
        info|Dry run active, won't touch any files.|
        info|New version will be '0.8.1'|
        info|Asserting files dont_touch_me.txt contain string '0.8':|
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
        info|Would tag 'v0.8.1' in Git|
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
        """))

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
        tag = False
        
        |
        info|Parsing version '0.3.3' using regexp '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'|
        info|Parsed the following values: major=0, minor=3, patch=3|
        info|Attempting to increment part 'patch'|
        info|Values are now: major=0, minor=3, patch=4|
        info|Available serialization formats: '{major}.{minor}.{patch}'|
        info|Found '{major}.{minor}.{patch}' to be a usable serialization format|
        info|Selected serialization format '{major}.{minor}.{patch}'|
        info|Serialized to '0.3.4'|
        info|New version will be '0.3.4'|
        info|Asserting files please_touch_me.txt contain string '0.3.3':|
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
        info|Would tag 'v0.3.4' in Git|
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
        """))

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
        """))

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
        """))

    main(['release', '--verbose'])

    assert '1.5' == tmpdir.join("with_prereleases.txt").read()

    main(['minor', '--verbose'])

    assert '1.6.dev' == tmpdir.join("with_prereleases.txt").read()

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

