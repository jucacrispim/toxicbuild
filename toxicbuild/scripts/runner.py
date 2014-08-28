# -*- coding: utf-8 -*-

import sys
from twisted.python import usage, reflect
from buildbot.scripts import base
from buildbot.scripts.runner import Options


class CreateToxicbuildOptions(base.BasedirMixin, base.SubcommandOptions):
    subcommandFunction = "toxicbuild.scripts.create.create"

    optFlags = [['quiet', 'q', 'Do not emit the commands being run']]

    optParameters = [
        ["toxicbuild-db", None, "sqlite:///toxicbuild.sqlite",
         "which DB to use for scheduler/status state. See below for syntax."]]

    def getSynopsis(self):
        return 'Usage: toxicbuild create <basedir>'


class StartToxicBuildOptions(base.BasedirMixin, base.SubcommandOptions):
    subcommandFunction = 'toxicbuild.scripts.start.start'

    optFlags = [['quiet', 'q', 'Do not emit the commands being run']]

    def getSynopsis(self):
        return 'Usage: toxicbuild toxicstart <basedir>'


class StopToxicBuildOptions(base.BasedirMixin, base.SubcommandOptions):
    subcommandFunction = 'toxicbuild.scripts.stop.stop'

    optFlags = [['quiet', 'q', 'Do not emit the commands being run']]

    def getSynopsis(self):
        return 'Usage: toxicbuild toxicstop <basedir>'


Options.subCommands.append(['create', None, CreateToxicbuildOptions,
                            "create easy buildbot install"])
Options.subCommands.append(['toxicstart', None, StartToxicBuildOptions,
                            'start master and slave'])
Options.subCommands.append(['toxicstop', None, StopToxicBuildOptions,
                            'stop master and slave'])


def run():  # pragma: no cover
    # copy/paste from buildbot
    config = Options()
    try:
        config.parseOptions(sys.argv[1:])
    except usage.error, e:
        print "%s:  %s" % (sys.argv[0], e)
        print
        c = getattr(config, 'subOptions', config)
        print str(c)
        sys.exit(1)

    subconfig = config.subOptions
    subcommandFunction = reflect.namedObject(subconfig.subcommandFunction)
    sys.exit(subcommandFunction(subconfig))
