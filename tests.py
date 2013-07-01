# -*- coding: utf-8 -*-

import pytest

import argparse
import subprocess
from os import curdir, makedirs, chdir, environ
from os.path import join, curdir, dirname
from shlex import split as shlex_split

from bumpversion import main

environ['HGENCODING'] = 'UTF-8'


EXPECTED_USAGE = u"""
usage: py.test [-h] [--config-file FILE] [--parse REGEX] [--serialize FORMAT]
               [--current-version VERSION] [--dry-run] --new-version VERSION
               [--commit | --no-commit] [--tag | --no-tag]
               [--message COMMIT_MSG]
               part file [file ...]

Bumps version strings

positional arguments:
  part                  Part of the version to be bumped.
  file                  Files to change

optional arguments:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --parse REGEX         Regex parsing the version string (default:
                        (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))
  --serialize FORMAT    How to format what is parsed back to a version
                        (default: {major}.{minor}.{patch})
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
  --message COMMIT_MSG, -m COMMIT_MSG
                        Commit message (default: Bump version:
                        {current_version} → {new_version})
""".lstrip()


def test_usage_string(tmpdir, capsys):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    assert err == ""
    assert out == EXPECTED_USAGE, u"Usage string changed to \n\n\n{}\n\n\n".format(out)

@pytest.mark.parametrize(("vcs"), [("git"), ("hg")])
def test_regression_help_in_workdir(tmpdir, capsys, vcs):
    tmpdir.chdir()
    tmpdir.join("somesource.txt").write("1.7.2013")
    subprocess.check_call([vcs, "init"])
    subprocess.check_call([vcs, "add", "somesource.txt"])
    subprocess.check_call([vcs, "commit", "-m", "initial commit"])
    subprocess.check_call([vcs, "tag", "v1.7.2013"])

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    assert err == ""

    if vcs == "git":
        assert "usage: py.test [-h] [--config-file FILE] [--parse REGEX] [--serialize FORMAT]" in out
        assert "Version that needs to be updated (default: 1.7.2013)" in out
        assert "[--new-version VERSION]" in out
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


def test_dry_run(tmpdir):

    config = """[bumpversion]
current_version: 12
new_version: 12.2
files: file4"""

    version = "12"

    tmpdir.join("file4").write(version)
    tmpdir.join(".bumpversion.cfg").write(config)

    tmpdir.chdir()
    main(['patch', '--dry-run'])

    assert config == tmpdir.join(".bumpversion.cfg").read()
    assert version == tmpdir.join("file4").read()


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


@pytest.mark.parametrize(("vcs"), [("git"), ("hg")])
def test_dirty_workdir(tmpdir, vcs):
    tmpdir.chdir()
    subprocess.check_call([vcs, "init"])
    tmpdir.join("dirty").write("i'm dirty")

    subprocess.check_call([vcs, "add", "dirty"])

    with pytest.raises(AssertionError):
        main(['patch', '--current-version', '1', '--new-version', '2', 'file7'])


def test_bump_major(tmpdir):
    tmpdir.join("fileMAJORBUMP").write("4.2.8")
    tmpdir.chdir()
    main(['--current-version', '4.2.8', 'major', 'fileMAJORBUMP'])

    assert '5.0.0' == tmpdir.join("fileMAJORBUMP").read()


@pytest.mark.parametrize(("vcs"), [("git"), ("hg")])
def test_commit_and_tag(tmpdir, vcs):
    tmpdir.chdir()
    subprocess.check_call([vcs, "init"])
    tmpdir.join("VERSION").write("47.1.1")
    subprocess.check_call([vcs, "add", "VERSION"])
    subprocess.check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '47.1.1', '--commit', 'VERSION'])

    assert '47.1.2' == tmpdir.join("VERSION").read()

    log = subprocess.check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-47.1.1' in log
    assert '+47.1.2' in log
    assert u'Bump version: 47.1.1 → 47.1.2' in log

    tag_out = subprocess.check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert 'v47.1.2' not in tag_out

    main(['patch', '--current-version', '47.1.2', '--commit', '--tag', 'VERSION'])

    assert '47.1.3' == tmpdir.join("VERSION").read()

    log = subprocess.check_output([vcs, "log", "-p"])

    tag_out = subprocess.check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert 'v47.1.3' in tag_out

