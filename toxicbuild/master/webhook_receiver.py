# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import json
from pyrocumulus.web.decorators import post
from pyrocumulus.web.handlers import BasePyroHandler
from toxicbuild.core.utils import LoggerMixin


class GithubWebhookReceiver(LoggerMixin, BasePyroHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type = None
        self.body = None

    def prepare(self):
        super().prepare()
        self._parse_body()
        self.event_type = self._check_event_type()

    @post('auth')
    async def authenticate(self):
        pass

    @post('webhooks')
    async def receive_webhook(self):
        if self.event_type == 'zen':
            msg = 'zen: {}'.format(self.body['zen'])
            self.log(msg, level='debug')

    def _parse_body(self):
        self.body = json.loads(self.request.body)

    def _check_event_type(self):
        if 'zen' in self.body.keys():
            r = 'zen'
        else:
            msg = 'Unknow event type\n{}'.format(self.body)
            self.log(msg, level='warning')
            r = 'unknown'

        return r
