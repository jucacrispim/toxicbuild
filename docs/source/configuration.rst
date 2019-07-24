Configuration
=============

These are the config values you may want to change:

General configs
+++++++++++++++

Toxicmaster config values
-------------------------

Database
~~~~~~~~

Set the following environment variables to configure the database.

* ``DBHOST`` - Defaults to `localhost`.
* ``DBPORT`` - Defaults to `27017`.
* ``DBNAME`` - Defaults to `toxicbuild`.
* ``DBUSER``
* ``DBPASSWORD``


Queue Manager
~~~~~~~~~~~~~

The queue manager is configured by the following environment variables:

* ``AMQPHOST`` - Defaults to `localhost`
* ``AMQPPORT`` - Defaults to `5672`
* ``AMQPLOGIN``
* ``AMQPPASSWORD``
* ``AMQPVIRTUALHOST``


Coordination
~~~~~~~~~~~~

The coordination of all the stuff in ToxicBuild in done using ZooKeeper.
The environment variables are:

* ``ZK_SERVERS`` - User a string like `host:port`. Multiple servers
  can be passed using a comma, eg: `host1:1234,host2:4321`
* ``ZK_KWARGS`` - A json with arguments to aiozk.ZKClient, eg:
  `"{'chroot': '/somewhere'}"`. The valid arguments are:

  - chroot
  - session_timeout=10,
  - default_acl
  - retry_policy
  - allow_read_only
  - read_timeout


Secure connections
~~~~~~~~~~~~~~~~~~

To use secure connections, you must set the following environment variables:

* ``MASTER_USE_SSL`` - Set its value to `1`
* ``MASTER_CERTFILE`` - Path for a cert file
* ``MASTER_KEYFILE`` - Path for a key file


Notifications
~~~~~~~~~~~~~

Set the following variables to configure the notifications

* ``NOTIFICATIONS_API_URL``
* ``NOTIFICATIONS_API_TOKEN``


Other config values
~~~~~~~~~~~~~~~~~~~

The following config values usually don't need to be changed.

* ``HOLE_PORT`` - The port in which master listen to connections.
* ``SOURCE_CODE_DIR`` - The directory where the source code is cloned.


.. _toxicoutput-config:

Toxicoutput config values
-------------------------

Database
~~~~~~~~

Set the following environment variables to configure the database.

* ``DBHOST`` - Defaults to `localhost`.
* ``DBPORT`` - Defaults to `27017`.
* ``DBNAME`` - Defaults to `toxicbuild`.
* ``DBUSER``
* ``DBPASSWORD``


Queue manager
~~~~~~~~~~~~~

The queue manager is configured by the following environment variables:

* ``AMQPHOST`` - Defaults to `localhost`
* ``AMQPPORT`` - Defaults to `5672`
* ``AMQPLOGIN``
* ``AMQPPASSWORD``
* ``AMQPVIRTUALHOST``


Email
~~~~~

If you want to be able to send emails containing information about builds,
you need to configure the smpt options.

* ``SMTP_MAIL_FROM``
* ``SMTP_HOST``
* ``SMTP_PORT``
* ``SMTP_USERNAME``
* ``SMTP_PASSWORD``

The next options indicate if we should use a secure connection and if we should
validate the certificate.

* ``SMTP_STARTTLS`` - Possible values are: `0` or `1`
* ``SMTP_VALIDATE_CERTS`` - Possible values are: `0` or `1`


Commit statuses to custom GitLab installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you use a custom installation of GitLab you need to change the following
variable in order to have the build status informed to your GitLab install:

* ``GITLAB_URL`` - The default value is `https://gitlab.com/`


Other config values
~~~~~~~~~~~~~~~~~~~

The following configuration values usually don't need to be changed:

* ``GITHUB_API_URL`` - Defaults to `https://api.github.com/`
* ``OUTPUT_WEB_PORT`` - Defaults to 9432


Toxicintegrations config values
-------------------------------

Database
~~~~~~~~

Set the following environment variables to configure the database.

* ``DBHOST`` - Defaults to `localhost`.
* ``DBPORT`` - Defaults to `27017`.
* ``DBNAME`` - Defaults to `toxicbuild`.
* ``DBUSER``
* ``DBPASSWORD``


Queue manager
~~~~~~~~~~~~~

The queue manager is configured by the following environment variables:

* ``AMQPHOST`` - Defaults to `localhost`
* ``AMQPPORT`` - Defaults to `5672`
* ``AMQPLOGIN``
* ``AMQPPASSWORD``
* ``AMQPVIRTUALHOST``


Notifications
~~~~~~~~~~~~~

Set the following variables to configure the notifications

* ``NOTIFICATIONS_API_URL``
* ``NOTIFICATIONS_API_TOKEN``


Secure cookies
~~~~~~~~~~~~~~

Set the following variable to configure the secure cookies.

* ``COOKIE_SECRET`` - This value MUST be the same used for toxicui.


Other config values
~~~~~~~~~~~~~~~~~~~
* ``TOXICUI_URL`` - A url pointing to your toxicui installation
* ``INTEGRATIONS_WEB_PORT``
* ``PARALLEL_IMPORTS`` - how many repos will be imported at the same time by
  the same user



Toxicweb config values
----------------------

These are the following  variables are the ones you can use to configure your
toxicweb  environment.

