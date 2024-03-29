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

# You shoud have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=all

__doc__ = """This package implements toxicbuild integrations with code
hosting services using the oauth2 protocol.

To implement a new integration you must extend the following classes:
:class:`~toxicbuild.integrations.base.BaseIntegration`,
:class:`~toxicbuild.integrations.base.BaseIntegrationApp` and
:class:`~toxicbuild.integrations.webhook_receivers.BaseWebhookReceiver`.

Check the documentation for each class for more information.
"""

from toxicbuild.core.conf import Settings

ENVVAR = 'TOXICINTEGRATIONS_SETTINGS'
DEFAULT_SETTINGS = 'toxicintegrations.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


def ensure_indexes():
    from .github import GithubApp, GithubIntegration
    from .gitlab import GitlabApp, GitlabIntegration
    from .bitbucket import BitbucketApp, BitbucketIntegration

    GithubApp.ensure_indexes()
    GithubIntegration.ensure_indexes()
    GitlabApp.ensure_indexes()
    GitlabIntegration.ensure_indexes()
    BitbucketApp.ensure_indexes()
    BitbucketIntegration.ensure_indexes()
