#!/bin/sh

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
behave -c tests/functional/webui
status=$?
killall Xvfb
exit $status
