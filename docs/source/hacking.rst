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

    $ mkvirtualenv toxicbuild -p python3.6
    $ mkdir ~/hacks
    $ cd ~/hacks

You may now clone the code from github:

.. code-block:: sh

    $ git clone https://github.com/jucacrispim/toxicbuild.git
    $ cd toxicbuild

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

First, create a directory for our development environment and link
everything that is needed:

.. code-block:: sh

    $ mkdir ~/hacks/cienv
    $ cd ~/hacks/cienv
    $ ln -s ~/hacks/toxicbuild/toxicbuild toxicbuild
    $ ln -s ~/hacks/toxicbuild/script/toxicmaster ~/hacks/cienv/toxicmaster
    $ ln -s ~/hacks/toxicbuild/script/toxicslave ~/hacks/cienv/toxicslave
    $ ln -s ~/hacks/toxicbuild/script/toxicintegrations ~/hacks/cienv/toxicintegrations
    $ ln -s ~/hacks/toxicbuild/script/toxicoutput ~/hacks/cienv/toxicoutput
    $ ln -s ~/hacks/toxicbuild/script/toxicweb ~/hacks/cienv/toxicweb

When everything is ready we can start the componets needed to have a
functional toxicbuild environment:

.. code-block:: sh

    $ ~/hacks/toxicbuild start ~/hacks/cienv/ --loglevel=debug


The following log files may be interesting:

* ``~/hacks/cienv/master/toxicmaster.log``: Log file for toxicmaster instance.
* ``~/hacks/cienv/master/toxicpoller.log``: Log file for toxicpoller instance.
* ``~/hacks/cienv/master/toxicscheduler.log``: Log file for toxicscheduler
  instance.
* ``~/hacks/cienv/slave/toxicslave.log``: Log file for toxicslave instance.
* ``~/hacks/cienv/output/toxicoutput.log``: Log file for toxicoutput instance.
* ``~/hacks/cienv/integrations/toxicintegrations.log``: Log file for
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

* Scheduler: Responsible for periodicaly asking for the poller to check for
  new changes. Used only by repositories imported manualy.

* Slave: Responsible for executing the builds.

* Integrations: Responsible for interacting with 3rd party services.

* Output: Responsible for sending notifications about events.


Master
------

The responsible for controlling everything. When it detects new revisions
notified by the poller, new builds and bildsets are created for them.

When the master is notified by poller - throught the revisions_added exchange -
that new revisions arrived it creates new buildsets and builds for the
revisions. Then, the :class:`~toxicbuild.master.build.BuildManager` is
responsible for requesting a build to the slave.

It also has some plugins (:mod:`toxicbuild.master.plugins`) that are, at the
moment, used to send information about builds to different places, like e-mail
notification or integration with 3rd party systems like slack.


Writting master plugins
+++++++++++++++++++++++

.. warning::

   This module is out of place here. In the version 0.4 the output module
   didn't exist, so the notification plugins were master plugins. It changed
   in 0.5, but the code still lives in the master. That is going to change
   in version 0.6.

To write master plugins is quite simple. In the
:mod:`toxicbuild.master.plugins` module, you must subclass
:class:`toxicbuild.master.plugins.MasterPlugin` and implement a ``run()``
method. Optionaly you may implement a ``stop()`` method too. Both are
coroutines.

.. code-block:: python

   class MyPlugin(MasterPlugin):

       # These are required for every plugin
       name = 'my-plugin'
       pretty_name = 'My Plugin'
       description = 'Do some nice stuff'
       type = 'some-plugin-type'

       # If you need to store config values in database, you can
       # create them here
       some_config = PrettyStringField(pretty_name='Some Config',
		                       required=True)


       async def run(self, sender):
           """Do your stuff here. Connect to signals and do something
           in reaction to them."""

       async def stop(self):
           """Disconnect from signals here."""


To make things easier, we already have
:class:`toxicbuild.master.plugins.NotificationPlugin` that reacts to
``build_started`` and ``build_finished`` signals. To write a notification
plugin, subclass :class:`toxicbuild.master.plugins.NotificationPlugin` and
implement ``send_started_message`` and ``send_finished_message`` methods.

.. code-block:: python

   class MyNotificationPlugin(NotificationPlugin):

       name = 'my-notification-plugin'
       pretty_name = 'My Notification Plugin'
       description = 'Sends messages to somewhere'
       type = 'notification'

       async def send_started_message(self, repo, build):
           """Sends a message informing about a build that has jsut
	   started."""

       async def send_finished_message(self, repo, build):
           """Sends a message informing about a build that has jsut
           finished."""


..
   Master signals
   ++++++++++++++

   The following signals are sent in master:

   * revision_added - Sent when changes are detected in the source code.
   * build_added - Sent when a new build is added to the database.
   * build_started - Sent when a build starts.
   * build_finished - Sent when a build finishes.
   * step_started - Sent when a build step starts
   * step_finished - Sent when a build step finishes.
   * step_output_arrived - Sent when we have some output from a step.
   * repo_status_changed - Sent when the status of a repository changes.

Slave
-----

Slaves are responsible for actually carrying the builds, executing the steps.
They receive build requests from the master, execute the builds and send
iformation about these builds back to the master. Slaves also have plugins.
Slave plugins add steps before and/or after the steps defined by you in your
toxicbuild.conf file.


Writting slave plugins
++++++++++++++++++++++

To write slave plugins you must extend
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


User Interfaces
---------------

The package :mod:`toxicbuild.ui` implements ways for end users to interact
with ToxicBuild. It uses the module :mod:`toxicbuild.ui.models` to
communicate with the master and the module :mod:`toxicbuild.ui.web`
implemnts a simple web interface.


..
   Exchanges
   ---------

   Exchanges are a the way ToxicBuild parts talk to each other when asychronous
   events occour, using RabbiMQ. The following may be interresting:

   - repo_notifications: Exchange used
