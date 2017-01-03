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
    $ mkdir ~/toxic-hack
    $ cd ~/toxic-hack

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


You should see no errors on the tests.



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

The master is resposible for polling data from the repositories, notifying
the slaves about new builds and send information about builds to the
ui(s). Clients communicate to the master, asking for things, like
to add a new repo, start a build or listen to events that occour
in the master throught the
:mod:`toxicbuild.master.hole` (using the tpp, of course.)

It also has some plugins that are, at the moment, used to send information
about builds to different places, like e-mail notification or integration
with 3rd party systems like slack.


Slave
-----

Slaves are responsible for actually carrying the builds, executing the steps.
They receive build requests from the master, execute the builds and send
iformation about these builds back to the master.

User Interfaces
---------------

The package :mod:`toxicbuild.ui` implements ways for end users to interact
with ToxicBuild. It uses the module :mod:`toxicbuild.ui.models` to
communicate with the master and the module :mod:`toxicbuild.ui.web`
implemnts a simple web interface.
