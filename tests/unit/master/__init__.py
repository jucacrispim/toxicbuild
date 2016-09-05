# -*- coding: utf-8 -*-

from toxicbuild.master import create_settings_and_connect
from toxicbuild.master import create_scheduler
create_scheduler()
from toxicbuild.master import scheduler
scheduler.stop()

create_settings_and_connect()
