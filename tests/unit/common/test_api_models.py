# -*- coding: utf-8 -*-

import datetime
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch
from toxicbuild.common import api_models
from tests import AsyncMagicMock, async_test


class BaseModelTest(TestCase):

    def test_get_ref_cls(self):
        cls = 'toxicbuild.common.api_models.BaseModel'
        model = api_models.BaseModel(MagicMock(), ordered_kwargs={})
        new_cls = model._get_ref_cls(cls)
        self.assertIs(new_cls, api_models.BaseModel)

    def test_attributes_order(self):
        ordered = api_models.OrderedDict()
        ordered['z'] = 1
        ordered['a'] = 2
        requester = MagicMock()
        model = api_models.BaseModel(requester, ordered)
        self.assertLess(model.__ordered__.index('z'),
                        model.__ordered__.index('a'))

    def test_datetime_attributes(self):
        requester = MagicMock()
        model = api_models.BaseModel(requester,
                                     {'somedt': '3 10 25 06:50:49 2017 +0000'})
        self.assertIsInstance(model.somedt, datetime.datetime)

    def test_to_dict(self):
        kw = api_models.OrderedDict()
        kw['name'] = 'bla'
        kw['other'] = 'ble'
        kw['somedt'] = '3 10 25 06:50:49 2017 +0000'
        requester = MagicMock()
        instance = api_models.BaseModel(requester, kw)

        instance_dict = instance.to_dict('%d')

        expected = api_models.OrderedDict()
        expected['name'] = 'bla'
        expected['other'] = 'ble'
        expected['somedt'] = api_models.format_datetime(instance.somedt, '%d')
        self.assertEqual(expected, instance_dict)
        keys = list(instance_dict.keys())
        self.assertLess(keys.index('name'), keys.index('other'))

    def test_to_json(self):
        kw = api_models.OrderedDict()
        kw['name'] = 'bla'
        kw['other'] = 'ble'
        requester = MagicMock()
        instance = api_models.BaseModel(requester, kw)

        instance_json = instance.to_json()

        expected = json.dumps(kw)
        self.assertEqual(expected, instance_json)

    def test_equal(self):
        class T(api_models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = T(id='some-id')
        self.assertEqual(a, b)

    def test_unequal_id(self):
        class T(api_models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = T(id='Other-id')
        self.assertNotEqual(a, b)

    def test_unequal_type(self):
        class T(api_models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        class TT(api_models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = TT(id='some-id')
        self.assertNotEqual(a, b)


class NotificationTest(TestCase):

    def setUp(self):
        self.notification = api_models.Notification
        self.notification.settings = MagicMock()
        self.notification.settings.NOTIFICATIONS_API_TOKEN = 'asdf123'

    def test_get_headers(self):
        expected = {'Authorization': 'token: {}'.format(
            self.notification.settings.NOTIFICATIONS_API_TOKEN)}
        returned = self.notification._get_headers()
        self.assertEqual(expected, returned)

    @patch.object(api_models.requests, 'get', AsyncMagicMock(
        spec=api_models.requests.get))
    @async_test
    async def test_list_no_repo(self):
        r = MagicMock()
        api_models.requests.get.return_value = r
        r.json.return_value = {'notifications': [{'name': 'bla'}]}

        r = await self.notification.list()
        self.assertEqual(r[0].name, 'bla')

    @patch.object(api_models.requests, 'get', AsyncMagicMock(
        spec=api_models.requests.get))
    @async_test
    async def test_list_for_repo(self):
        r = MagicMock()
        obj_id = 'fake-obj-id'
        api_models.requests.get.return_value = r
        r.json.return_value = {'notifications': [{'name': 'bla'}]}

        r = await self.notification.list(obj_id)
        self.assertEqual(r[0].name, 'bla')

    @patch.object(api_models.requests, 'post', AsyncMagicMock(
        spec=api_models.requests.post))
    @async_test
    async def test_enable(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'
        config = {'webhook_url': 'https://somewebhook.url'}
        expected_config = {'webhook_url': 'https://somewebhook.url',
                           'repository_id': obj_id}
        expected_url = '{}/{}'.format(self.notification.api_url(),
                                      notif_name)
        await self.notification.enable(obj_id, notif_name, **config)
        called_url = api_models.requests.post.call_args[0][0]
        called_config = json.loads(
            api_models.requests.post.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)

    @patch.object(api_models.requests, 'delete', AsyncMagicMock(
        spec=api_models.requests.delete))
    @async_test
    async def test_disable(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'
        expected_config = {'repository_id': obj_id}
        expected_url = '{}/{}'.format(self.notification.api_url(),
                                      notif_name)
        await self.notification.disable(obj_id, notif_name)
        called_url = api_models.requests.delete.call_args[0][0]
        called_config = json.loads(
            api_models.requests.delete.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)

    @patch.object(api_models.requests, 'put', AsyncMagicMock(
        spec=api_models.requests.put))
    @async_test
    async def test_update(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'

        expected_url = '{}/{}'.format(self.notification.api_url(),
                                      notif_name)
        config = {'webhook_url': 'https://somewebhook.url'}
        expected_config = {'webhook_url': 'https://somewebhook.url',
                           'repository_id': obj_id}

        await self.notification.update(obj_id, notif_name, **config)
        called_url = api_models.requests.put.call_args[0][0]
        called_config = json.loads(
            api_models.requests.put.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)
