# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

VERSION = '0.1'
DESCRIPTION = """
Hackish pieces of software to an easy buildbot config
"""
LONG_DESCRIPTION = DESCRIPTION

setup(name='toxicbuild',
      version=VERSION,
      author='Juca Crispim',
      author_email='jucacrispim@gmail.com',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      packages=find_packages(exclude=['tests', 'tests.*']),
      install_requires=['buildbot>=0.8.8'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: No Input/Output (Daemon)',
          'Environment :: Web Environment',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Software Development :: Testing',
      ],
      scripts=['script/toxicbuild'],
      test_suite='tests',
      provides=['toxicbuild'],)
