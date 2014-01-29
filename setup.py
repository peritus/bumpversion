from setuptools import setup

setup(
    name='bumpversion',
    version='0.4.0',
    url='https://github.com/peritus/bumpversion',
    author='Filip Noetzel',
    author_email='filip+bumpversion@j03.de',
    license='',
    packages=['bumpversion'],
    description='Version-bump your software with a single command',
    long_description=str(open('README.rst', 'rb').read()),
    entry_points={
        'console_scripts': [
            'bumpversion = bumpversion:main',
        ]
    },
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: PyPy',
    ),
)
