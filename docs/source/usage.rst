Add a new repository
====================

The first thing we need is to add a repository we want to have a continuous
integration process. This is done by clicking in the `Add repository` button.

|add-repo-img|

.. |add-repo-img| image:: ./_static/add-repo.png
    :alt: Adding new repository


Repository Params
+++++++++++++++++

- Name (required): A name for the repository.
- Parallel builds: Limits the number of parallel builds for this repository.
  If null or 0 there is no limit for builds.
- URL (required): The url for the repository.
- Branches: It indicates which branches ToxicBuild should look for changes.
  If no branch is inserted here ToxicBuild will look for changes in all remote
  branches.

  .. note::

     If `Only latest commit`, when a bunch of commits are retrieved in the same
     fetch, only the most recent one will be builded.

- Slaves: The slaves that will execute builds for this repository. You must
  to choose at least one slave or no build will be executed.


Notifications
+++++++++++++

Notifications are the way ToxicBuild sends messages about builds using a given
notification method. The available notification methods are:

Email notification...
