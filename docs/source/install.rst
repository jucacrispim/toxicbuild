Installation
============

You have a few options to have a ToxicBuild instance running.

Using Docker
++++++++++++

The easiest way to have a ToxicBuild local installation is to use Docker.
So, with docker installed on your system, first clone the code:

.. code-block:: sh

   $ git clone https://github.com/jucacrispim/toxicbuild.git
   $ cd toxicbuild

And then run the ``./build-scripts/toxicinstall.sh create-local`` command

.. code-block:: sh

   $ ./build-scripts/toxicinstall.sh create-local
   - Pulling required images
   ...

   - Creating toxicbase image. Be patient.
   ...

   - Creating toxicslave
   - Creating toxicoutput
   - Creating toxicmaster
     email: a@a.com
     password: 123
   - Creating toxicscheduler
   - Creating toxicpoller
   - Creating toxicintegrations
   - Creating toxicweb

Now you can start with ``./build-scripts/toxicinstall.sh start-local``

.. code-block:: sh

   $ ./build-scripts/toxicinstall.sh start-local

And access http://localhost:8888/ using your browser.


Using pip
+++++++++

ToxicBuild is written in Python, and runs in Python3.6 and later. It uses
MongoDB to store data, rabbitmq for queues, zookeeper for coordination
and git as vcs. You must have these installed. In a Debian system, use the
following command:

.. code-block:: sh

   sudo apt-get install mongodb rabbitmq zookeeperd


If you want to be able to build c extensions for speed, install the
Python header files, a C compiler ``libffi`` and ``libyaml``.

.. code-block:: sh

   sudo apt-get install build-essential libffi-dev python3.7-dev libyaml-dev


After the installation of the external dependencies you can install toxicbuild
using pip:

.. code-block:: sh

   $ pip install toxicbuild


Now that toxicbuild is installed we need to create a new environment


Setup
-----

Create a new environment using the command ``toxicbuild create``.

.. code-block:: sh

   $ toxicbuild create ~/ci
   Creating root_dir `ci/slave` for toxicslave
   Toxicslave environment created with access token: mI4AHDl0LjzTrD1RieX64xp1xWrXhoiGgdedFJ5IRvg
   Creating root_dir `ci/output` for toxicoutput
   Creating root_dir `ci/master` for toxicmaster
   email: a@a.com
   password: 123
   Toxicmaster environment created with access token: wq7dUahnE_EkveLIH1R9KsDg2qT0rHSfljQqh1g3iB8
   Creating root_dir `ci/integrations` for toxicintegrations
   Creating root_dir ci/ui
   Toxicui environment created for web



And now you can start toxicbuild with the command ``toxicbuild start``:

.. code-block:: sh

   $ toxicbuild start ~/ci
   Starting toxicslave
   Starting toxicmaster
   Starting toxicpoller
   Starting toxicscheduler
   Starting output web api on port 9432
   Starting integrations on port 9999


.. _toxicslave-install:

Installing only toxicslave
++++++++++++++++++++++++++

One toxicbuild installation can handle multiple slaves so now lets install
only toxicslave and use supervisor to start toxicslave on startup.

For the slave we don't need mongo, rabbitmq or zookeeper, so we simply install
toxicbuild

.. code-block:: sh

   $ pip install toxicbuild

Now we create a toxicslave environment

.. code-block:: sh

   $ toxicslave create ~/ci/slave
   Creating root_dir `ci/slave` for toxicslave
   Toxicslave environment created with access token: xXE2enJ-O1YcSx8vurLyTawGds_bkJ79i6-LShVEPjA

Save this access token as it can't be recovered later.

This is an example of a minimal supervisor config:

.. code-block:: cfg

   [program:toxicslave]
   command=/home/ec2-user/venv/bin/toxicslave start /home/ec2-user/ci/slave
   directory=/home/ec2-user/ci/slave
   numprocs=1
   autorestart=true
   user=ec2-user
   environment=HOME="/home/ec2-user/"
