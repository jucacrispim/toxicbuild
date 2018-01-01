Configuring builds
==================

Now we have our repository in ToxicBuild, lets create the build configuration.
The build configuration stays in a file called `toxicbuild.conf` in the root
directory of your repository.

`Builds` are simply a sequence of shell commands, called `steps` in
ToxicBuild, that are executed sequencially. The builds are done by
`builders`. The build config is based in these steps and builders.

When a change is detected in the source code new `builds` will be
created for the `builders` that will execute the `steps`.

So, let's say you have build process consisting in two steps: ``make`` and
``make test``. To have this executed by ToxicBuild we create a builder
with these two steps. This config must be in a file called `toxicbuild.conf`
in the root directory of your code:


.. note::

   The `toxicbuild.conf` file is a Python file, do whatever you want, but
   it must have a ``BUILDERS`` list.


.. code-block:: python

    # The step configuration has two required keys: 'name' and 'command'
    MAKE_STEP = {'name': 'Compile', 'command': 'make'}
    MAKE_TEST_STEP = {'name': 'Test': 'command': 'make test'}

    # Builder configuration has two requred keys: 'name' and 'steps'.
    # The 'steps' value is a list of steps configurations.
    BUILDER = {'name': 'my-builder',
               'steps': [MAKE_STEP, MAKE_TEST_STEP]}

    # And now we need to add the builder config to a list of builders
    # that will be used in the builds. You may have more than one builder
    # and the builders will execute the builds in parallel for every change
    # in the source code.
    BUILDERS = [BUILDER]


And it is done! Commit and push this config to you repository and ToxicBuild
will execute this steps when a change is detected in your source code.

These are the most basic configuration for a build, but the following
parameters may be used in your builds:

Step parameters
---------------

The two params we saw, ``name`` and ``command``, are the two required params
for a steps, but the following params may be used too:

* ``stop_on_fail``: If true, the build will halt if the step fails.
* ``warning_on_fail``: If true the build status will be marked as warning if
  the command fails (exits with a status different than 0).
* ``timeout``: How many seconds we should wait for the step complete. The
  default is 3600 seconds (one hour).

Example:

.. code-block:: python

   MAKE_STEP = {'name': 'Compile', 'command': 'make',
		'stop_on_fail': True}


Builder params
--------------

Builder has extra optional params, too. They are the following:

* ``branches``: A list containing the branches that trigger this builder.
  If no branches, all branches will trigger the builder.
  You may use wildcards here.
* ``envvars``: A dictionary in the form {VAR: VALUE} for environment variables
  to be used in all steps in this builder.
* ``plugins``: A list of plugins configurations that will be used in the
  builder.

Example:

.. code-block:: python

   # note that here the value of the environment variable PATH will be
   # interpolated in the builder envvars.
   ENVVARS = {'PATH': '/opt/bin:PATH'}
   BUILDER = {'name': 'my-builder',
              'steps': [MAKE_STEP, MAKE_TEST_STEP],
	      'envvars': ENVVARS}



Plugins
-------

Plugins may add steps before and/or after your own steps. At the moment we have
only two plugins. They are:

Python virtualenv plugin
^^^^^^^^^^^^^^^^^^^^^^^^

A very common way of installing python packages is using a `vitualenv`.
This plugin enables you test your python programs inside a virutalenv.

The basic configuration of this plugin is as follows:

.. code-block:: python

    PY_VENV = {'python-venv', 'pyversion': 'python3.5'}
    BUILDER = {'plugins': [PY_VENV]}

This will include two steps before your steps: First will create a virtualenv
using python3.5 and then will install the dependencies using pip.

.. note::

   This plugin uses the external program ``virtualenv``. You must have this
   installed in the slave system.


Python virtualenv parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following params may be used with this plugin:

* ``requirements_file``: File that contais a list of dependencies to install
  with pip. The default is `requirements.txt`.
* ``remove_env``: Indicates if the virtualenv will be removed after are
  executed. Default is False.


Aptitude install plugin
^^^^^^^^^^^^^^^^^^^^^^^

This plugins installs a list of packages in a debian system using the aptitude
command.

.. code-block:: python

   APT_INSTALL = {'name': 'aptitude-install', 'packages': ['build-essential']}

.. note::

   This plugin uses the external programs ``sudo`` and ``aptitude``. You must
   have these installed in the slave system.


Now we have some configuration for builds and we have commited and pushed
the configuration we can see the progress of the builds in the waterfall.
