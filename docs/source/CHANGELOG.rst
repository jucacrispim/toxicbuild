Changelog
=========

* 0.4.0 (not released yet!)

  - Added wildcards filters for branches
  - added started, finished and total time for buildsets
  - Added option to limit builds in parallel
  - Corrected bug with pending builds that started before the previous
    finish.
  - Added master plugins (slack notification)
  - Added build step output view 'real time'
  - Css bugfixes
  - Improved docs

* 0.3.1

  - Corrected bug with new branches. Now it fetches the remote branches
    every
    time it looks for incomming changes

* 0.3

  - Re-wrote from scratch. It does not uses BuildBot as base anymore.
    Now it is
    written using python 3 and asyncio.

* 0.2.1

  - Corrected gitpoller branches behavior
  - added js to reload the waterfall web status
  - Correction on poller to poll() asap in order to have some builders.


* 0.2

  - Initial release
