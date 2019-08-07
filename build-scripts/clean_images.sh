#!/bin/bash

# clean old image to save disk space

docker rmi $(docker images -f "dangling=true" -q)
docker rmi $(docker images --filter "before=toxicbase:latest"  -q)
docker rmi $(docker images --filter "before=toxictest:latest"  -q)
docker rmi $(docker images --filter "before=toxictest-selenium:latest"  -q)

# delete old replicasets
kubectl get rs | egrep '0\s+0\s+0' | cut -d' ' -f1 | xargs kubectl delete rs

# always work
exit 0