* ``HOLE_HOST`` - The server where the master is
* ``HOLE_PORT`` - The port which master is listening.
* ``WEB_UI_PORT`` - The port for the webserver. Defaults to `8888`
* ``NOTIFICATIONS_API_URL``
* ``MASTER_USES_SSL`` - Indicates if the connection to toxicmaster is secure.
  Defaults to `0`. Possible values are `0` and `1`.
* ``VALIDATE_CERT_MASTER``. Indicates if we should validate the master ssl
  certificate. Possible values are `0` and `1`.
* ``GITHUB_IMPORT_URL`` - The url to import your github repositories. See
  :ref:`github-integration-config`
* ``GITLAB_IMPORT_URL`` - The url to import your gitlab repositories. See
  :ref:`gitlab-integration-config`


Toxicslave config values
------------------------

Change the following environment variables to configure toxicslave:

* ``SLAVE_PORT`` - Defaults to `7777`
* ``SLAVE_USE_SSL`` - Defaults to `0`. Possible values are `0` or `1`.
* ``SLAVE_CERTIFILE`` - Path for a certificate file.
* ``SLAVE_KEYFILE`` - Path for a key file.


Running builds inside docker containers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to run builds inside docker containers so each time we
run a build it is executed in a new environment. So, lets say you have
the following Dockerfile and you will tag the image as `my-deb-slim`:

.. code-block:: sh

   FROM	debian:buster-slim

   # You MUST to create a user in your image as we don't want to run tests
   # as  root. You may create a user with sudo if you want.
   RUN useradd -ms /bin/bash toxicuser
   USER toxicuser
   WORKDIR /home/toxicuser


Then you must to set the following environment variables:

* ``SLAVE_USE_DOCKER`` - Set its value to `1`
* ``SLAVE_DOCKER_IMAGES`` - This value is a json mapping platform names to
  docker image names e.g: `"{'debian-generic': 'my-deb-slim'}"`
* ``SLAVE_CONTAINER_USER`` - The name of the user you created in your image.


And thats it. Your builds will run inside docker containers.

.. _github-integration-config:

Integration with Github
+++++++++++++++++++++++

If you want to integrate toxicbuild with github you need a few steps

Create a Github app on Github
-----------------------------

To create a new Github App, go to ``https://github.com/settings/apps`` and
click in ``New GitHub App``. In the app page, fill the
``User authorization callback URL`` and the ``setup URL`` with
`<your-integrations-server>:9999/github/auth`. Set the ``Webhook URL`` to
`<your-integrations-server>:9999/github/webhooks`. Fill the ``Webhook secret``
with a unique random string.

Generate a private key in the Github interface and save the file.

In the permissions page, give the following permissions to your app.

* read-only to Repository contents
* read-only to Repository metadata
* read-only to Pull requests
* read & write to Checks

Subscribe to the following events:

* Push
* Repository
* Pull request
* Status
* Check run

Now we're done in the Github side. Let's configure ToxicBuild.


Toxicbuild Configuration
------------------------

In your toxicintegrations environment set the following variables

* ``GITHUB_PRIVATE_KEY`` - Path for your github private key
* ``GITHUB_APP_ID`` - The id of your Github application
* ``GITHUB_WEBHOOK_TOKEN`` - The same webhook secret set in the github app
  creation.

In your toxicui environmen set the following variables:

* ``GITHUB_IMPORT_URL`` - https://github.com/apps/<app-name>/installations/new

.. note::

   <app-name> is the name you gave to your github app.


.. _gitlab-integration-config:

Integration with Gitlab
+++++++++++++++++++++++

To integrate with GitLab you also need to create an app and then configure
ToxicBuild.


Create a Gitlab app on Gitlab
-----------------------------

Go to ``https://gitlab.com/profile/applications`` and fill the name field with
`ToxicBuild` and the field ``redirect URI`` with
`<your-integrations-server>:9999/gitlab/setup`. In the scopes section
check ``api`` and save the application. Copy and save the ``Application ID``
and ``Secret`` shown.


Toxicbuild Configuration
------------------------

In your toxicintegrations environment set the following variables:

* ``GITLAB_APP_ID``
* ``GITLAB_APP_SECRET``
* ``GITLAB_WEBHOOK_TOKEN``

In your toxicui set the following:

* ``GITLAB_IMPORT_URL`` - 'https://gitlab.com/oauth/authorize?client_id=<app_id>&redirect_uri=<redirect-url>&response_type=code&state={state}'

.. note::

   ``GITLAB_APP_ID`` and ``GITLAB_APP_SECRET`` are the ones you got from
   gitlab. ``GITLAB_WEBHOOK_TOKEN`` must be a unique string. <redirect-url>
   must be the same as in the gitlab app.


.. _ec2-integration:

Integration with Amazon ec2
+++++++++++++++++++++++++++

Toxicbuild can start/stop ec2 on-demand instances, saving costs on builds
machines.

Your first need to :ref:`install toxicslave <toxicslave-install>` in a ec2
instance. Don't forget to setup supervisor.

Then you need to create a key pair in the amazon console and in your
toxicmaster envionment set the following variables:

* ``AWS_ACCESS_KEY_ID``
* ``AWS_SECRET_ACCESS_KEY``

And finally :ref:`add an on demand slave <add-ec2-slave>`
