# -*- coding: utf-8 -*-


class UIFunctionNotFound(Exception):
    pass


class CloneException(Exception):
    pass


class DBError(Exception):
    pass


class NotEnoughPerms(Exception):
    pass


class OwnerDoesNotExist(Exception):
    pass


class InvalidCredentials(Exception):
    pass
