# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

VERSION = '0.3'
DESCRIPTION = """
Simple and flexible continuous integration tool.
"""
LONG_DESCRIPTION = DESCRIPTION

setup(name='toxicbuild',
      version=VERSION,
      author='Juca Crispim',
      author_email='juca@poraodojuca.net',
      url='http://toxicbuild.poraodojuca.net',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      packages=find_packages(exclude=['tests', 'tests.*']),
      include_package_data=True,
      install_requires=['tornado>=4.1', 'mongomotor>=0.9b6',
                        'asyncblink>=0.1.1', 'mando>=0.3.2',
                        'pyrocumulus>=0.8rc0'],
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
      entry_points={
          'console_scripts': ['toxicbuild=toxicbuild.script:main',
                              'toxicmaster=toxicbuild.master:main',
                              'toxicslave=toxicbuild.slave:main',
                              'toxicweb=toxicbuild.ui:main']
      },
      test_suite='tests',
      provides=['toxicbuild'],)
