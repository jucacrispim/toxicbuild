ToxicBuild Poor's Protocol
==========================

The ToxicBuild Poor's Protocol is a simple protocol used to exchange messages,
using tcp sockets, between the components of ToxicBuild. It is as follows:

The first ``n`` bytes, until the first ``\n`` are indicate the length of the
message, the rest of the message is a utf-8 encoded json. This json must
contain 3 keys: ``token``, ``action`` and ``body``.

The ``token`` is obviously for authentication. The ``action`` key says
what you want to do and the ``body`` are params specific for each action.

For example, lets say a client wants execute the action ``list-funcs``
in the master. The message that must be sent is something like:

.. code-block:: sh

    MSG='59\n{"token": "auth-token", "action": "list-funcs", "body": {}}'


And you can send it using nc, for example.

.. code-block:: sh

  echo $MSG | nc localhost 6666
  # here you should see the response from the master.


Or, using the :class:`toxicbuild.core.BaseToxicClient` in the python
API.

.. code-block:: python

    >>> import asyncio
    >>> loop = asycio.get_event_loop()
    >>> async def list_funcs():
    ...     client = BaseToxicClient('localhost', 6666)
    ...     await client.connect()
    ...     msg = {'token': 'auth-token', 'action': 'list-funcs', 'body': {}}
    ...     await client.write(msg)
    ...     response = await client.get_response()
    ...     client.disconnect()
    ...     print(response['body']['list-funcs'].keys())
    ...
    >>> loop.run_until_complete(list_funcs())


For more information about the actions supported by the master look at
:class:`toxicbuild.master.hole.HoleHandler` and
:source:`tests/functional/test_master.py`.

For for information about the actions supported by the slave look at
:class:`toxicbuild.slave.protocols.BuildServerProtocol` and
:source:`tests/functional/test_slave.py`.
