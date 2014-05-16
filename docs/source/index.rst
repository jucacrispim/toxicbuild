.. toxicbuild documentation master file, created by
   sphinx-quickstart on Thu May 15 21:22:59 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to toxicbuild's documentation!
======================================

Toxicbuild is a tiny - and hackish -  layer built on top of buildbot. Using
toxicbuild you can keep your steps configuration within your project's source
code and toxicbuild will create per-build config based steps.


Install
+++++++

.. code-block:: sh

   $ pip install toxicbuild

Usage
+++++

First, you need to create a new toxicbuild application. It simply creates a
new master and a new slave in the specified directory.

.. code-block:: sh

    $ toxicbuild create ~/toxicCI

Edit the file ~/toxicCI/master/master.cfg and in the ``toxicbuild_source``
variable, replace the original git url by your project git url. Then,
in the DynamicBuilderConfig instanciation, change the variables ``venv_path``
and ``pyversion`` to your like. Note that ``venv_path`` must be a relative
path and is relative to the slave basedir.

After that, you need to start master and slave.

.. code-block:: sh

    $ buildbot start ~/toxicCI/master
    $ buildslave start ~/toxicCI/slave

Now you have things up and ready to build your project, but one thing is
still missing. We need to configure the steps in our project. Lets create
a file called ``toxicbuild.conf`` in the root dir of the project with the
following content:

.. code-block:: python

    steps = [{'name': 'run tests',
              'command': 'python setup.py test',
	      'haltOnFailure': True},
	     {'name': 'say hello',
	      'command': 'echo "hello"'}]

Finally, put your dependencies in a file called ``requirements.txt`` Like this:

.. code-block:: sh

    pyrocumulus==0.4.2
    redis==2.4.9

Commit, push and that's it. In a minute or so your build will start.


Notes
+++++

Toxicbuild is in its very initial development. By now it only builds python
projects using git cvs, but I'm still working on it.

Stay tuned for new features!


Contents:

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
