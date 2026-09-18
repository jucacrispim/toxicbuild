#!/bin/bash

project=toxicbuild
cd docs/build
mv html $project
tar -czf docs.tar.gz $project

curl -F 'file=@docs.tar.gz' https://docs.poraodojuca.dev/e/ -H "Authorization: Key $TUPI_AUTH_KEY"
