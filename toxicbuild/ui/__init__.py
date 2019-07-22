# -*- coding: utf-8 -*-

import gettext
import os
import pkg_resources
import shutil
import sys
from tornado import locale
from tornado.platform.asyncio import AsyncIOMainLoop
from toxicbuild.core.cmd import command, main
from toxicbuild.core.conf import Settings
from toxicbuild.core.utils import bcrypt, changedir, SettingsPatcher

# pylint: disable=global-statement

here = os.path.dirname(os.path.abspath(__file__))

# translations for cli
cli_translations = os.path.join(here, 'translations')
gettext.install('toxicbuild.ui', cli_translations)


# translations for ui
web_translations = os.path.join(here, 'translations', 'web')
locale.load_translations(web_translations)


ENVVAR = 'TOXICUI_SETTINGS'
DEFAULT_SETTINGS = 'toxicui.conf'

settings = None

LOGFILE = './toxicui.log'


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


# we install the asyncio loop for tornado so we can
# use it inside tornado handlers with @gen.coroutine
AsyncIOMainLoop().install()


pyrocommand = None


def _check_conffile(workdir, conffile):
    """Checks if the conffile is inside workdir."""

    absworkdir = os.path.abspath(workdir)
    absconffile = os.path.abspath(conffile)

    return absconffile.startswith(absworkdir)


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          pidfile=None, loglevel='info', conffile=None):
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
    :param -c, --conffile: path to config file. It must be relative
      to the workdir. Defaults to None. If not conffile, will look
      for a file called ``toxicui.conf`` inside ``workdir``
    """

    global pyrocommand

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        if conffile:

            is_in_workdir = _check_conffile(workdir, conffile)

            if not is_in_workdir:
                print('Config file must be inside workdir')
                sys.exit(1)

            os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir, conffile)
            module = conffile.replace('.conf', '').replace(
                workdir, '').strip('/').replace(os.sep, '.')
            os.environ['PYROCUMULUS_SETTINGS_MODULE'] = module
        else:
            os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir,
                                                          'toxicui.conf')
            os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicui'

        create_settings()

        SettingsPatcher().patch_pyro_settings(settings)

        from pyrocumulus.commands.base import get_command

        sys.argv = ['pyromanager.py', '']

        print('Starting web ui on port {}'.format(settings.TORNADO_PORT))

        if not pyrocommand:
            pyrocommand = command = get_command('runtornado')()
        else:
            command = pyrocommand

        command.kill = False
        command.daemonize = daemonize
        command.stderr = stderr
        command.application = None
        command.loglevel = loglevel
        command.stdout = stdout
        command.port = settings.TORNADO_PORT
        command.pidfile = pidfile
        command.run()


@command
def stop(workdir, pidfile=None):
    """ Stops the web interface.

    :param workdir: Work directory for the ui to be killed.
    :param --pidfile: pid file for the process.
    """

    global pyrocommand

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir,
                                                      'toxicui.conf')
        os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicui'

        create_settings()

        SettingsPatcher().patch_pyro_settings(settings)

        from pyrocumulus.commands.base import get_command

        sys.argv = ['pyromanager.py', '']

        if not pyrocommand:
            pyrocommand = command = get_command('runtornado')()
        else:
            command = pyrocommand

        command.pidfile = pidfile
        command.kill = True
        command.run()


@command
def restart(workdir, pidfile=None, loglevel='info'):
    """Restarts the web interface

    The instance of toxicweb in ``workdir`` will be restarted.
    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.
    :param --loglevel: Level for logging messages.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True, loglevel=loglevel)


@command
def create(root_dir, access_token='', output_token='', root_user_id='',
           cookie_secret=''):
    """ Create a new toxicweb project.

    :param root_dir: Root directory for toxicweb.
    :param --access-token: Access token to master's hole.
    :param --output-token: Access token to the notifications api.
    :param --root-user-id: The id for the root user of the system.
    :param --cookie-secret: Secret for secure cookies.
    """
    print('Creating root_dir {}'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicui.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.ui',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicui.conf')
    shutil.copyfile(template_file, dest_file)

    cookie_secret = cookie_secret or bcrypt.gensalt(8).decode()

    # and finally update the config file content with the new generated
    # salt and access token
    with open(dest_file, 'r+') as fd:
        content = fd.read()
        content = content.replace('{{COOKIE_SECRET}}', cookie_secret)
        content = content.replace('{{HOLE_TOKEN}}', access_token)
        content = content.replace('{{NOTIFICATIONS_API_TOKEN}}', output_token)
        content = content.replace('{{ROOT_USER_ID}}', root_user_id)
        fd.seek(0)
        fd.write(content)

    print('Toxicui environment created for web ')
    return access_token


def _ask_thing(thing):
    response = input(thing)
    while not response:
        response = input(thing)

    return response


if __name__ == '__main__':
    main()
