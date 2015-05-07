#!/bin/bash

sources=`echo $1 | tr "," "\n"`
pepit="";

for dir in $sources
do
    errors=`pep8 $dir`
    pepit="$pepit$errors"
done

if [ "$pepit" != "" ]
then
    echo "Ops! something is not ok. pep8 it!";
    echo "$pepit";
    exit 1
else
    echo "hell yeah! great code, mate!"
    exit 0;
fi
