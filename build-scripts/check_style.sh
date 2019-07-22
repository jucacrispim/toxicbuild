#!/bin/bash

flake=`flake8 --select W --select E toxicbuild tests --exclude=tests/functional/data`;


if [ "$flake" != "" ]
then
    echo "#### Ops! some thing went WRONG! ####";
    echo "$flake";
    exit 1
else
    echo "hell yeah! nice code, mate.";
    exit 0;
fi
