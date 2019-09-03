#!/bin/bash

# clean old image to save disk space
echo "Cleaning environment..."

echo "  Stopping containers..."
docker stop $(docker ps -q)
echo "  Done!"
echo "\n"

echo "  Removing containers..."
docker rm $(docker ps -a -q)
echo "  Done!"
echo "\n"

echo "  Removing old images..."
docker rmi $(docker images --filter "before=toxicbase"  -q)
docker rmi $(docker images --filter "before=toxictest"  -q)
docker rmi $(docker images --filter "before=toxictest-selenium"  -q)
echo "  Done!"
echo "\n"

echo "Environment clean!"


# always work
exit 0
