Hacking ToxicBuild
==================

This is a brief introduction to the internals of ToxicBuild for those
who want to hack it in some way. ToxicBuild is written in python so you
must have some python dev tools, like virtualenv-wrapper and C compiler and
some header files to install it.


Installing from sources
-----------------------

Before we fetch the code, lets create a virtualenv to install our code inside.

.. code-block:: sh

    $ mkvirtualenv toxicbuild -p python3.5
    $ mkdir ~/hacks
    $ cd ~/hacks

Now you may clone the code from github:

.. code-block:: sh

    $ git clone https://github.com/jucacrispim/toxicbuild.git
    $ cd toxicbuild

And now install the dependencies:

.. code-block:: sh

    $ pip install -r requirements.txt

Finally, run the tests:

.. code-block:: sh

    $ python setup.py test
    $ behave tests/functional/webui/


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
    $ ln -s ~/hacks/toxicbuild/script/toxicweb ~/hacks/cienv/toxicweb

When everything is ready we can start the componets needed to have a
functional toxicbuild environment:

.. code-block:: sh

    $ ~/hacks/toxicbuild/toxicslave start ~/hacks/cienv/slave --daemonize --loglevel=debug
    $ ~/hacks/toxicbuild/toxicmaster start ~/hacks/cienv/master --daemonize --loglevel=debug
    $ ~/hacks/toxicbuild/toxicweb start ~/hacks/cienv/ui --daemonize --loglevel=debug


How that works
--------------

ToxicBuild consists in three parts: master, slave and ui. Each componet
talks to the others they need using the
:doc:`ToxicBuild Poor's Protocol <tpp>`.

In the users' guide we saw how to start the whole thing at once using the
``toxicbuild`` command. We may start each one of the components individually
using the ``toxicmaster``, ``toxicslave`` and ``toxicweb`` command. Use them
with the ``-h`` option for more information.


Master
------

The master is resposible for polling data (:mod:`toxicbuild.master.pollers`)
from the repositories (:mod:`toxicbuild.master.repository`), notifying the
slaves about new builds and send information about builds to the ui(s). Clients
communicate to the master, asking for things, like to add a new repo, start a
build or listen to events that occour in the master throught the
:mod:`toxicbuild.master.hole` (using the tpp, of course.)

It also has some plugins (:mod:`toxicbuild.master.plugins`) that are, at the
moment, used to send information about builds to different places, like e-mail
notification or integration with 3rd party systems like slack.


Writting master plugins
+++++++++++++++++++++++

To write master plugins is quite simple. You must subclass
:class:`toxicbuild.master.plugins.MasterPlugin` and implement a ``run()``
method. Optionaly you may implement a ``stop()`` method too. Both are
coroutines. Take a look at :mod:`toxicbuild.master.plugins` for more
information.


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


User Interfaces
---------------

The package :mod:`toxicbuild.ui` implements ways for end users to interact
with ToxicBuild. It uses the module :mod:`toxicbuild.ui.models` to
communicate with the master and the module :mod:`toxicbuild.ui.web`
implemnts a simple web interface.
