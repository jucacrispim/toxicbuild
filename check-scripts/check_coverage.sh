#!/bin/sh

ERRORFILE="errors.txt"
coverage run --source=$1 setup.py test --test-suite=tests.unit -q 1>/dev/null 2>$ERRORFILE;
haserr=`grep FAILED $ERRORFILE`;
err=`cat $ERRORFILE`
rm $ERRORFILE;
coverage=`coverage report -m | grep TOTAL | sed 's/TOTAL\s*\w*\s*\w*\s*//g' | cut -d'%' -f1`

echo 'coverage was:' $coverage'%'

if [ "$haserr" != "" ]
then
    if [ $coverage -eq $2 ]
    then
	echo "But something went wrong";
	echo "$err";
	exit 1
    fi
fi

if [ $coverage -eq $2 ]
then
    if [ "$haserr" != "" ]
    then
	echo "And something went wrong";
	echo "$err";
	exit 1;
    else
	echo "Yay! Everything ok!";
	exit 0;
    fi

else
    coverage report -m
    exit 1
fi
