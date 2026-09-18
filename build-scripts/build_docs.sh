#!/bin/bash

cd docs
rm -rf "$PWD/build"
make html
