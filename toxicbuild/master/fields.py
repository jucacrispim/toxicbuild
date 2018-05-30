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


from mongoengine.errors import NotRegistered
from mongomotor.fields import ListField, EmbeddedDocumentField


class IgnoreUnknownListField(ListField):
    """List field that ignores documents that are instances of
    :class:`~toxicbuild.master.fields.DocPlaceHolder` by simply
    excluding them from the result list."""

    def to_python(self, value):
        r = super().to_python(value)
        return [d for d in r if not isinstance(d, DocPlaceHolder)]


class DocPlaceHolder:
    """A simple placeholder for"""

    def __init__(self, value):
        self.value = value


class HandleUnknownEmbeddedDocumentField(EmbeddedDocumentField):
    """The idea of this class is to handle documents which the class is
    not registered in the class registry. When this happens, the
    value is a generic class,
    :class:`~toxicbuild.master.fields.DocPlaceHolder`"""

    def to_python(self, value):
        try:
            value = super().to_python(value)
        except NotRegistered:
            value = DocPlaceHolder(value)
        return value
