#!/bin/sh

if [ "$ENV" = "ci" ]
then
    echo "$GCRYPTKEY" | base64 -d > ~/toxictest-gcrypt.key
    git-crypt unlock ~/toxictest-gcrypt.key
fi

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
behave -c tests/integrations_functional/
status=$?
killall Xvfb
rm -f /tmp/.X99-lock
exit $status
