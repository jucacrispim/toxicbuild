# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# Server for custom webhook. Used in functional tests

import asyncio
import os
import sys
from mando import command, main
from mongomotor import Document
from mongomotor.fields import StringField
from pyrocumulus.commands.base import get_command
from pyrocumulus.web.applications import PyroApplication
from pyrocumulus.web.decorators import post
from pyrocumulus.web.handlers import RestHandler
from pyrocumulus.web.urlmappers import URLSpec
from tornado import gen
from toxicbuild.core.utils import changedir
from tests.functional import MASTER_ROOT_DIR

LOGFILE = os.path.join(MASTER_ROOT_DIR, 'customwebhook.log')


class WebHookMessage(Document):
    message = StringField()


class CustomWebHook(RestHandler):

    @post('')
    @gen.coroutine
    def income_webhook(self, **kw):
        m = self.model(message=self.request.body)
        yield from m.save()


url = URLSpec('/webhookmessage/(.*)', CustomWebHook, {'model': WebHookMessage})
app = PyroApplication([url])


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          pidfile=None, loglevel='info', conffile=None):

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)
        module = 'tests.functional.data.master.custom_webhook'
        os.environ['PYROCUMULUS_SETTINGS_MODULE'] = module

        from pyrocumulus.conf import settings

        sys.argv = ['pyromanager.py', '']

        command = get_command('runtornado')()

        command.kill = False
        command.daemonize = daemonize
        command.stderr = stderr
        command.application = 'tests.functional.custom_webhook.app'
        command.stdout = stdout
        command.port = settings.TORNADO_PORT
        command.pidfile = pidfile
        command.run()


@command
def stop(workdir, pidfile=None):

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        module = 'tests.functional.data.master.custom_webhook'
        os.environ['PYROCUMULUS_SETTINGS_MODULE'] = module

        sys.argv = ['pyromanager.py', '']

        command = get_command('runtornado')()
        command.application = 'tests.functional.custom_webhook.app'
        command.pidfile = pidfile
        command.kill = True
        command.run()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(WebHookMessage.drop_collection())


if __name__ == '__main__':
    main()
