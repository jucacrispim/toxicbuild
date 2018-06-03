Install & setup
===============

Before using toxicbuild in our ci process we need to install it and create a
new environment.


Install
+++++++

ToxicBuild is written in Python, and runs in Python3.5 and later. It uses
mongodb to store data, rabbitmq for queues and git as vcs.
You must have these installed.

.. note::

   These are the external programs used by ToxicBuild, but to install the
   code dependencies you may need a C compiler and the header files for your
   Python interpreter and for libffi. In a Debian system install the packages
   ``build-essential``, ``libffi-dev`` and ``pythonX.Y-dev``, where X.Y is the
   version of your interpreter.

After the installation of the external dependencies you can install toxicbuild
using pip:

.. code-block:: sh

   $ pip install toxicbuild


And that's it. ToxicBuild is installed.


Setup
+++++

First we need to create a new environment for our continuous integration.
This is done using the command ``toxicbuild create``.

.. code-block:: sh

    $ toxicbuild create ~/ci
    Creating root_dir ~/ci/slave for toxicslave
    Toxicslave environment created with access token: ...
    Creating root_dir ~/ci/master for toxicmaster
    Toxicmaster environment created with access token: ...
    Creating user for authenticated access
    email:
    password:
    User created successfully
    Creating root_dir ~/ci/ui
    Toxicui environment created for web


.. note::

   Here a super user was created. If you want create more users you can use
   the ``toxicmaster create_user`` command.


General configs
----------------

There are some config values you may want to change. They are:

.. note::

   If you installed mongodb and rabbitmq on localhost with default configs
   you may not need to change these general configs. You may skip to
   :ref:`docker-config`.

Toxicmaster config values
^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration file for toxicmaster is located at
`~/ci/master/toxicmaster.conf`.

Basic stuff
~~~~~~~~~~~

.. code-block:: python

   # Address from which address the master should accept connections.
   # If '0.0.0.0' accepts connections from everywhere.
   HOLE_ADDR = '127.0.0.1'
   # Port for the master to listen.
   HOLE_PORT = 1111


Database
~~~~~~~~

You can change the database connection parameters changing the
`DATABASE` parameter:

.. code-block:: python

   DATABASE = {'host': 'localhost',
	       'port': 27017,
               'db': 'toxicmaster'}

For authentication, add the `username` and `password` keys:

.. code-block:: python

   DATABASE = {'host': 'localhost',
	       'port': 27017,
               'db': 'toxicmaster',
	       'username': 'db-user',
	       'password': 'db-password'}

Queue Manager
~~~~~~~~~~~~~

ToxicBuild uses Rabbitmq as queue manager. Use the `RABBITMQ_CONNECTION`
settings to configure it:

.. code-block:: python

   RABBITMQ_CONNECTION = {'host': 'localhost', 'port': 5672}


Secure connections
~~~~~~~~~~~~~~~~~~

To use secure connections, you must set the following parameters:

.. code-block:: python

   USE_SSL = True
   CERTFILE = '/path/to/a/file.cert'
   KEYFILE = '/path/to/a/file.key'



ToxicOutput config values
^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration file for toxicmaster is located at
`~/ci/output/toxicoutput.conf`.


Database and Queue Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~

The database and queue manager configurations MUST be the same as the ones
used in the master configuration


Email
~~~~~

If you want to be able to send emails containing information about builds,
you need to configure the smpt options.


.. code-block:: python

   SMTP_MAIL_FROM = 'test@toxictest.com'
   SMTP_HOST = 'localhost'
   SMTP_PORT = 587
   SMTP_USERNAME = 'test@toxictest.com'
   SMTP_PASSWORD = 'some-strong-password'
   # Should we validade the certificate? If your certificate is self signed
   # this should be False
   SMTP_VALIDATE_CERTS = True
   SMTP_STARTTLS = False

ToxicIntegrations config values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

General configs
~~~~~~~~~~~~~~~

.. code-block:: python

   # indicates which port the integrations server listens.
   TORNADO_PORT = 9999
   # how many repos will be imported at the same time by the same user
   PARALLEL_IMPORTS = 1


Database and queue managers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The database and queue manager configurations MUST be the same as the ones
used in the master configuration



