#!/bin/sh

ERRORFILE="errors.txt"
echo "\nChecking coverage for Python code\n"
coverage run --source=$1 --branch setup.py test --test-suite=tests.unit -q 1>/dev/null 2>$ERRORFILE;
haserr=`grep FAILED $ERRORFILE`;
err=`cat $ERRORFILE`
rm $ERRORFILE;
coverage=`coverage report -m | grep TOTAL | sed 's/TOTAL\s*\w*\s*\w*\s*\w*\s*\w*//g' | cut -d'%' -f1`

echo 'coverage was:' $coverage'%'

if [ "$haserr" != "" ]
then
    if [ $coverage -eq $2 ]
    then
	echo "But something went wrong";
	echo "$err";
	exit 1
    else
	echo "And something went wrong"
	echo "$err";
	exit 1
    fi
fi

if [ $coverage -eq $2 ]
then
    echo "Yay! Everything ok!";
    exit 0;
else
    coverage report -m
    exit 1
fi
