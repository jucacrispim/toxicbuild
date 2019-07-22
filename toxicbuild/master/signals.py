# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from asyncblink import signal


revision_added = signal('revision-added')
step_started = signal('step-started')
step_finished = signal('step-finished')
step_output_arrived = signal('step-output-arrived')
build_preparing = signal('build-preparing')
build_started = signal('build-started')
build_finished = signal('build-finished')
build_added = signal('build-added')
repo_status_changed = signal('repo-status-changed')
build_cancelled = signal('build-cancelled')
buildset_added = signal('buildset-added')
buildset_started = signal('buildset-started')
buildset_finished = signal('buildset-finished')
