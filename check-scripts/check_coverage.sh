#!/bin/sh

err=`coverage run --source=toxicbuild setup.py test --test-suite=tests.unit -q`;
coverage=`coverage report -m | grep TOTAL | sed 's/TOTAL\s*\w*\s*\w*\s*//g' | cut -d'%' -f1`

echo 'coverage was:' $coverage'%'

if [ "$err" != "" ]
then
    if [ $coverage -eq 100 ]
    then
	echo "But something went wrong";
	echo "$err";
	exit 1
    fi
fi

if [ $coverage -eq 100 ]
then
    if [ "$err" != "" ]
    then
	echo "And something went wrong";
	echo "$err";
	exit 1;
    else
	echo "Everything ok, buddy!";
	exit 0;
    fi

else
    coverage report -m
    exit 1
fi
