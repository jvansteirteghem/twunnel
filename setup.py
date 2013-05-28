#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import twunnel


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    readme = f.read()

packages = [
    'twunnel',
]

package_data = {
}

requires = [
]

classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
]

setup(
    name='twunnel',
    version=twunnel.__version__,
    description='A HTTP/SOCKS5 tunnel for Twisted.',
    long_description=readme,
    packages=packages,
    package_data=package_data,
    install_requires=requires,
    author=twunnel.__author__,
    author_email='jeroen.vansteirteghem@gmail.com',
    url='https://github.com/jvansteirteghem/twunnel',
    license='MIT',
    classifiers=classifiers,
)
