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

from mongomotor.fields import StringField, ListField, URLField


class PrettyFieldMixin:  # pylint: disable=too-few-public-methods
    """A field with a descriptive name for humans"""

    def __init__(self, *args, **kwargs):
        keys = ['pretty_name', 'description']
        for k in keys:
            setattr(self, k, kwargs.get(k))
            try:
                del kwargs[k]
            except KeyError:
                pass

        super().__init__(*args, **kwargs)


class PrettyStringField(PrettyFieldMixin, StringField):
    pass


class PrettyURLField(PrettyFieldMixin, URLField):
    pass


class PrettyListField(PrettyFieldMixin, ListField):
    pass
