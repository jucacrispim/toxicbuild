#!/bin/bash

# clean old image to save disk space
echo "Cleaning images"

docker rmi $(docker images --filter "before=toxicbase"  -q)
docker rmi $(docker images --filter "before=toxictest"  -q)
docker rmi $(docker images --filter "before=toxictest-selenium"  -q)


# always work
exit 0
