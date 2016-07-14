# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

VERSION = '0.3-a0'
DESCRIPTION = """
Easy and flexible continuous integration.
"""
LONG_DESCRIPTION = DESCRIPTION

setup(name='toxicbuild',
      version=VERSION,
      author='Juca Crispim',
      author_email='juca@poraodojuca.net',
      url='http://toxicbuild.readthedocs.org/en/latest/',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      packages=find_packages(exclude=['tests', 'tests.*']),
      include_package_data=True,
      install_requires=['tornado>=4.1', 'mongomotor>=0.8.2',
                        'asyncblink>=0.1.1', 'mando>=0.3.2',
                        'pyrocumulus>=0.7.1'],
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
      scripts=['scripts/toxicmaster', 'scripts/toxicslave',
               'scripts/toxicweb'],
      test_suite='tests',
      provides=['toxicbuild'],)
