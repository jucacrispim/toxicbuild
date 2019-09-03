#!/bin/bash

# clean old image to save disk space
echo "Cleaning images"

docker rmi $(docker images --filter "before=toxicbase"  -q) &> /dev/null
docker rmi $(docker images --filter "before=toxictest"  -q) &> /dev/null
docker rmi $(docker images --filter "before=toxictest-selenium"  -q) &> /dev/null

# always work
exit 0
