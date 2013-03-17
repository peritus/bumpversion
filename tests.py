import pytest

import argparse
import subprocess
from os import curdir, makedirs, chdir
from os.path import join, curdir, dirname
from shlex import split as shlex_split

from bumpversion import main

def test_usage_string(tmpdir, capsys):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    assert err == ""
    assert out == """
usage: py.test [-h] [--config-file FILE] [--bump PART] [--parse REGEX]
               [--serialize FORMAT] [--current-version VERSION] [--dry-run]
               --new-version VERSION [--commit] [--tag] [--message COMMIT_MSG]
               file [file ...]

Bumps version strings

positional arguments:
  file                  Files to change

optional arguments:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --bump PART           Part of the version to be bumped. (default: patch)
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
  --commit              Create a commit in version control (default: False)
  --tag                 Create a tag in version control (default: False)
  --message COMMIT_MSG, -m COMMIT_MSG
                        Commit message (default: Bump version:
                        {current_version} -> {new_version})
""".lstrip()

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
    main(shlex_split("--current-version 1.2.0 --new-version 1.2.1 VERSION"))
    assert "1.2.1" == tmpdir.join("VERSION").read()

def test_config_file(tmpdir):
    tmpdir.join("file1").write("0.9.34")
    tmpdir.join("mybumpconfig.cfg").write("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
files: file1""")

    tmpdir.chdir()
    main(shlex_split("--config-file mybumpconfig.cfg"))

    assert "0.9.35" == tmpdir.join("file1").read()

def test_default_config_file(tmpdir):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
files: file2""")

    tmpdir.chdir()
    main([])

    assert "0.10.3" == tmpdir.join("file2").read()

def test_config_file_is_updated(tmpdir):
    tmpdir.join("file3").write("13")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 13
new_version: 14
files: file3""")

    tmpdir.chdir()
    main([])

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
    main(['--dry-run'])

    assert config == tmpdir.join(".bumpversion.cfg").read()
    assert version == tmpdir.join("file4").read()

def test_bump_version(tmpdir):

    tmpdir.join("file5").write("1.0.0")
    tmpdir.chdir()
    main(['--current-version', '1.0.0', 'file5'])

    assert '1.0.1' == tmpdir.join("file5").read()

def test_bump_version_custom_parse(tmpdir):

    tmpdir.join("file6").write("XXX1;0;0")
    tmpdir.chdir()
    main([
      '--current-version', 'XXX1;0;0',
      '--bump', 'garlg',
      '--parse', 'XXX(?P<spam>\d+);(?P<garlg>\d+);(?P<slurp>\d+)',
      '--serialize', 'XXX{spam};{garlg};{slurp}',
      'file6'
    ])

    assert 'XXX1;1;0' == tmpdir.join("file6").read()

def test_git_dirty_workdir(tmpdir):
    tmpdir.chdir()
    subprocess.check_call(["git", "init"])
    tmpdir.join("dirty").write("i'm dirty")

    subprocess.check_call(["git", "add", "dirty"])

    with pytest.raises(AssertionError):
        main(['--current-version', '1', '--new-version', '2', 'file7'])

def test_bump_major(tmpdir):
    tmpdir.join("fileMAJORBUMP").write("4.2.8")
    tmpdir.chdir()
    main(['--current-version', '4.2.8', '--bump', 'major', 'fileMAJORBUMP'])

    assert '5.0.0' == tmpdir.join("fileMAJORBUMP").read()

def test_git_commit(tmpdir):
    tmpdir.chdir()
    subprocess.check_call(["git", "init"])
    tmpdir.join("VERSION").write("47.1.1")
    subprocess.check_call(["git", "add", "VERSION"])
    subprocess.check_call(["git", "commit", "-m", "initial commit"])

    main(['--current-version', '47.1.1', '--commit', 'VERSION'])

    assert '47.1.2' == tmpdir.join("VERSION").read()

    log = subprocess.check_output(["git", "log", "-p"])

    assert '-47.1.1' in log
    assert '+47.1.2' in log

    tag_out = subprocess.check_output(["git", "tag"])

    assert 'v47.1.2' in tag_out
