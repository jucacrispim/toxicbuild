#!/bin/sh

err=`coverage run --source=toxicbuild --omit="*migrations*" setup.py test --test-suite=tests.unit -q 2>&1 | egrep -i 'fail|error'`;
coverage=`coverage report -m | grep TOTAL | sed 's/TOTAL\s*\w*\s*\w*\s*//g' | cut -d'%' -f1`

echo 'coverage was:' $coverage '%'

if [ "$err" != "" ]
then
    echo "But something went wrong";
    exit 1;
fi

if [ $coverage -eq 100 ]
then
    exit 0
else
    coverage report -m
    exit 1
fi
