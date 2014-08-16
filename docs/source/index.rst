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

Edit the master.cfg file to your needs. Namely the TOXICBUILD_SOURCE,
POLLINTERVAL and BRANCHES variables.

Now you have to start buildbot master and buildbot slave. Execute this commands
in your command line:

.. code-block:: sh

    $ buildbot start ~/toxicCI/master
    $ buildslave start ~/toxicCI/slave

You have now your toxicbuild instance configured and ready to build your
application. The only thing that is still missing is the config file for
builders and its steps. In order to do so, in the root directory of your
project, put the following code in the ``toxicbuild.conf`` file.
.. code-block:: python

	builders [{'name': 'builder 1',
	           'steps': [{'name': 'run tests',
		              'command': 'python setup.py test',
			      'haltOnFailure': True},
			      {'name': 'say hello',
			      'command': 'echo "hello"'}]},
		   {'name': 'builder 2',
		   'steps': [{'name': 'echo',
		              'command': 'echo 1'}]}]

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
