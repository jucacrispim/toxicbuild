#!/bin/sh

Xvfb :99  -ac -screen 0, 1368x768x24 &
behave tests/functional/webui
status=$?
killall Xvfb
exit $status
