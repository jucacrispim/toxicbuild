#!/bin/sh

if [ "$ENV" = "ci" ]
then
   git-crypt unlock ~/.keys/toxictest-gcrypt.key
fi

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
behave -c tests/integrations_functional/
status=$?
killall Xvfb
exit $status
