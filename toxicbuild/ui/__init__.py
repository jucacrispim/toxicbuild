# -*- coding: utf-8 -*-

import gettext
import os
import pkg_resources
import shutil
import sys
from mando import command, main
from tornado.platform.asyncio import AsyncIOMainLoop
from pyrocumulus.commands.base import get_command
from toxicbuild.core.conf import Settings

here = os.path.dirname(os.path.abspath(__file__))
translations = os.path.join(here, 'translations')

gettext.install('toxicbuild.ui', translations)

ENVVAR = 'TOXICUI_SETTINGS'
DEFAULT_SETTINGS = 'toxicui.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


# we install the asyncio loop for tornado so we can
# use it inside tornado handlers with @gen.coroutine
AsyncIOMainLoop().install()


@command
def start(workdir, daemonize=False, stdout='/dev/null', stderr='/dev/null',
          pidfile=None, loglevel='info'):  # pragma: no cover
    """ Starts the web interface.

    Starts the build server to listen on the specified port for
    requests from addr (0.0.0.0 means everyone). Addr and port params
    came from the configfile

    :param workdir: Work directory for server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to /dev/null
    :param --stderr: stderr path. Defaults to /dev/null
    :param --pidfile: pid file for the process.
    :param --loglevel: Level for logging messages. Defaults to `info`.
    """

    workdir = os.path.abspath(workdir)
    os.chdir(workdir)
    sys.path.append(workdir)

    os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir,
                                                  'toxicui.conf')
    os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicui'

    create_settings()

    sys.argv = ['pyromanager.py', 'web']
    command = get_command('runtornado')()
    command.kill = False
    command.daemonize = daemonize
    command.stderr = stderr
    command.stdout = stdout
    command.port = settings.TORNADO_PORT
    command.pidfile = pidfile
    command.run()


@command
def stop(workdir, pidfile=None):  # pragma: no cover
    """ Stops the web interface.

    :param workdir: Work directory for the ui to be killed.
    :param --pidfile: pid file for the process.
    """

    workdir = os.path.abspath(workdir)
    os.chdir(workdir)
    sys.path.append(workdir)

    os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir,
                                                  'toxicui.conf')
    os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicui'

    create_settings()

    sys.argv = ['pyromanager.py', 'web']

    command = get_command('runtornado')()
    command.pidfile = pidfile
    command.kill = True
    command.run()


@command
def create(root_dir):  # pragma: no cover
    """ Create a new toxicweb project.

    :param --root_dir: Root directory for toxicweb.
    """
    print('Creating root_dir {}'.format(root_dir))

    os.mkdir(root_dir)

    fakesettings = os.path.join(root_dir, 'fakesettings.py')
    with open(fakesettings, 'w') as f:
        f.write('DATABASE = {}')
    os.environ['TOXICUI_SETTINGS'] = fakesettings

    template_fname = 'toxicweb_settings.py.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.ui',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicweb_settings.py')
    shutil.copyfile(template_file, dest_file)
    os.remove(fakesettings)


if __name__ == '__main__':  # pragma: no cover
    main()
