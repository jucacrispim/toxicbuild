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

from collections import defaultdict

from mongomotor.fields import ReferenceField

from toxicbuild.core import requests
from toxicbuild.core.utils import string2datetime, datetime2string
from toxicbuild.integrations.github import GithubIntegration

from toxicbuild.output import settings

from .base import Notification


class GithubCheckRunNotification(Notification):
    """A plugin that creates a check run reacting to a buildset that
    was added, started or finished."""

    name = 'github-check-run'
    """The name of the plugin"""

    events = ['buildset-added', 'buildset-started', 'buildset-finished']
    """Events that trigger the plugin."""

    no_list = True

    run_name = 'ToxicBuild CI'
    """The name displayed on github."""

    installation = ReferenceField(GithubIntegration)
    """The :class:`~toxicbuild.integrations.github.GithubIntegration`
    that owns the notification. It is needed because each installation has
    its own auth token and it is needed send the checks.
    """

    async def run(self, buildset_info):
        """Executed when a notification about a build arrives. Reacts
        to buildsets that started or finished.

        :param buildset_info: A dictionary with information about a buildset.
        """

        self.log('Sending notification to github for buildset {}'.format(
            buildset_info['id']), level='info')
        self.log('Info is: {}'.format(buildset_info), level='debug')

        self.sender = buildset_info['repository']
        status = buildset_info['status']
        status_tb = defaultdict(lambda: 'completed')

        status_tb.update({'pending': 'queued',
                          'running': 'in_progress'})
        run_status = status_tb[status]

        conclusion_tb = defaultdict(lambda: 'failure')
        conclusion_tb.update({'success': 'success'})
        conclusion = conclusion_tb[status]

        await self._send_message(buildset_info, run_status, conclusion)

    def _get_payload(self, buildset_info, run_status, conclusion):

        payload = {'name': self.run_name,
                   'head_branch': buildset_info['branch'],
                   'head_sha': buildset_info['commit'],
                   'status': run_status}

        started_at = buildset_info.get('started')
        if started_at:
            dt = string2datetime(started_at)
            started_at = datetime2string(
                dt, dtformat="%Y-%m-%dT%H:%M:%S%z")

            started_at = started_at.replace('+0000', 'Z')
            payload.update({'started_at': started_at})

        if run_status == 'completed':
            dt = string2datetime(buildset_info['finished'])
            completed_at = datetime2string(
                dt, dtformat="%Y-%m-%dT%H:%M:%S%z")

            completed_at = completed_at.replace('+0000', 'Z')
            payload.update(
                {'completed_at': completed_at,
                 'conclusion': conclusion})

        return payload

    async def _send_message(self, buildset_info, run_status, conclusion):
        full_name = self.sender['external_full_name']
        install = await self.installation
        url = settings.GITHUB_API_URL + 'repos/{}/check-runs'.format(
            full_name)

        self.log('sending check for {} buildset {}'.format(
            url, buildset_info['id']), level='debug')

        payload = self._get_payload(buildset_info, run_status, conclusion)

        header = await install.get_header(
            accept='application/vnd.github.antiope-preview+json')
        r = await requests.post(url, headers=header, json=payload)

        self.log('response from check for buildset {} - status: {}'.format(
            buildset_info['id'], r.status), level='debug')
        self.log(r.text, level='debug')
