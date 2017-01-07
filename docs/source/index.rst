.. toxicbuild documentation master file, created by
   sphinx-quickstart on Thu May 15 21:22:59 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


ToxicBuild |toxicbuild-logo|
============================

.. |toxicbuild-logo| image:: ./_static/Logo.svg
    :alt: Simple and flexible continuous itegration tool.

ToxicBuild is an easy-to-install, simple-to-use distributed continuous
integration tool that enables you to have fully control of your build process.


User Guide
==========

If you are interested in using toxicbuild in your ci process read:

.. toctree::
   :maxdepth: 1

   user_guide


Hacking
=======

If you are interested in mess around with toxicbuild, read:

.. toctree::
   :maxdepth: 1

   hacking
   apidoc/modules


Issue Tracker
=============

You can follow the development of toxicbuild throught the issue tracker in
`<https://github.com/jucacrispim/toxicbuild/issues>`_

Licence
=======

ToxicBuild is free software released under the GPLv3 or later.



Changelog
=========

* 0.4.0 (not released yet!)

  - Corrected bug with pending builds that started before the previous finish.
  - Added master plugins (slack notification)
  - Added build step output view 'real time'
  - Css bugfixes
  - Improved docs

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
