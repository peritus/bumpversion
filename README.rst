===========
bumpversion
===========

Version-bump your software with a single command!

bumpversion updates all version strings in your source tree by the correct
increment, commits that change to git or Mercurial and tags it.

.. image:: https://pypip.in/v/bumpversion/badge.png
  :target: https://pypi.python.org/pypi/bumpversion

.. image:: https://pypip.in/d/bumpversion/badge.png
  :target: https://pypi.python.org/pypi/bumpversion

.. image:: https://travis-ci.org/peritus/bumpversion.png?branch=master
  :target: https://travis-ci.org/peritus/bumpversion

Screencast
==========

.. image:: https://dl.dropboxusercontent.com/u/8735936/Screen%20Shot%202013-04-12%20at%202.43.46%20PM.png
  :target: http://goo.gl/gljhM

Installation
============

You can download and install the latest version of this software from the Python package index (PyPI) as follows::

    pip install --upgrade bumpversion

Usage
=====

::

    bumpversion [options] part file [file ...]

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
``part``
  Part of the version to increase.

  Valid values include those given in the ``--serialize`` / ``--parse`` option.

  Example `bumping to 0.6.0`::

     bumpversion --current-version 0.5.1 minor setup.py

  Example `bumping to 2.0.0`::

     bumpversion --current-version 1.1.9 major setup.py

``file [file ...]`` / ``files =``
  **no default value**

  The files where to search and replace version strings

  Command line example::

     bumpversion setup.py src/VERSION.txt

  Config file example::

    [bumpversion]
    files = setup.py src/VERSION.txt

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

  Is required to parse all strings produced by ``--serialize``. Named matching groups ("``(?P<name>...)``") provide values to as the ``part`` argument.

``--serialize`` / ``serialize =``
  **default:** "``{major}.{minor}.{patch}``"

  Template specifying how to serialize the version parts to a version string again.

  This is templated using the `Python Format String Syntax <http://docs.python.org/2/library/string.html#format-string-syntax>`_. Available in the template context are parsed values of the named groups specified in ``--parse`` as well as all environment variables (prefixed with ``$``).

``(--tag | --no-tag)`` / ``tag = (True | False)``
  **default:** `Don't create a tag`

  Whether to create a tag, that is the new version, prefixed with the character
  "``v``". If you are using git, don't forget to ``git-push`` with the
  ``--tags`` flag.

``--tag-name`` / ``tag_name =``
  **default:** "``v{new_version}``"

  The name of the tag that will be created. Only valid when using ``--tag`` / ``tag = True``.

  This is templated using the `Python Format String Syntax <http://docs.python.org/2/library/string.html#format-string-syntax>`_. Available in the template context are ``current_version`` and ``new_version`` as well as all environment variables (prefixed with ``$``). You can also use the variables ``now`` or ``utcnow`` to get a current timestamp. Both accept datetime formatting (when used like as in ``{now:%d.%m.%Y}``).


  Example::

    bumpversion --message 'Jenkins Build {$BUILD_NUMBER}: {new_version}'


``(--commit | --no-commit)`` / ``commit = (True | False)``
  **default:** `Don't create a commit`

  Whether to create a commit

``--message`` / ``message =``
  **default:** "``Bump version: {current_version} → {new_version}``"

  The commit message to use when creating a commit. Only valid when using ``--commit`` / ``commit = True``.

  This is templated using the `Python Format String Syntax <http://docs.python.org/2/library/string.html#format-string-syntax>`_. Available in the template context are ``current_version`` and ``new_version`` as well as all environment variables (prefixed with ``$``). You can also use the variables ``now`` or ``utcnow`` to get a current timestamp. Both accept datetime formatting (when used like as in ``{now:%d.%m.%Y}``).

  Example::

    bumpversion --message '[{now:%Y-%m-%d}] Jenkins Build {$BUILD_NUMBER}: {new_version}'

``--dry-run, -n``
  Don't touch any files, just pretend

``--verbose, -v``
  Print out current and new version strings

``-h, --help``
  Print help and exit

Development
===========

Development of this happens on GitHub, patches including tests, documentation are very welcome, as well as bug reports! Also please open an issue if this tool does not support every aspect of bumping versions in your development workflow, as it is intended to be very versatile.

Changes
=======

**v0.3.5**

- add {now} and {utcnow} to context
- use correct file encoding writing to config file. NOTE: If you are using
  Python2 and want to use UTF-8 encoded characters in your config file, you
  need to update ConfigParser like using 'pip install -U configparser'
- leave current_version in config even if available from vcs tags (was
  confusing)
- print own version number in usage
- allow bumping parts that contain non-numerics
- various fixes regarding file encoding

**v0.3.4**

- bugfix: tag_name and message in .bumpversion.cfg didn't have an effect (`#9 <https://github.com/peritus/bumpversion/issues/9>`_)

**v0.3.3**

- add --tag-name option
- now works on Python 3.2, 3.3 and PyPy

**v0.3.2**

- bugfix: Read only tags from `git describe` that look like versions

**v0.3.1**

- bugfix: ``--help`` in git workdir raising AssertionError
- bugfix: fail earlier if one of files does not exist
- bugfix: ``commit = True`` / ``tag = True`` in .bumpversion.cfg had no effect

**v0.3.0**

- **BREAKING CHANGE** The ``--bump`` argument was removed, this is now the first
  positional argument.
  If you used ``bumpversion --bump major`` before, you can use
  ``bumpversion major`` now.
  If you used ``bumpversion`` without arguments before, you now
  need to specify the part (previous default was ``patch``) as in
  ``bumpversion patch``).

**v0.2.2**

- add --no-commit, --no-tag

**v0.2.1**

- If available, use git to learn about current version

**v0.2.0**

- Mercurial support

**v0.1.1**

- Only create a tag when it's requested (thanks @gvangool)

**v0.1.0**

- Initial public version

