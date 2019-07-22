#!/bin/bash
cd docs
export TOXICMASTER_SETTINGS="$PWD/../tests/functional/data/master/toxicmaster.conf"
export TOXICSLAVE_SETTINGS="$PWD/../tests/functional/data/slave/toxicslave.conf"
export TOXICUI_SETTINGS="$PWD/../tests/functional/data/ui/toxicui.conf"
export TOXICOUTPUT_SETTINGS="$PWD/../tests/functional/data/output/toxicoutput.conf"
export PYTHONPATH="$PWD/../"
rm -rf "$PWD/source/apidoc"
rm -rf "$PWD/build"
sphinx-apidoc -o "$PWD/source/apidoc" "$PWD/../toxicbuild/"
make html
