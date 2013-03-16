import pytest

import argparse
import subprocess
from os import curdir, makedirs, chdir
from os.path import join, curdir, dirname
from shlex import split as shlex_split

from bumpversion import main

def test_usage_string(capsys):
    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    assert err == ""
    assert out == """usage: py.test [-h] [--config-file FILE] --current-version VERSION
               --new-version VERSION
               file [file ...]

Bumps version strings

positional arguments:
  file                  Files to change

optional arguments:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --current-version VERSION
                        Version that needs to be updated (default: None)
  --new-version VERSION
                        New version that should be in the files (default:
                        None)
"""

def test_usage_string_with_config(tmpdir, capsys):
    tmpdir.chdir()
    tmpdir.join("mydefaults.cfg").write("""[bumpversion]
current_version: 18
new_version: 19
files: file1 file2 file3""")
    with pytest.raises(SystemExit):
        main(['--config-file', 'mydefaults.cfg', '--help'])

    out, err = capsys.readouterr()
    assert out == """usage: py.test [-h] [--config-file FILE] [--current-version VERSION]
               [--new-version VERSION]
               [file [file ...]]

Bumps version strings

positional arguments:
  file                  Files to change (default: ['file1', 'file2', 'file3'])

optional arguments:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --current-version VERSION
                        Version that needs to be updated (default: 18)
  --new-version VERSION
                        New version that should be in the files (default: 19)
"""

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

