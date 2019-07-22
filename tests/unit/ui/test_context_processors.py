# -*- coding: utf-8 -*-

# Copyright 2015, 2018 Juca Crispim <juca@poraodojuca.net>

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


from unittest import TestCase, mock
from toxicbuild.ui import context_processors


class ToxicWebMainContextProcessorTest(TestCase):

    @mock.patch.object(context_processors, 'settings', mock.Mock())
    def test_get_context(self):
        context_processors.settings.HOLE_HOST = 'localhost'
        context_processors.settings.HOLE_PORT = 1234
        processor = context_processors.ToxicWebMainContextProcessor(
            mock.Mock())
        context = processor.get_context()

        self.assertIn('master_location', context.keys())


class ToxicWebTranslationProcessorTest(TestCase):

    def setUp(self):
        request = mock.Mock()
        morsel = mock.Mock()
        morsel.value = 'pt_BR'
        request.cookies = {'ui_locale': morsel}
        self.processor = context_processors.ToxicWebTranslationProcessor(
            request)

    @mock.patch.object(context_processors.locale, 'get', mock.Mock())
    def test_get_context(self):
        expected_keys = {'translate'}
        r = set(self.processor.get_context().keys())

        self.assertEqual(r, expected_keys)

    @mock.patch.object(context_processors.locale, 'get', mock.Mock())
    def test_get_context_missing(self):
        expected_keys = {'translate'}
        self.processor.request.cookies = {}
        r = set(self.processor.get_context().keys())

        self.assertEqual(r, expected_keys)
