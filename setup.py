from setuptools import setup

setup(
    name='bumpversion',
    version='0.3.2',
    url='https://github.com/peritus/bumpversion',
    author='Filip Noetzel',
    author_email='filip+bumpversion@j03.de',
    license='',
    packages=['bumpversion'],
    description='Version-bump your software with a single command',
    long_description=open('README.rst', 'r').read(),
    entry_points={
        'console_scripts': [
        'bumpversion = bumpversion:main',
        ]
    },
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ),
)