Toxicweb config values
^^^^^^^^^^^^^^^^^^^^^^
The configuration file for toxicui is located at
`~/ci/ui/toxicui.conf`.

By default, all dates and times are displayed using the UTC timezone in the
following format: ``'%a %b %d %H:%M:%S %Y %z'``. You can change it using the
``TIMEZONE`` and ``DTFORMAT`` variables.

A list with the format codes can be found `here <http://strftime.org/>`_
and a list of timezones can be found
`here <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_.

If the master uses ssl connection, you must set following parameters

.. code-block:: python

   MASTER_USES_SSL = True
   VALIDATE_CERT_MASTER = True


Toxicslave config values
^^^^^^^^^^^^^^^^^^^^^^^^
The configuration file for toxicslave is located at
`~/ci/slave/toxicslave.conf`.


If you want to use a ssl connection, set the following config params:

.. code-block:: python

   USE_SSL = True
   CERTFILE = '/path/to/a/file.cert'
   KEYFILE = '/path/to/a/file.key'


.. _docker-config:

Running builds in docker containers
-----------------------------------

It is possible to run builds inside docker containers so each time we
run a build it is executed in a new environment. The most important thing
is to have a docker image that runs a toxicslave instance. This image will
be used as base to the container that will execute the build. Here is an
example of a Dockerfile that installs and runs a toxicslave instance.

.. code-block:: sh

   FROM debian:9.2
   RUN apt-get update && apt-get install -y build-essential \
		                            python3.5 python3.5-dev
   # we must have a 'python' exec
   RUN ln -s /usr/bin/python3 /usr/bin/python
   RUN pip3 install toxicbuild
   RUN toxicslave create /opt/slave
   # This must be done, otherwise the builds will end in exception
   RUN mkdir /opt/slave/src
   # preciso por a parte das configs aqui
   # Here you copy the config for the container's slave, with
   # the USE_DOCKER = False.
   # The USE_DOCKER param is for the slave outside the container.
   CMD [ "/usr/bin/toxicslave", "start", "/opt/slave" ]

After your image is ready, in the toxicslave config file you must set the
following variables:

.. code-block:: python

   USE_DOCKER = True
   # here you need at least the linux-generic image, this is the default.
   # You can change the image used in your build by using the ``platform``
   # parameter in the builder configuration.
   DOCKER_IMAGES = {'linux-generic': 'my-image-name',
                    'python3.6': 'my-py36-image'}
   CONTAINER_SLAVE_WORKDIR = '/opt/slave'
   CONTAINER_SLAVE_PORT = 7777
   CONTAINER_SLAVE_TOKEN = 'slave-token'

And thats it. Your builds will run inside docker containers.

.. _github-integration-config:

Integration with Github
-----------------------

Create a Github app on Github
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To integrate with Github you first need to create a Github App. To do so, go to
`https://github.com/settings/apps` and click in `New GitHub App`. In the app
page, fill the `User authorization callback URL` and the `setup URL` to
`<your-integrations-server>:9999/github/auth`. Set the `Webhook URL` to
`<your-integrations-server>:9999/github/webhooks`. Fill the `Webhook secret`
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
^^^^^^^^^^^^^^^^^^^^^^^^

In your `toxicintegrations.conf` set the following parameters.

.. code-block:: python

   GITHUB_PRIVATE_KEY = '/the/path/to/your/github-private.key'
   # The id of your github. You can see it in your app page on github
   GITHUB_APP_ID = 666
   # The secret string you put in the Webhook secret field in github
   GITHUB_WEBHOOK_TOKEN = 'secret-token'
   TOXICUI_LOGIN_URL = '<your-toxicui-sever>/login/'
   TOXICUI_URL = '<your-toxicui-sever>'


In your `toxicui.conf` set the following parameters:

.. code-block:: python

   GITHUB_IMPORT_URL = 'https://github.com/apps/<app-name>/installations/new'


Starting toxicbuild
+++++++++++++++++++

After the environment is created, use the command ``toxicbuld start`` to
start everything needed.

.. code-block:: sh

    $ toxicbuild start ~/ci
    Starting toxicslave
    Starting toxicmaster
    Starting tornado server on port 8888

And now access http://localhost:8888 in your browser. Use the username and
password supplied in the create process to access the web interface.
