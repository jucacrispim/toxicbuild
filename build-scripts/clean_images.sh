#!/bin/bash

# clean old image to save disk space

docker rmi $(docker images -f "dangling=true" -q)
docker rmi $(docker images --filter "before=toxicbase:latest"  -q)
docker rmi $(docker images --filter "before=toxictest:latest"  -q)
docker rmi $(docker images --filter "before=toxictest-selenium:latest"  -q)

# always work
exit 0
