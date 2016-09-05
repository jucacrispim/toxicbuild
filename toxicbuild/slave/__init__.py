# -*- coding: utf-8 -*-

import logging
import os
import pkg_resources
import shutil
from mando import command, main
from toxicbuild.core.conf import Settings
from toxicbuild.core.utils import daemonize as daemon
from toxicbuild.slave.managers import BuildManager


ENVVAR = 'TOXICSLAVE_SETTINGS'
DEFAULT_SETTINGS = 'toxicslave.conf'

settings = None

PIDFILE = 'toxicslave.pid'


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


@command
def start(workdir, daemonize=False, stdout='/dev/null', stderr='/dev/null',
          conffile=None, loglevel='info', pidfile=PIDFILE):  # pragma: no cover
    """ Starts the build server.

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

        os.chdir(workdir)
        server.run_server(addr, port)


@command
def stop(workdir, pidfile=PIDFILE):  # pragma: no cover
    """ Stops a buid server instance.

    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    os.chdir(workdir)
    with open(pidfile) as fd:
        pid = int(fd.read())

    os.kill(pid, 9)
    os.remove(pidfile)


@command
def create(root_dir):  # pragma: no cover
    """ Create a new toxicslave project.

    :param --root_dir: Root directory for toxicslave.
    """
    print('Creating root_dir {}'.format(root_dir))

    os.mkdir(root_dir)

    fakesettings = os.path.join(root_dir, 'fakesettings.py')
    with open(fakesettings, 'w') as f:
        f.write('DATABASE = {}')
    os.environ['TOXICSLAVE_SETTINGS'] = fakesettings

    template_fname = 'toxicslave.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.slave',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicslave.conf')
    shutil.copyfile(template_file, dest_file)
    os.remove(fakesettings)

make_pyflakes_happy = [BuildManager]
del make_pyflakes_happy


if __name__ == '__main__':   # pragma: no cover
    main()
