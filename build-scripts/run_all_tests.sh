#!/bin/bash

check_run_ok(){
    if [ $? != "0" ]
    then
	exit 1;
    fi
}

echo "\n"
echo "#############################\n"
echo "# Running python unit tests #\n"
echo "#############################\n"
echo "\n"
sh ./build-scripts/check_coverage.sh toxicbuild 100

check_run_ok;

echo "\n"
echo "###################################\n"
echo "# Running python functional tests #\n"
echo "###################################\n"
echo "\n"
python setup.py test --test-suite=tests.functional

check_run_ok;

echo "\n"
echo "###########################\n"
echo "# Running selenium  tests #\n"
echo "###########################\n"
echo "\n"
sh ./build-scripts/run_selenium_tests.sh

check_run_ok;
