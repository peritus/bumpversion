
import subprocess
from os import curdir, makedirs, chdir
from os.path import join, curdir, dirname
from shlex import split as shlex_split

from bumpversion import main

def test_simple_replacement():
    path = join(curdir, '_test_run', 'simple_replacement')
    makedirs(path)
    chdir(path)

    with open('VERSION', 'w') as f:
        f.write("1.2.0")

    main(shlex_split("--old-version 1.2.0 --new-version 1.2.1 VERSION"))

    with open('VERSION', 'r') as f:
        assert "1.2.1" == f.read()

    chdir('../..')

def test_config_file():
    path = join(curdir, '_test_run', 'config_file')
    makedirs(path)
    chdir(path)

    with open('mybumpconfig.cfg', 'w') as f:
        f.write("""[bumpversion]
old_version: 0.9.34
new_version: 0.9.35
files: file1""")

    with open('file1', 'w') as f:
        f.write("0.9.34")

    main(shlex_split("--config-file mybumpconfig.cfg"))

    with open('file1', 'r') as f:
        assert "0.9.35" == f.read()

    chdir('../..')
