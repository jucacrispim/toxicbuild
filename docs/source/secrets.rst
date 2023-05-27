.. _secrets-config:

Secrets
=======

Secrets are information you don't want to be exposed to everyone.

Secrets are implemented in toxicbuild to avoid exposure of sensitive information,
like api tokens, to third party actors. This is done like this:

- Secrets are stored encrypted in the database
- Secrets are NOT available for builds requested by third parties.

What that means is if someone who can access the secrets database will not have
access to the secrets themselves and builds requested by external repos (like a
pull request) will not have access to the secrets.

.. warning::

   People that have access to the repository will have access to the secrets.
   This is not a way to hide secrets from people that have access to
   your repositories configuration.

To use the secrets just save your information and that will be available as a
environment variable in your builds.
