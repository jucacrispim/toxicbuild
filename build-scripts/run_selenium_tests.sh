#!/bin/sh

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
behave tests/webui
status=$?
killall Xvfb
rm -f /tmp/.X99-lock
exit $status
