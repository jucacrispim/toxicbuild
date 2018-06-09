#!/bin/bash

pylint toxicbuild/
flake8 --select F tests --exclude=tests/functional/data
