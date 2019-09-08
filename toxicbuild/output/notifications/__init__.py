# -*- coding: utf-8 -*-
"""This package implements notifications for repositories. Notifications are
triggered by messages published in the notifications exchange.

To implement your own notifications you must to subclass
:class:`~toxicbuild.output.notifications.Notification` and implement a
``send_message`` method.

The class :class:`~toxicbuild.output.notifications.Notification` is a
mongomotor document that you can subclass and create your own fields to store
the notification config params. It already has the following fields:

- branches: A list of branch names that triggers the plugin.
- statuses: A list of statuses that triggers the plugin.

Example:
^^^^^^^^

.. code-block:: python

    from mongomotor.fields import StringField
    from toxicbuild.output.notifications import Notification

    class MyNotification(Notification):

        # you must define name
        name = 'my-notification'

        # optionally you may define pretty_name and description
        pretty_name = "My Plugin"
        description = "A very cool plugin"

        something_to_store_on_database = PrettyStringField()

        async def run(self, info):
            '''Here is where you implement your stuff.

            :param info: A dictionary with some information for the
              plugin to handle.'''

"""

from .base import Notification  # noqa
from .github import GithubCheckRunNotification  # noqa
from .gitlab import GitlabCommitStatusNotification  # noqa

# The order of the imports here is the order the notifications will be
# displayed in the ui.
from .slack import SlackNotification  # noqa
from .email import EmailNotification  # noqa
from .custom_webhook import CustomWebhookNotification  # noqa
