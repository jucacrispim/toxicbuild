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
from mongoengine.base.common import _document_registry
from mongomotor import Document
from mongomotor.fields import StringField
from toxicbuild.master import fields
from toxicbuild.master.plugins import MasterPlugin
from tests import async_test


class HandleUnknownEmbeddedDocumentFieldTest(TestCase):

    @async_test
    async def setUp(self):

        class Embed(MasterPlugin):
            name = 'embed0'
            type = 'test'

            a = StringField()

        class Doc(Document):
            name = 'embed1'
            type = 'test'

            a = StringField()
            el = fields.IgnoreUnknownListField(
                fields.HandleUnknownEmbeddedDocumentField(MasterPlugin))

        self.embed_class = Embed
        self.doc_class = Doc

        self.embed = self.embed_class(a='a')
        self.doc = self.doc_class(a='a')
        self.doc.el.append(self.embed)
        await self.doc.save()

    @async_test
    async def test_list_unknown_embed_doc(self):

        class ToDelete(self.embed_class):
            name = 'embed2'
            type = 'test'

            a = StringField()

        embed = ToDelete(a='a')

        self.doc.el.append(embed)
        await self.doc.save()

        del ToDelete
        del _document_registry['ToDelete']

        doc = await self.doc_class.objects.get(id=self.doc.id)
        self.assertTrue(doc.id)
        self.assertEqual(len(doc.el), 1)
