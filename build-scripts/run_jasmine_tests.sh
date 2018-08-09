#!/bin/sh

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
jasmine ci -c tests/js-unit/jasmine.yml --browser chrome
status=$?
killall Xvfb
exit $status
