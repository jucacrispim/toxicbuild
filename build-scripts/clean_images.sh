#!/bin/bash

# clean old image to save disk space
echo "Cleaning images"

docker rmi $(docker images --filter "before=toxicbase:latest"  -q) &> /dev/null
docker rmi $(docker images --filter "before=toxictest:latest"  -q) &> /dev/null
docker rmi $(docker images --filter "before=toxictest-selenium:latest"  -q) &> /dev/null

# always work
exit 0
