#!/bin/bash

pep=`pep8 toxicbuild/`;
peep=`pep8 tests/`;
flakes=`pyflakes toxicbuild tests`;
errors=0;

if  [ "$pep" != "" ]
then
    errors=1;
fi

if [ "$peep" != "" ]
then
    errors=1;
fi

if [ "$flakes" != "" ]
then
    errors=1;
fi

if [ $errors -eq 1 ]
then
    echo "#### Ops! some thing went WRONG! ####";

    echo "$pep";
    echo "$peep";
    echo "$flakes";
    exit 1
else
    echo "hell yeah! nice code, mate.";
    exit 0;
fi
