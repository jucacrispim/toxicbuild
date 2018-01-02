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

from unittest import TestCase
from unittest.mock import Mock, patch
from toxicbuild.master import webhook_receiver
from tests import async_test


class GithubWebhookReceiverTest(TestCase):

    def setUp(self):

        body = webhook_receiver.json.dumps({
            "zen": "Speak like a human.",
            "hook_id": 'ZZZZZ',
            "hook": {
                "type": "App",
                "id": 'XXXXX',
                "name": "web",
                "active": True,
                "events": [
                    "pull_request",
                    "status"
                ],
                "config": {
                    "content_type": "json",
                    "insecure_ssl": "0",
                    "url": "http://ci.poraodojuca.net:9999/github/webhooks/"
                },
                "updated_at": "2018-01-01T04:25:35Z",
                "created_at": "2018-01-01T04:25:35Z",
                "app_id": 'YYYYY'
            }
        })
        request = Mock()
        request.body = body
        request.arguments = {}
        application = Mock()
        application.ui_methods = {}
        self.webhook_receiver = webhook_receiver.GithubWebhookReceiver(
            application, request)

    def test_parse_body(self):
        self.webhook_receiver._parse_body()
        self.assertEqual(
            self.webhook_receiver.body,
            webhook_receiver.json.loads(self.webhook_receiver.request.body))

    def test_check_event_type_zen(self):
        self.webhook_receiver.prepare()
        r = self.webhook_receiver._check_event_type()
        self.assertEqual(r, 'zen')

    @patch.object(webhook_receiver.LoggerMixin, 'log', Mock())
    def test_check_event_type_unknown(self):
        body = webhook_receiver.json.dumps({
            "hook_id": 'ZZZZZ',
            "hook": {
                "type": "App",
                "id": 'XXXXX',
                "name": "web",
                "active": True,
                "events": [
                    "pull_request",
                    "status"
                ],
                "config": {
                    "content_type": "json",
                    "insecure_ssl": "0",
                    "url": "http://ci.poraodojuca.net:9999/github/webhooks/"
                },
                "updated_at": "2018-01-01T04:25:35Z",
                "created_at": "2018-01-01T04:25:35Z",
                "app_id": 'YYYYY'
            }
        })

        self.webhook_receiver.request.body = body
        self.webhook_receiver.prepare()
        r = self.webhook_receiver._check_event_type()
        self.assertEqual(r, 'unknown')

    @patch.object(webhook_receiver.LoggerMixin, 'log', Mock())
    @async_test
    async def test_receive_webhook(self):
        self.webhook_receiver.prepare()
        await self.webhook_receiver.receive_webhook()
        self.assertTrue(self.webhook_receiver.log.called)
