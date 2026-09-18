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

   $ sudo apt-get install python3-dev build-essential mongodb \
		rabbitmq-server libyaml-dev xvfb chromedriver


The components
--------------

ToxicBuild is **not** a single code base anymore. It was split into a few
repositories, each one with its own python package and its own dependencies:

* `toxiccore <https://github.com/jucacrispim/toxiccore>`_: The core
  library used by all the components (protocol, vcs, utils).

* `toxiccommon <https://github.com/jucacrispim/toxiccommon>`_: Common
  code and clients shared by the different components.

* `toxicmaster <https://github.com/jucacrispim/toxicmaster>`_: Responsible
  for controlling all the stuff. Manages build queues, controlling access to
  resources and receiving requests from the user interface.

* `toxicpoller <https://github.com/jucacrispim/toxicpoller>`_: Responsible
  for polling changes from the repository and notify the master in case of
  new revisions.

* `toxicslave <https://github.com/jucacrispim/toxicslave>`_: Responsible for
  executing the builds.

* `toxicintegrations <https://github.com/jucacrispim/toxicintegrations>`_:
  Responsible for interacting with 3rd party services.

* `toxicnotifications <https://github.com/jucacrispim/toxicnotifications>`_:
  Responsible for sending notifications about events.

* `toxicsecrets <https://github.com/jucacrispim/toxicsecrets>`_: Responsible
  for storing secrets.

* `toxicwebui <https://github.com/jucacrispim/toxicwebui>`_: The web
  interface.

* `toxicbuild <https://github.com/jucacrispim/toxicbuild>`_ (this
  repository): The documentation, the build images, the docker
  installation and the ``toxicbuild`` command used to orchestrate the
  components.


Installing from sources
-----------------------

Clone each component from github:

.. code-block:: sh

    $ mkdir ~/mysrc
    $ cd ~/mysrc
    $ for p in toxiccore toxiccommon toxicmaster toxicpoller toxicslave \
        toxicintegrations toxicnotifications toxicsecrets toxicwebui \
        toxicbuild; do
          git clone https://github.com/jucacrispim/$p.git
      done

Then install the orchestrator:

.. code-block:: sh

    $ cd ~/mysrc/toxicbuild
    $ pip install -e .


Creating a development environment
----------------------------------

Because the components may have conflicting dependencies, each one is
installed in its own virtualenv. The ``toxicbuild setup`` command takes
care of that for you, creating a virtualenv per component under
``<root_dir>/venvs/<component>`` and running the ``create`` command of each
one inside its own venv.

To use your live code, pass ``--source local`` so each component is
installed in editable mode from ``--source-dir``:

.. code-block:: sh

    $ toxicbuild setup ~/ci --source local --source-dir ~/mysrc

When everything is ready we can start the components:

.. code-block:: sh

    $ toxicbuild start ~/ci --loglevel debug

And to stop them:

.. code-block:: sh

    $ toxicbuild stop ~/ci

You can also start/stop/restart a subset of the components:

.. code-block:: sh

    $ toxicbuild start ~/ci --components master,slave

The following log files may be interesting:

* ``~/ci/master/toxicmaster.log``: Log file for toxicmaster instance.
* ``~/ci/poller/toxicpoller.log``: Log file for toxicpoller instance.
* ``~/ci/slave/toxicslave.log``: Log file for toxicslave instance.
* ``~/ci/notifications/toxicnotifications.log``: Log file for the
  notifications instance.
* ``~/ci/integrations/toxicintegrations.log``: Log file for
  toxicintegrations instance.


How that works
--------------

ToxicBuild consists in a few moving parts that interact with each other using
the :doc:`ToxicBuild Poor's Protocol <tpp>` (for 'direct' messages from one
part to another) or sending messages using a broker (for async events that may
occour). The different components of ToxicBuild are described above in
`The components`_.


Writting notification plugins
-----------------------------

Notification plugins are the way toxicbuild sends messages to a third party
service when buildsest start to build or when the builds are done. To
write a new notification plugin you need to extend the
:class:`~toxicnotifications.base.Notification` class and
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

   You can use the fields in the :mod:`~toxicnotifications.fields` in order
   to use the ``pretty_name`` param that is the name that will be displayed
   in the plugin config.

.. code-block:: python

   from toxicnotifications.base import Notification
   from toxicnotifications.fields import PrettyStringField


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
:mod:`toxicnotifications.__init__` module. Then restart
the notifications instance and you should see your plugin in the repositories
notifications config page


Writting slave plugins
----------------------

Slave plugins add steps before and/or after the steps defined by you in your
toxicbuild.conf file. To write slave plugins you must extend
:class:`~toxicslave.plugins.SlavePlugin`. You may implement the methods
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
