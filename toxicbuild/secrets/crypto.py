# -*- coding: utf-8 -*-
# Copyright 2023 Juca Crispim <juca@poraodojuca.net>

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

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from mongomotor import Document
from mongomotor.fields import StringField, ObjectIdField, BinaryField

from toxicbuild.secrets import settings

KEY_LEN = 256
NONCE_LEN = 96


class Secret(Document):

    owner = ObjectIdField(required=True, unique_with='key')
    key = StringField(required=True, unique_with='owner')
    value = BinaryField(required=True)

    @classmethod
    async def add(cls, owner, key, value):
        inst = cls(owner=owner, key=key)
        encr = inst._encrypt(value)
        inst.value = encr
        await inst.save()
        return inst

    @classmethod
    async def remove(cls, owner, key):
        await cls.objects.filter(owner=owner, key=key).all().delete()

    def to_dict(self):
        d = {'id': str(self.id), 'owner': str(self.owner), 'key': self.key}
        plain = self._decrypt(self.value)
        d['value'] = plain
        return d

    def _encrypt(self, value):
        b = value.encode()
        key = settings.CRYPTO_KEY
        return encrypt(b, key)

    def _decrypt(self, value):
        key = settings.CRYPTO_KEY
        return decrypt(value, key).decode()


def gen_key():
    """Generates a AESGCM key to encrypt/decrypt the secrets
    """

    key = AESGCM.generate_key(bit_length=KEY_LEN)
    return key


def encrypt(data, key):
    """Encrypts ``data`` using ``key`` using the aesgcm algo

    :param data: The data to be encrypted.
    :param key: The encryption key
    """

    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LEN)
    encr = nonce + aesgcm.encrypt(nonce, data, None)
    return encr


def decrypt(data, key):
    """Decrypts ``data`` using ``key``

    :param data: The data encrpyted by :func:`decript`.
    :param key: The decryption key.
    """
    aesgcm = AESGCM(key)
    nonce = data[:NONCE_LEN]
    plain = aesgcm.decrypt(nonce, data[NONCE_LEN:], None)
    return plain
