.. toxicbuild documentation master file, created by
   sphinx-quickstart on Thu May 15 21:22:59 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to toxicbuild's documentation!
======================================

Toxicbuild is a tiny - and hackish -  layer built on top of buildbot. Using
toxicbuild you can keep your builders and steps configuration within your
project's source code. Change everything and you don't need to touch your
master.cfg file!


Install
+++++++

.. code-block:: sh

   $ pip install toxicbuild

Usage
+++++

First, you need to create a new toxicbuild application. It simply creates a
new buildbot master and a new buildbot slave in the specified directory.

.. code-block:: sh

    $ toxicbuild create ~/toxicCI

With this command, a new master was created in ~/toxicCI/master and a new
slave was created in ~/toxicCI/slave.

Edit the master.cfg file to your needs. Namely the PROJECT_NAME,
TOXICBUILD_SOURCE, BRANCHES and POLLINTERVAL variables.

Now you have to start buildbot master and buildbot slave. Execute this
command in your command line:

.. code-block:: sh

    $ toxicbuild toxicstart ~/toxicCI/

You have now your toxicbuild instance configured and ready to build your
application. The only thing that is still missing is the config file for
builders and its steps. In order to do so, in the root directory of your
project, put the following code in the ``toxicbuild.conf`` file.

.. code-block:: python

    # candies are pre-configured steps for common tasks.
    candies = [
	# this git candy updates the codebase and checkout
	# to a named_tree (a branch, a commit...)
	{'name': 'git-update-and-checkout'},

	# this python-virtualenv candy creates a virtualenv,
	# install the dependencies using pip + requirements.txt file
	# and sets the env vars to use the virutalenv in every step.
	{'name': 'python-virtualenv',
	 'venv_path': 'toxicenv',
	 'pyversion': '/usr/bin/python2.7'}
    ]

    # These steps are shell commands. The rootdir for the
    # commands execution is the directory containing this file.
    steps = [{'name': 'Unit tests and coverage',
	      'command': 'sh ./build-scripts/check_coverage.sh'},

	     {'name': 'Checking coding style',
	      'command': 'sh ./build-scripts/check_code.sh',
	      'warnOnFailure': True,
	      'flunkOnFailure': False},

	     {'name': 'Functional tests',
	      'command': 'python setup.py test --test-suite=tests.functional'}]

    release_steps = steps + [{'name': 'Upload to pypi',
			      'command': 'python setup.py sdist'}]

    # This is the main variable for toxicbuild.conf.
    # Bulders can be configured on a per-branch basis.
    # The builder name must be unique.
    builders = [
	{'name': 'default',
	 'branch': 'master',

	 'candies': candies,
	 'steps': steps}

	{'name': 'release',
	 'branch': 'release',

	 'candies': candies,
	 'steps': release_steps}

    ]

And that's it. Commit, push and your build will begin automatically.


Notes
+++++

Toxicbuild is in its very initial development. By now it only builds projects
using git cvs, but I'm still working on it.

Stay tuned for new features!


Contents:

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
