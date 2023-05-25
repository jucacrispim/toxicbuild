# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


def get_version_from_file():
    # get version number from __init__ file
    # before module is installed

    fname = 'toxicbuild/__init__.py'
    with open(fname) as f:
        fcontent = f.readlines()
    version_line = [l for l in fcontent if 'VERSION' in l][0]
    return version_line.split('=')[1].strip().strip("'").strip('"')


def get_long_description_from_file():
    # content of README will be the long description

    fname = 'README'
    with open(fname) as f:
        fcontent = f.read()
    return fcontent


VERSION = get_version_from_file()

DESCRIPTION = """
Simple and flexible continuous integration tool.
""".strip()

LONG_DESCRIPTION = get_long_description_from_file()

setup(name='toxicbuild',
      version=VERSION,
      author='Juca Crispim',
      author_email='juca@poraodojuca.net',
      url='http://toxicbuild.poraodojuca.net',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      packages=find_packages(exclude=['tests', 'tests.*']),
      license='AGPL',
      include_package_data=True,
      install_requires=['tornado==6.3.2', 'mongomotor==0.16.2',
                        'asyncblink==0.3.2', 'mando==0.6.4',
                        'pyrocumulus==0.12.4', 'pytz==2022.7.1',
                        'aiohttp==3.8.4', 'aiosmtplib==2.0.1',
                        'asyncamqp==0.1.7', 'pyyaml==5.4',
                        'PyJWT==2.6.0', 'cryptography==39.0.2',
                        'aiozk==0.30.0', 'blinker==1.5',
                        'aiobotocore==2.4.0', 'awscli==1.25.60',
                        'bcrypt==4.0.1', 'mongoengine==0.27.0'],
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
          'console_scripts': [
              'toxicbuild=toxicbuild.script:main',
              'toxicmaster=toxicbuild.master.cmds:main',
              'toxicslave=toxicbuild.slave.cmds:main',
              'toxicpoller=toxicbuild.poller.cmds:main',
              'toxicsecrets=toxicbuild.secrets.cmds:main',
              'toxicweb=toxicbuild.ui.cmds:main',
              'toxicintegrations=toxicbuild.integrations.cmds:main',
              'toxicoutput=toxicbuild.output.cmds:main']
      },
      test_suite='tests',
      provides=['toxicbuild'],)
