# -*- coding: utf-8 -*-

# Copyright 2018, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import patch, AsyncMock
from toxicbuild.master import utils
from tests import async_test


class SendEmailTest(TestCase):

    @patch.object(utils.requests, 'post', AsyncMock(
        spec=utils.requests.post))
    @async_test
    async def test_send_email(self):
        await utils.send_email(['a@a.com'], 'subject', 'message')
        self.assertTrue(utils.requests.post.called)
