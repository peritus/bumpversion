import re
from setuptools import setup

description = 'Version-bump your software with a single command!'

long_description = re.sub(
  "\`(.*)\<#.*\>\`\_",
  r"\1",
  str(open('README.rst', 'rb').read()).replace(description, '')
)

setup(
    name='bumpversion',
    version='0.5.3',
    url='https://github.com/peritus/bumpversion',
    author='Filip Noetzel',
    author_email='filip+bumpversion@j03.de',
    license='MIT',
    packages=['bumpversion'],
    description=description,
    long_description=long_description,
    entry_points={
        'console_scripts': [
            'bumpversion = bumpversion:main',
        ]
    },
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: PyPy',
    ),
)
