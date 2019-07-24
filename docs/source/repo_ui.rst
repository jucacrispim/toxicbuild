Importing Repositories
======================

You need to import the repositoires into ToxicBuild to be able to
have continuous integration. Repositories can be imported from github,
from gitlab or can be added manually.

Importing repositories from Github
++++++++++++++++++++++++++++++++++

First configure the :ref:`github-integration-config` then go to
`http://localhost:8888/settings/repositories` and click in the
github link:

|import-from-github-link-img|


.. |import-from-github-link-img| image:: ./_static/import-from-github.jpg
    :alt: Adding new github repository


You will be redirected to Github and can choose wich repositories you want
imported into ToxicBuild.

|github-app-install|

.. |github-app-install| image:: ./_static/github-app-install.jpg


After you select your repositoires and install, you will be redirect to
the ToxicBuild web ui again and that's it. Your repositories will be imported.


Importing repositories from Gitlab
++++++++++++++++++++++++++++++++++

First configure the :ref:`gitlab-integration-config` then go to
`http://localhost:8888/settings/repositories` and click in the
gitlab link:

|import-from-gitlab-link-img|


.. |import-from-gitlab-link-img| image:: ./_static/import-from-gitlab.jpg
    :alt: Adding new Gitlab repository


The Gitlab does not have an option to select the repositories you want
imported, so all your repositories will be imported, but you can
enable/disable repositories at `http://localhost:8888/settings/repositories`

|disable-repo-link-img|


.. |disable-repo-link-img| image:: ./_static/disable-repo.jpg
    :alt: Disabling repositories


Adding repositories manually
++++++++++++++++++++++++++++

If you do not use github, gitlab or do not want import your repositoires
automaticaly, you can add them by hand. Go to
`http://localhost:8888/repository/add`:

|import-manually|

.. |import-manually| image:: ./_static/import-manually.jpg

* ``Name`` - An unique name for the repository
* ``URL`` - The clone url of the repository


Repository advanced configuration
+++++++++++++++++++++++++++++++++

When you click in the advanced link in the repository settings page
these are the available options:

|repo-advanced-config-img|

.. |repo-advanced-config-img| image:: ./_static/repo-advanced-config.jpg
    :alt: Repository advanced configuration


* ``Branches`` - Configure which branches trigger can builds. If no
  branches configuration, all branches will trigger builds. The branches
  configuration has the following options:

  - ``Name`` - The branch name. You can use wildcards here.
  - ``Only most recent changes`` - If checked when a bunch of commits
    are pushed at the same time only the most recent will trigger builds

* ``Parallel builds`` - How many parallel builds this repository can
  run. If no parallel builds there is no limit.
* ``Slaves`` - Which slaves can execute builds for the repository. If a
  repository don't have any enabled slave no builds will be executed.