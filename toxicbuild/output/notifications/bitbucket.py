# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from mongomotor.fields import ReferenceField
import requests

from toxicbuild.integrations.bitbucket import BitbucketIntegration

from toxicbuild.output import settings
from .base import Notification


class BitbucketCommitStatusNotification(Notification):
    """Sends commit status information to bitbucket when
    a build is added, started or finished.
    """

    name = 'bitbucket-commit-status'
    events = [
        'build-started',
        'build-finished',
        'build-cancelled'
    ]
    no_list = True

    installation = ReferenceField(BitbucketIntegration)

    async def run(self, build_info):
        self.log('Sending build status to bitbucket', level='debug')
        sender = build_info['repository']
        installation = await self.installation
        url = settings.BITBUCKET_API_URL + \
            'repositories/{}/commit/{}/statuses/build'.format(
                sender['external_full_name'], build_info['named_tree'])
        self.log('With url: {}'.format(url))
        state_tb = {
            'running': 'INPROGRESS',
            'success': 'SUCCESSFULL',
            'cancelled': 'STOPPED',
            'warning': 'FAILED',
            'exception': 'FAILED',
            'fail': 'FAILED',
        }
        state = state_tb[build_info['status']]

        data = {
            'uuid': build_info['uuid'],
            'key': build_info['builder']['name'],
            'name': '{}-{}'.format(build_info['builder']['name'],
                                   build_info['number']),
            'state': state,
            'description': 'Toxicbuild tests',
        }

        headers = await installation.get_headers()
        await requests.post(url, json=data, headers=headers)
        return True
