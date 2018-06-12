Notifications
=============

.. _notifications:

Notifications are the way ToxicBuild sends messages about builds using a given
notification method. All notification methods have the following common
parameters:

|notification-methods-img|

.. |notification-methods-img| image:: ./_static/notification-methods.png
    :alt: Notification methods


- ``Branches``: Which branches may trigger the notification method. This is
  a list. The values are coma-separated.
- ``Statuses``: Which statuses may trigger the notification method. This is
  a list. The values are coma-separated.

Email notification
++++++++++++++++++

Sends notifications using email. This method have the following parameters:

.. note::

   To use this notification method you must configure the smtp parameters
   in toxicmaster.

- ``Recipients``: Email addresses that will receive messages. This is a list.
  The values are coma-separated.


Slack notification
++++++++++++++++++

Sends notifications to a slack channel. This method have the following
parameters:

- ``Webhook URL``: The url for the slack webhook.
- ``Channel name``: The name of the slack channel.


Custom webhook notification
+++++++++++++++++++++++++++

Sends notifications to a custom webhook. This method have the following
parameters:

- ``Webhook URL``: The url for the webhook. This method sends a post request
  the the webhook url. The body of the request is a json with 3 keys:
  ``repository``, ``build`` and ``buildset``.


Now we have a repository in ToxicBuild, we need to configure a build and this
is done creating a configfile called `toxicbuild.conf` in the root directory
of your repository.
