#!/bin/bash

# clean old image to save disk space
echo "Cleaning environment..."

echo "  Stopping containers..."
docker stop $(docker ps -q) &> /dev/null
echo "  Done!"
echo ""

echo "  Removing containers..."
docker rm $(docker ps -a -q) &> /dev/null
echo "  Done!"
echo ""

echo "  Removing old images..."
docker rmi $(docker images --filter "before=toxicbase"  -q) &> /dev/null
docker rmi $(docker images --filter "before=toxictest"  -q) &> /dev/null
docker rmi $(docker images --filter "before=toxictest-selenium"  -q) &> /dev/null
echo "  Done!"
echo ""

echo "Environment clean!"


# always work
exit 0
