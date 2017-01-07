.. toxicbuild documentation master file, created by
   sphinx-quickstart on Thu May 15 21:22:59 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


ToxicBuild |toxicbuild-logo|
============================

.. |toxicbuild-logo| image:: ./_static/Logo.svg
    :alt: Simple and flexible continuous itegration tool.

ToxicBuild is a simple but flexible distributed continuous integration tool
that enables you to configure your ci process using the power of the Python
programming language.


.. toctree::
   :maxdepth: 1

   user_guide
   hacking


Licence
=======

ToxicBuild is free software released under the GPLv3 or later.


Known Bugs
==========

- The waterfall.js does not now how to include new builders that came via
  websocket and sometimes it places the build in a wired place. Must reload
  the page.

- Slaves should kill all processes created by its child processes.


Aditional notes
===============

- Slaves must to work in all platforms. Probably now they will not work, some
  development towards this feature must be done. Master and ui would be nice to
  work in as many platforms as possible.

- ToxicBuild should have a build step that triggers another builder.

- Should support more vcs, not only git.

- It needs other report methods other than the web ui.

- Needs an install for master, slave and ui separately.

- Should support ssl.


Changelog
=========

* 0.3.1

  - Corrected bug with new branches. Now it fetches the remote branches every
    time it looks for incomming changes

* 0.3

  - Re-wrote from scratch. It does not uses BuildBot as base anymore. Now it is
    written using python 3 and asyncio.

* 0.2.1

  - Corrected gitpoller branches behavior
  - added js to reload the waterfall web status
  - Correction on poller to poll() asap in order to have some builders.


* 0.2

  - Initial release



That's all. Thank you very much for using ToxicBuild!
