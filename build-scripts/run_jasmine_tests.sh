#!/bin/sh

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
toxicjasmine ci -c tests/js-unit/jasmine.yml --browser chrome --options=no-sandbox
status=$?
killall Xvfb
rm /tmp/.X99-lock
exit $status
