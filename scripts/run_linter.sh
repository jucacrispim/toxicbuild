#!/bin/bash

pylint toxicbuild/
if [ $? != "0" ]
then
    exit 1;
fi

flake8 toxicbuild/

if [ $? != "0" ]
then
    exit 1;
fi

flake8 doctools.py docs/extensions.py
exit $?;
