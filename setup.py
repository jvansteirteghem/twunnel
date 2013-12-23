#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

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
    'nose', 
    'pyopenssl', 
    'pycrypto', 
    'pyasn1', 
    'twisted', 
    'autobahn'
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
    version='0.7.1',
    description='A HTTPS/SOCKS5 tunnel for Twisted.',
    long_description=readme,
    packages=packages,
    package_data=package_data,
    install_requires=requires,
    author='Jeroen Van Steirteghem',
    author_email='jeroen.vansteirteghem@gmail.com',
    url='https://github.com/jvansteirteghem/twunnel',
    license='MIT',
    classifiers=classifiers,
)
