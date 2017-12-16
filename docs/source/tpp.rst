ToxicBuild Poor's Protocol
==========================

The ToxicBuild Poor's Protocol is a simple protocol used to exchange messages,
using tcp sockets, between the components of ToxicBuild. It is as follows:

The first ``n`` bytes, until the first ``\n`` are indicate the length of the
message, the rest of the message is a utf-8 encoded json. This json must
contain 3 keys: ``token``, ``action`` and ``body``.

The ``token`` is obviously for authentication. The ``action`` key says
what you want to do and the ``body`` are params specific for each action.

Requests to the slave
---------------------

For example, lets say a client wants execute the action ``healthcheck``
in the slave. The message that must be sent is something like:

.. code-block:: sh

    MSG='60\n{"token": "auth-token", "action": "healthcheck", "body": {}}'


And you can send it using nc, for example.

.. code-block:: sh

  echo $MSG | nc localhost 7777
  # here you should see the response from the slave.


Or, using the :class:`toxicbuild.core.BaseToxicClient` in the python
API.

.. code-block:: python

    >>> import asyncio
    >>> loop = asycio.get_event_loop()
    >>> async def healthcheck():
    ...     client = BaseToxicClient('localhost', 6666)
    ...     await client.connect()
    ...     msg = {'token': 'auth-token', 'action': 'healthcheck', 'body': {}}
    ...     await client.write(msg)
    ...     response = await client.get_response()
    ...     client.disconnect()
    ...     print(response['body'])
    ...
    >>> loop.run_until_complete(healthcheck())


For for information about the actions supported by the slave look at
:class:`toxicbuild.slave.protocols.BuildServerProtocol` and
:source:`tests/functional/test_slave.py`.


Requests to the master
----------------------

To perform requests to the master, we need one more key in our json, it is
the ``user_id`` key, used to identify the user who is requesting. To obtain
an user id, first you need to authenticate the user and then send the user id
in the subsequent requests.

So, first authenticate:


.. code-block:: sh

    MSG='115\n{"token": "auth-token", "action": "authenticate", "body": {"username_or_email": "ze", "password": "some-password"}}'

    echo $MSG | nc localhost 6666
    # In the response from the master there is the user id. Use this
    # id in the subsequent requests.

    MSG='84\n{"token": "auth-token", "action": "repo-list", "user_id": "the-user-id", "body": {}}'

    echo $MSG | nc localhost 6666


For more information about the actions supported by the master look at
:class:`toxicbuild.master.hole.HoleHandler` and
:source:`tests/functional/test_master.py`.
