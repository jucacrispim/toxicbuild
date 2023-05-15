# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import patch, Mock, AsyncMock

from toxicbuild.integrations.notifications import bitbucket

from tests import async_test


@patch.object(bitbucket, 'settings', Mock(
    BITBUCKET_API_URL='https://api.bb.org'))
class BitbucketCommitStatusNotificationTest(TestCase):

    def setUp(self):
        install = bitbucket.BitbucketIntegration()
        self.notification = bitbucket.BitbucketCommitStatusNotification(
            installation=install)

    @patch.object(bitbucket.BitbucketIntegration, 'get_headers',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.get_headers))
    @patch.object(bitbucket.requests, 'post', AsyncMock(
        spec=bitbucket.requests.post))
    @async_test
    async def test_run(self):
        build_info = {
            'repository': {
                'external_full_name': 'user/repo'
            },
            'builder': {
                'name': 'the-builder'
            },
            'number': 1,
            'uuid': 'the-uuid',
            'status': 'running',
            'named_tree': 'the-sha',
        }

        await self.notification.run(build_info)

        self.assertTrue(bitbucket.BitbucketIntegration.get_headers.called)
        self.assertTrue(bitbucket.requests.post.called)
