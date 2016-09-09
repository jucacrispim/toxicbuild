# -*- coding: utf-8 -*-

import logging
import os
import pkg_resources
import shutil
import sys
from uuid import uuid4
from toxicbuild.core.conf import Settings
from toxicbuild.core.cmd import command, main
from toxicbuild.core.utils import (daemonize as daemon, bcrypt_string, bcrypt,
                                   changedir)
from toxicbuild.slave.managers import BuildManager


ENVVAR = 'TOXICSLAVE_SETTINGS'
DEFAULT_SETTINGS = 'toxicslave.conf'

settings = None

PIDFILE = 'toxicslave.pid'
LOGFILE = 'toxicslave.log'


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


@command
def start(workdir, daemonize=False, stdout=LOGFILE,
          stderr=LOGFILE, conffile=None, loglevel='info',
          pidfile=PIDFILE):
    """ Starts toxicslave.

    Starts the build server to listen on the specified port for
    requests from addr (0.0.0.0 means everyone). Addr and port params
    came from the config file

    :param workdir: Work directory for server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to /dev/null
    :param --stderr: stderr path. Defaults to /dev/null
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicslave.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    print('Starting toxicslave')
    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    if conffile:
        os.environ['TOXICSLAVE_SETTINGS'] = conffile
    else:
        os.environ['TOXICSLAVE_SETTINGS'] = os.path.join(workdir,
                                                         'toxicslave.conf')

    create_settings()
    # These toxicbuild.slave imports must be here so I can
    # change the settings file before settings are instanciated.
    from toxicbuild.slave import server, settings

    addr = settings.ADDR
    port = settings.PORT

    if daemonize:
        daemon(call=server.run_server, cargs=(addr, port), ckwargs={},
               stdout=stdout, stderr=stderr, workdir=workdir, pidfile=pidfile)
    else:
        loglevel = getattr(logging, loglevel.upper())
        logging.basicConfig(level=loglevel)

        with changedir(workdir):
            server.run_server(addr, port)


@command
def stop(workdir, pidfile=PIDFILE):
    """ Stops toxicslave.

    The instance of toxicslave in ``workdir`` will be stopped.

    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    print('Stopping toxicslave')
    with changedir(workdir):
        with open(pidfile) as fd:
            pid = int(fd.read())

        os.kill(pid, 9)
        os.remove(pidfile)


@command
def restart(workdir, pidfile=PIDFILE):
    """Restarts toxicslave

    The instance of toxicslave in ``workdir`` will be restarted.
    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True)


@command
def create(root_dir):
    """ Create a new toxicslave environment.

    :param --root_dir: Root directory for toxicslave.
    """
    print('Creating root_dir `{}` for toxicslave'.format(root_dir))

    # First we create the directory
    os.makedirs(root_dir)

    # after that we copy the config file to the root dir
    template_fname = 'toxicslave.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.slave',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicslave.conf')
    shutil.copyfile(template_file, dest_file)

    # here we create a bcrypt salt and a access token for authentication.
    salt = bcrypt.gensalt(8)
    access_token = str(uuid4())
    encrypted_token = bcrypt_string(access_token, salt)

    # and finally update the config file content with the new generated
    # salt and access token
    with open(dest_file, 'r+') as fd:
        content = fd.read()
        content = content.replace('{{BCRYPT_SALT}}', salt.decode())
        content = content.replace('{{ACCESS_TOKEN}}', encrypted_token)
        fd.seek(0)
        fd.write(content)

    print('Toxicslave environment created with access token: {}'.format(
        access_token))
    return access_token

make_pyflakes_happy = [BuildManager]
del make_pyflakes_happy


if __name__ == '__main__':
    main()
