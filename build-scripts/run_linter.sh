#!/bin/bash

pylint toxicbuild/
if [ $? != "0" ]
then
    exit 1;
fi

flake8 --select F tests --exclude=tests/functional/data
exit $?;
