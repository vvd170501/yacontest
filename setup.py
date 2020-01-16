#!/usr/bin/env python3
from setuptools import setup
from os import path, environ
from pathlib import Path


home = Path.home()
here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='yacontest',
    version='0.1.0',
    description='console utility for Yandex.Contest',
    long_description=long_description,
    url='https://github.com/vvd170501/yacontest',
    license='GPL',
    packages=['yacontest'],
    package_data={'yacontest': ['data/config']},
    entry_points={
        'console_scripts': ['yacontest = yacontest.console:main'],
    },
    install_requires=['beautifulsoup4', 'requests'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ]
)
