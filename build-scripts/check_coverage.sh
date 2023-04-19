#!/bin/sh

echo "\nChecking coverage for Python code\n"
OUT=`coverage run --source=toxicbuild --branch --omit=toxicbuild/script.py,toxicbuild/master/__init__.py,toxicbuild/master/cmds.py,toxicbuild/slave/__init__.py,toxicbuild/slave/cmds.py,toxicbuild/poller/cmds.py,toxicbuild/ui/__init__.py,toxicbuild/ui/cmds.py,toxicbuild/integrations/__init__.py,toxicbuild/integrations/cmds.py,toxicbuild/integrations/monkey.py,toxicbuild/output/__init__.py,toxicbuild/output/cmds.py,toxicbuild/script.py,toxicbuild/poller/__init__.py setup.py test --test-suite=tests.unit`;
ERROR=$?
cov_threshold=100
coverage html;
coverage=`coverage report -m | grep TOTAL | sed 's/TOTAL\s*\w*\s*\w*\s*\w*\s*\w*//g' | cut -d'%' -f1`

echo 'coverage was:' $coverage'%'

if [ "$ERROR" != "0" ]
then
    if [ $coverage -eq "$cov_threshold" ]
    then
	echo "But something went wrong";
	echo "$OUT";
	exit 1
    else
	echo "And something went wrong"
	echo "$OUT";
	exit 1
    fi
fi

if [ $coverage -eq "$cov_threshold" ]
then
    echo "Yay! Everything ok!";
    exit 0;
else
    coverage report -m
    exit 1
fi
