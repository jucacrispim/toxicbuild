Configuring builds
==================

.. _build-config:

Now we have our repository in ToxicBuild, lets create the build configuration.
The build configuration stays in a file called `toxicbuild.yml` in the root
directory of your repository.

`Builds` are simply a sequence of shell commands, called `steps` in
ToxicBuild, that are executed sequencially. The builds are carried by
`builders`. The build config is based in these steps and builders.

When a change is detected in the source code new `builds` will be
created for the `builders` that will execute the `steps`.

So, let's say you have build process consisting in two steps: ``make`` and
``make test``. To have this executed by ToxicBuild we create a builder
with these two steps. This config must be in a file called `toxicbuild.yml`
in the root directory of your code:


.. code-block:: yaml

    # You must have a list of builders
    builders:
      # Our builder will be called `My Builder`
      - name: My Builder
	# and will execute two steps
	steps:
	  - make
	  - make test


And it is done! Commit and push this config to your repository and ToxicBuild
will execute this steps when a change is detected in the source code.

.. note::

   If you want some specific change in the repository doesn't trigger
   any builds, you can use the instruction ``ci: skip`` in the body of
   the commit.

These are the most basic configuration for a build, but the following
parameters may be used in your builds:


Builder parameters
------------------

The following parameters may be used for a builder:

* ``branches``: A list containing the branches that trigger this builder.
  If no branches, all branches will trigger the builder.
  You may use wildcards here.
* ``envvars``: A dictionary in the form VAR: VALUE for environment variables
  to be used in all steps in this builder.
* ``plugins``: A list of plugins configurations that will be used in the
  builder.


Example:

.. code-block:: yaml

   builders:
     - name: My Builder

       # a list of branches that may trigger builds. If no branches, all
       # branches in the repository will be allowed to trigger builds.
       # You can use wildcars to specify the branches.
       branches:
         - master
	 - feature-*
	 - bug-*

       envvars:
         # You can use interpolation in environment variables
         PATH: /some/dir:PATH
	 OTHER: some-value
	 # environment variables must always be strings.
	 A_VAR: '10'

       plugins:
         - name: apt-install
	   packages:
	     - build-essential

   ...

.. note::

   See :ref:`builder-plugins-config` for information about plugins


Step parameters
---------------

We saw steps configuration as a string that is a shell command, but we can
configure steps with a few extra parameters. To do so, configure the step
as a dictionary.

Example:

.. code-block:: yaml

   ...

   steps:

     # The can give a descriptive name for the step and the name will
     # be shown in the waterfall.
     - command: make
       name: Build the project

     # We can also give a timeout for the step. The timeout counts for how
     # long a step keeps running without sending any data to the output.
     - command: make test
       name: Test the whole stuff
       timeout: 300  # seconds



The following are the options accepted by the step:

* ``stop_on_fail``: If true, the build will halt if the step fails.
* ``warning_on_fail``: If true the build status will be marked as warning if
  the command fails (exits with a status different than 0).
* ``timeout``: How many seconds we should wait for the step complete. The
  default is 3600 seconds (one hour).


.. _builder-plugins-config:

Plugins
-------

Plugins may add steps before and/or after your own steps. At the moment we have
only two plugins. They are:

Python virtualenv plugin
^^^^^^^^^^^^^^^^^^^^^^^^

A very common way of installing python packages is installing it
inside a `vitualenv` using ``pip``.
This plugin enables you test your python programs inside a `virutalenv` and
install de python dependencies usig ``pip``.

The basic configuration of this plugin is as follows:


.. code-block:: yaml

   PY_ENV_PLUGIN:  &PY_ENV_PLUGIN
      - name: python-venv
	pyversion: python3.5

   # your builder config
   builders:
     - name: My Builder
      ...

     - plugins:
       - <<: *PY_ENV_PLUGIN

   ...

This will include two steps before your steps: First will create a virtualenv
using python3.5 and then will install the dependencies using pip.

.. note::

   This plugin uses the external programs ``virtualenv`` and ``pip``.
   You must have these installed in the slave system.


Python virtualenv parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following params may be used with this plugin:

* ``requirements_file``: File that contais a list of dependencies to install
  with pip. The default is `requirements.txt`.
* ``remove_env``: Indicates if the virtualenv will be removed after are
  executed. Default is False.


Apt install plugin
^^^^^^^^^^^^^^^^^^

This plugins installs a list of packages in a debian system using the apt-get
command.


.. code-block:: yaml

   APT_INSTALL_PLUGIN:  &APT_INSTALL_PLUGIN
     - name: apt-install
       packages:
         - build-essential
	 - python3.6-dev

.. note::

   This plugin use the external program ``sudo``. You must have this
   installed in the slave system.

.. note::

   This is a plugin that uses the APT package system, thus can only be used in
   debian (or debian-based) systems.


Now we have some configuration for builds and we have commited and pushed
the configuration we can see the progress of the builds in the waterfall.
