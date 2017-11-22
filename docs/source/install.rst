Install & setup
===============

Before using toxicbuild in our ci process we need to install it and create a
new environment.


Install
+++++++

ToxicBuild is written in Python, and runs in Python3.5 and later. It uses
mongodb to store data and git as vcs. You must have these installed.

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
    Creating root_dir ~/ci/ui
    Username for web access:
    Password for web access:
    Toxicui environment created for web


There are some config values you may want to change. They are:

Toxicmaster config values
-------------------------

The configuration file for toxicmaster is located at
`~/ci/master/toxicmaster.conf`.

Database
^^^^^^^^

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

Email
^^^^^

If you want to be able to send emails containing information about builds,
we need to configure the smpt options.


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


Toxicweb config values
----------------------
The configuration file for toxicmaster is located at
`~/ci/ui/toxicui.conf`.

By default, all dates and times are displayed using the UTC timezone in the
following format: ``'%a %b %d %H:%M:%S %Y %z'``. You can change it using the
``TIMEZONE`` and ``DTFORMAT`` variables.

A list with the format codes can be found `here <http://strftime.org/>`_
and a list of timezones can be found
`here <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_.


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