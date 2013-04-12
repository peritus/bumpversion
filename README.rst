===========
bumpversion
===========

Version-bump your software with a single command!

bumpversion updates all version strings in your source tree by the correct increment, commits that change to git and tags it.

.. image:: https://travis-ci.org/peritus/bumpversion.png?branch=master
  :target: https://travis-ci.org/peritus/bumpversion

Screencast
==========

.. image:: https://dl.dropboxusercontent.com/u/8735936/Screen%20Shot%202013-04-12%20at%202.43.46%20PM.png
  :target: http://goo.gl/xogFw

Installation
============

You can download and install the latest version of this software from the Python package index (PyPI) as follows::

    pip install --upgrade bumpversion

Usage
=====

::

    bumpversion [options] file [file ...]

Config file .bumpversion.cfg
++++++++++++++++++++++++++++

All options can optionally be specified in a config file called ``.bumpversion.cfg`` so that once you know how ``bumpversion`` needs to be configured for one particular software package, you can run it without specifying options later. You should add that file to VCS so others can also bump versions.

Options on the command line take precedence over those from the config file, which take precedence over those derived from the environment and then from the defaults.

Example ``.bumpversion.cfg``::

  [bumpversion]
  current_version = 0.2.9
  files = setup.py
  commit = True
  tag = True


Options
=======

``file [file ...]`` / ``files =``
  **no default value**

  The files where to search and replace version strings

  Command line example::

     bumpversion setup.py src/VERSION.txt

  Config file example::

    [bumpversion]
    files = setup.py src/VERSION.txt

``--bump`` / ``bump =``
  **default:** ``patch``

  Part of the version to increase.

  Valid values include those given in the ``--serialize`` / ``--parse`` option.

  Example `bumping to 0.6.0`::

     bumpversion --current-version 0.5.1 --bump minor setup.py

  Example `bumping to 2.0.0`::

     bumpversion --current-version 1.1.9 --bump major setup.py

``--current-version`` / ``current_version =``
  **no default value**

  The current version of the software package.

  Example::

     bumpversion --current-version 0.5.1 setup.py

``--new-version`` / ``new_version =``
  **no default value**

  The version of the software after the increment

  Example (`Go from 0.5.1 directly to 0.6.1`)::

      bumpversion --current-version 0.5.1 --new-version 0.6.1 setup.py

``--parse`` / ``parse =``
  **default:** "``(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)``"

  Regular expression (using `Python regular expression syntax <http://docs.python.org/2/library/re.html#regular-expression-syntax>`_) on how to find and parse the version string.

  Is required to parse all strings produced by ``--serialize``. Named matching groups ("``(?P<name>...)``") provide values to use with the ``--bump`` flag.

``--serialize`` / ``serialize =``
  **default:** "``{major}.{minor}.{patch}``"

  Template specifying how to serialize the version parts to a version string again.

  This is templated using the `Python Format String Syntax <http://docs.python.org/2/library/string.html#format-string-syntax>`_. Available in the template context are parsed values of the named groups specified in ``--parse`` as well as all environment variables (prefixed with ``$``).

``--tag`` / ``tag = True``
  **default:** `Don't create a tag`

  Whether to create a git tag, that is the new version, prefixed with the character "``v``". Don't forget to ``git-push`` with the ``--tags`` flag.

``--commit`` / ``commit = True``
  **default:** `Don't create a commit`

  Whether to create a git commit

``--message`` / ``message =``
  **default:** "``Bump version: {current_version} → {new_version}``"

  The commit message to use when creating a commit. Only valid when using ``--commit`` / ``commit = True``.

  This is templated using the `Python Format String Syntax <http://docs.python.org/2/library/string.html#format-string-syntax>`_. Available in the template context are ``current_version`` and ``new_version`` as well as all environment variables (prefixed with ``$``).

  Example::

    bumpversion --message 'Jenkins Build {$BUILD_NUMBER}: {new_version}'

``-dry-run, -n``
  Don't touch any files, just pretend

``-h, --help``
  Print help and exit

Development
===========

Development of this happens on GitHub, patches including tests, documentation are very welcome, as well as bug reports! Also please open an issue if this tool does not support every aspect of bumping versions in your development workflow, as it is intended to be very versatile.


