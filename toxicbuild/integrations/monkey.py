# -*- coding: utf-8 -*-
# Copyright 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import logging
import os

from tornado import ioloop
from tornado.httpserver import HTTPServer
from pyrocumulus.utils import get_value_from_settings


# patches pyrocumulus.run to allow a setup function after daemonization
# and before server start
def run(self):
    self.port = self.get_port()
    self.pidfile = self.pidfile or 'tornado-%i.pid' % self.port

    if self.kill:
        return self.killtornado()

    if self.daemonize:
        self.run_as_a_daemon()
        self.close_file_descriptors()
        self.redirect_stdout_stderr()
        self._write_to_file(self.pidfile, str(os.getpid()))

    # AsyncIOMainLoop().install()
    ioloop_inst = ioloop.IOLoop.instance()
    self.application = self.get_application()

    self._set_log_level()
    logger = logging.getLogger()
    msg = self.user_message.format(self.port)
    logger.log(logging.INFO, msg)
    self.setup_fn()
    tornado_opts = get_value_from_settings('HTTP_SERVER_OPTS', {})
    server = HTTPServer(self.application, **tornado_opts)
    server.listen(self.port)
    ioloop_inst.start()