@pytest.mark.parametrize(("vcs"), [("git"), ("hg")])
def test_commit_and_tag_with_configfile(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]\ncommit = True\ntag = True""")

    subprocess.check_call([vcs, "init"])
    tmpdir.join("VERSION").write("48.1.1")
    subprocess.check_call([vcs, "add", "VERSION"])
    subprocess.check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '48.1.1', '--no-tag', 'VERSION'])

    assert '48.1.2' == tmpdir.join("VERSION").read()

    log = subprocess.check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-48.1.1' in log
    assert '+48.1.2' in log
    assert u'Bump version: 48.1.1 → 48.1.2' in log

    tag_out = subprocess.check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert 'v48.1.2' not in tag_out

    main(['patch', '--current-version', '48.1.2', 'VERSION'])

    assert '48.1.3' == tmpdir.join("VERSION").read()

    log = subprocess.check_output([vcs, "log", "-p"])

    tag_out = subprocess.check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert 'v48.1.3' in tag_out


@pytest.mark.parametrize(("vcs"), [("git"), ("hg")])
def test_commit_explicitly_false(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 10.0.0
commit = False
tag = False""")

    subprocess.check_call([vcs, "init"])
    tmpdir.join("trackedfile").write("10.0.0")
    subprocess.check_call([vcs, "add", "trackedfile"])
    subprocess.check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', 'trackedfile'])

    assert '10.0.1' == tmpdir.join("trackedfile").read()

    log = subprocess.check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "10.0.1" not in log

    diff = subprocess.check_output([vcs, "diff"]).decode("utf-8")
    assert "10.0.1" in diff


@pytest.mark.parametrize(("vcs"), [("git"), ("hg")])
def test_commit_configfile_true_cli_false_override(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 27.0.0
commit = True""")

    subprocess.check_call([vcs, "init"])
    tmpdir.join("dontcommitfile").write("27.0.0")
    subprocess.check_call([vcs, "add", "dontcommitfile"])
    subprocess.check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--no-commit', 'dontcommitfile'])

    assert '27.0.1' == tmpdir.join("dontcommitfile").read()

    log = subprocess.check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "27.0.1" not in log

    diff = subprocess.check_output([vcs, "diff"]).decode("utf-8")
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


def test_current_version_from_tag(tmpdir):
    # prepare
    tmpdir.join("update_from_tag").write("26.6.0")
    tmpdir.chdir()
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", "update_from_tag"])
    subprocess.check_call(["git", "commit", "-m", "initial"])
    subprocess.check_call(["git", "tag", "v26.6.0"])

    # don't give current-version, that should come from tag
    main(['patch', 'update_from_tag'])

    assert '26.6.1' == tmpdir.join("update_from_tag").read()


def test_current_version_from_tag_not_written_to_config_file(tmpdir):
    # prepare
    tmpdir.join("updated_but_not_config_file").write("14.6.0")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]""")

    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", "updated_but_not_config_file"])
    subprocess.check_call(["git", "commit", "-m", "initial"])
    subprocess.check_call(["git", "tag", "v14.6.0"])

    # don't give current-version, that should come from tag
    main([
        'patch',
        'updated_but_not_config_file',
         '--commit',
         '--tag',
         ])

    assert '14.6.1' == tmpdir.join("updated_but_not_config_file").read()
    assert '14.6.1' not in tmpdir.join(".bumpversion.cfg").read()


def test_distance_to_latest_tag_as_part_of_new_version(tmpdir):
    # prepare
    tmpdir.join("mysourcefile").write("19.6.0")
    tmpdir.chdir()

    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", "mysourcefile"])
    subprocess.check_call(["git", "commit", "-m", "initial"])
    subprocess.check_call(["git", "tag", "v19.6.0"])
    subprocess.check_call(["git", "commit", "--allow-empty", "-m", "Just a commit 1"])
    subprocess.check_call(["git", "commit", "--allow-empty", "-m", "Just a commit 2"])
    subprocess.check_call(["git", "commit", "--allow-empty", "-m", "Just a commit 3"])

    # don't give current-version, that should come from tag
    main([
         'patch',
         '--parse', '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*',
         '--serialize', '{major}.{minor}.{patch}-pre{distance_to_latest_tag}',
         'mysourcefile',
         ])

    assert '19.6.1-pre3' == tmpdir.join("mysourcefile").read()


def test_override_vcs_current_version(tmpdir):
    # prepare
    tmpdir.join("contains_actual_version").write("6.7.8")
    tmpdir.chdir()
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", "contains_actual_version"])
    subprocess.check_call(["git", "commit", "-m", "initial"])
    subprocess.check_call(["git", "tag", "v6.7.8"])

    # update file
    tmpdir.join("contains_actual_version").write("7.0.0")
    subprocess.check_call(["git", "add", "contains_actual_version"])

    # but forgot to tag or forgot to push --tags
    subprocess.check_call(["git", "commit", "-m", "major release"])

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

def test_read_version_tags_only(tmpdir):
    # prepare
    tmpdir.join("update_from_tag").write("29.6.0")
    tmpdir.chdir()
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", "update_from_tag"])
    subprocess.check_call(["git", "commit", "-m", "initial"])
    subprocess.check_call(["git", "tag", "v29.6.0"])
    subprocess.check_call(["git", "commit", "--allow-empty", "-m", "a commit"])
    subprocess.check_call(["git", "tag", "jenkins-deploy-myproject-2"])

    # don't give current-version, that should come from tag
    main(['patch', 'update_from_tag'])

    assert '29.6.1' == tmpdir.join("update_from_tag").read()


