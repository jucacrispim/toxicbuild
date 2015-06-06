Bem-vindo à documentação do Toxicbuild!
=======================================

Toxicbuid é um sistema distribuído para automatização do processo de *build*,
*test* e *release* de software. Ele é fortemente inspirado no *buildbot*,
a principal diferença é que os *steps*


Instalação
++++++++++

A instalação é comum, via *pip*:

.. code-block:: sh

   $ pip install toxicbuild


O *master* usa o MongoDB como banco de dados, então também é preciso
instalá-lo. Faça a instalação da maneira adequada ao seu sistema operacional.


Uso
+++

A configuração dos *builds* é toda baseada em *builders*. Os *builders* são
entidades que executam os comandos determinados na configuração. Pode-se
configurar *builders* pra todos os *branches* ou para um *branch* específico.

A configuração de um *builder* é muito simples: um dicionário contendo o nome
do *builder*, os *steps* que o *builder* executará e, opcionalmente, o branch
para o qual este builder está configurado. Um step é simplesmente um comando
de *shell*. Nós vamos representá-lo como um dicionário contento um nome para o
*step* e o comando em si. Um exemplo:

.. code-block:: python

    builder = {'name': 'my-builder',
	       # steps é uma lista de dicionários. Cada dicionário é um step.
               'steps': [{'name': 'run tests',
		          'command': 'python setup.py test'}]}

Neste exemplo temos um builder chamado ``my-builder``, com um *step*, que
executa o comando ``python setup.py test``.

Podemos configurar quantos *builders* quisermos, o que precisamos fazer depois
é simplesmente colocar estes *builders* em uma lista, chamada ``BUILDERS``.
Assim:

.. code-block:: python

    BUILDERS = [builder, other_builder, ...]


E é isso. Agora já podemos usar uma das interfaces para interagir com o master.


Usando a interface em linha de comando
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para iniciar a interface em linha de comando, simplesmente execute o comando
``toxiccli`` à partir de um *shell*.

.. note::

  Por padrão o comando ``toxiccli`` tenta conectar-se ao master em localhost
  na porta 6666. Estas configurações podem ser alteradas usando-se os
  parâmetros ``--host`` e ``--port``, respectivamente, ou ainda usando o
  arquivo de configuração ``~/.toxicclirc``

A primeira coisa a se fazer assim que se está na cli, é usar o comando ``help``
para obter uma lista de todos os comandos e opções disponíveis. Para começar
vamos usar o comando ``repo-add``. Este comando adiciona um novo repositório
ao toxicbuild. Um repositório de o local de onde o toxicbuild vai buscar o
código fonte e verificar por alterações. Vamos usar o comando com os
seguintes parâmetros (posicionais):

* repo-name - Um nome (único) para o repositório.
* repo-url - Url para o repositório.
* update-seconds - Tempo para procurar por atualizações.
* vcs-type - tipo de vcs usado.

.. note::

  Para ver a lista completa de opções de um comando, execute ``help <comando>``
  na cli do toxicbuild.
