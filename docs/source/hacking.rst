Hacking ToxicBuild
==================

This is a brief introduction to the internals of ToxicBuild for those
who want to hack it in some way. ToxicBuild is written in python so you
must have some python dev tools, like virtualenv-wrapper and C compiler and
some header files to install it. Other than that, you need a database and
a queue manager - the same you need for the usage. And, finally you need
xvfb and selenium chrome driver for the web tests. In a Debian system the
following command should do the trick:

.. code-block:: sh

   $ sudo apt-get install python3.6-dev build-essential mongodb \
		rabbitmq-server libyaml-dev xvfb chromedriver


Installing from sources
-----------------------

Before we fetch the code, lets create a virtualenv to install our code inside.

.. code-block:: sh

    $ mkvirtualenv toxicbuild -p python3.7
    $ mkdir ~/toxicbuild
    $ cd ~/toxicbuild

You may now clone the code from github:

.. code-block:: sh

    $ git clone https://github.com/jucacrispim/toxicbuild.git src
    $ cd src

And now install python the dependencies:

.. code-block:: sh

    $ pip install -r requirements.txt

Finally, run the tests:

.. code-block:: sh

    $ sh ./build-scripts/run_all_tests.sh


You should see no errors in the tests.


Setting up a development environment
------------------------------------

In the user documentation we saw how to create a new environment using
a code "installed" in your system (or venv). To hack the code is better
to have an environment that is linked to your live code. This is what we
are going to do now.

First, create a few directories for our development environment and link
everything that is needed:

.. code-block:: sh

    $ mkdir ~/toxicbuild/cienv
    $ cd ~/toxicbuild/cienv
    $ ln -s ~/toxicbuild/toxicbuild/toxicbuild toxicbuild
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicbuild ./toxicbuild-script
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicmaster ./toxicmaster
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicslave ./toxicslave
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicintegrations ./toxicintegrations
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicoutput ./toxicoutput
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicpoller ./toxicpoller
    $ ln -s ~/toxicbuild/toxicbuild/script/toxicweb ./toxicweb


Now let's create a working installation.

.. code-block:: sh

   $ ./toxicbuild-script create ci


When everything is ready we can start the componets needed to have a
functional toxicbuild environment:

.. code-block:: sh

    $ ./toxicslave start ./ci/slave --loglevel=debug
    $ ./toxicslave poller ./ci/poller --loglevel=debug
    $ ./toxicoutput start ./ci/output --loglevel=debug
    $ ./toxicintegrations start ./ci/integrations --loglevel=debug
    $ ./toxicmaster start ./ci/master --loglevel=debug
    $ ./toxicweb start ./ci/ui --loglevel=debug


You can use ``--daemonize`` to run the processes as deamons. The following
log files may be interesting:

* ``~/toxicbuild/cienv/master/toxicmaster.log``: Log file for toxicmaster
  instance.
* ``~/toxicbuild/cienv/poller/toxicpoller.log``: Log file for toxicpoller
  instance.
* ``~/toxicbuild/cienv/slave/toxicslave.log``: Log file for toxicslave
  instance.
* ``~/toxicbuild/cienv/output/toxicoutput.log``: Log file for toxicoutput
  instance.
* ``~/toxicbuild/cienv/integrations/toxicintegrations.log``: Log file for
  toxicintegrations instance.


How that works
--------------

ToxicBuild consists in a few moving parts that interact with each other using
the :doc:`ToxicBuild Poor's Protocol <tpp>` (for 'direct' messages from one
part to another) or sending messages using a broker (for async events that may
occour). The differente components of ToxicBuild are:

* Master: Responsible for controlling all the stuff. Manages build queues,
  controlling access to resources and receiving requests from the user
  interface.

* Poller: Responsible for polling changes from the repository and notify
  the master in case of new revisions.

* Slave: Responsible for executing the builds.

* Integrations: Responsible for interacting with 3rd party services.

* Output: Responsible for sending notifications about events.


Writting notification plugins
-----------------------------

Notification plugins are the way toxicbuild sends messages to a third party
service when buildsest start to build or when the builds are done. To
write a new notification plugin you need to extend the
:class:`~toxicbuild.output.notifications.base.Notification` class and
implement the ``send_started_message`` and ``send_finished_message`` methods.
These methods get a ``buildset_info`` param that is a dictionary containing
information about the buildset that started or finished. The notification
instance has also a ``sender`` attribute that is a dictionary for the
repository that owns the buildset.

In your notification class you need also set the following attributes:

* ``name`` - A name for your plugin
* ``pretty_name`` - The name that will be displayed in the user interface
  for the plugin configuration
* ``description`` - A description for your plugin.

You can also create mongomotor fields in your plugin and they will be displayed
in the plugin config.

.. note::

   You can use the fields in the :mod:`~toxicbuild.common.fields` in order
   to use the ``pretty_name`` param that is the name that will be displayed
   in the plugin config.

.. code-block:: python

   from toxicbuild.output.notifications.base import Notification
   from toxicbuild.common.fields import PrettyStringField


   class MyNotification(Notification):

       name = 'my-notification'
       pretty_name = "My super cool notification"
       description = "Sends a message to mars"

       a_config = PrettyStringField(pretty_name='A config value',
                                    required=True)


       async def send_started_message(self, buildset_info):
           self.log('buidset started for repo {}'.format(self.sender['name]))
	   # Do your stuff here

       async def send_finished_message(self, buildset_info):
           self.log('buidset finished for repo {}'.format(self.sender['name]))
	   # Do your stuff here

Now your plugin is done you MUST import it in the
:mod:`toxicbuild.output.notifications.__init__` module. Then restart
the master instance and you should see your plugin in the repositories
notifications config page


Writting slave plugins
----------------------

Slave plugins add steps before and/or after the steps defined by you in your
toxicbuild.conf file. To write slave plugins you must extend
:class:`toxicbuild.slave.plugins.SlavePlugin`. You may implement the methods
``get_steps_before()`` that adds steps before the steps created by you in
your conffile; ``get_steps_after()`` that adds steps after the steps created
by you and ``get_env_vars()`` that adds environment variables to all steps
of your build.

.. code-block:: python

   class MySlavePlugin(SlavePlugin):

       name = 'my-slave-plugin'

       def get_steps_before(self):
           cmd = 'ls -la'
	   name = 'list files'
           my_step = BuildStep(cmd, name)
	   return [my_step]

       def get_step_after(self):
           cmd = 'ls -la'
	   name = 'list files again'
	   my_step = BuildStep(cmd, name)
	   return [my_step]

       def get_env_vars(self):
           return {'PATH': '/opt/bin:PATH'}
