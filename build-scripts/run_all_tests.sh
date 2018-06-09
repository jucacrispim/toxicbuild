#!/bin/bash

echo "\n"
echo "#############################\n"
echo "# Running python unit tests #\n"
echo "#############################\n"
echo "\n"
python setup.py test --test-suite=tests.unit

echo "\n"
echo "###################################\n"
echo "# Running python functional tests #\n"
echo "###################################\n"
echo "\n"
python setup.py test --test-suite=tests.functional

echo "\n"
echo "###########################\n"
echo "# Running selenium  tests #\n"
echo "###########################\n"
echo "\n"
sh ./build-scripts/run_selenium_tests.sh
