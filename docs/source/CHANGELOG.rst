Changelog
=========

* 0.7.0

  - Added step details page
  - Added branch filter on waterfall
  - Added ci-include-builders and ci-exclude-builders commit instructions.
  - Added environment variables to repository.
  - Minor ui fixes.
  - Updated aiozk - fix poller deadlock.

* 0.6.2

  - Web ui fixes.

* 0.6.1

  - Now builds stop when a steps finishes with exception

* 0.6.0

  - Add simple build config
  - Builds now can be optionally trigger by other builds.
  - New build queue. Now are not sent to all slaves.
  - Amazon ec2 integration
  - Improved builds on docker containers
  - Gitlab integration
  - New web user interface

* 0.5.0

  - Added support for builds inside docker containers.
  - Added multi-user support
  - Master process divided in master, scheduler, poller and output
  - SSL support
  - New yaml config format
  - Github integration
  - Added ci: skip instruction

* 0.4.2

  - Corrected builds without limit.

* 0.4.1

  - Corrected changing of repository status in the main page

* 0.4.0

  - Added build details modal.
  - Added timezone option on ui
  - added total_time to buildset, build and step
  - Added datetime stuff to buildset
  - Added wildcards filters for branches
  - added started, finished and total time for buildsets
  - Added option to limit builds in parallel
  - Corrected bug with pending builds that started before the previous
    finish.
  - Added master plugins (slack notification, email notification and
    custom webhook notification).
  - Added build step output view 'real time'
  - Css bugfixes
  - Improved docs

* 0.3.1

  - Corrected bug with new branches. Now it fetches the remote branches
    every time it looks for incomming changes

* 0.3

  - Re-wrote from scratch. It does not uses BuildBot as base anymore.
    Now it is written using python 3 and asyncio.

* 0.2.1

  - Corrected gitpoller branches behavior
  - added js to reload the waterfall web status
  - Correction on poller to poll() asap in order to have some builders.


* 0.2

  - Initial release
