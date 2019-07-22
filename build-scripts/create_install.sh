#!/bin/bash

DOCKER_DIR="ops/docker"
BASE_DIST_DIR="$DOCKER_DIR/dist"
DIST_DIR="$BASE_DIST_DIR/toxicbuild"

create_dist(){
    # Copies the source files to a dist/ dir in the docker env
    mkdir -p $DIST_DIR
    cp setup.py $DIST_DIR
    cp requirements.txt $DIST_DIR
    cp MANIFEST.in $DIST_DIR
    cp README $DIST_DIR
    cp -r toxicbuild $DIST_DIR
    cp -r scripts $DIST_DIR
}


create_base_img(){
    # Creates the base Docker image
    docker build -f $DOCKER_DIR/Dockerfile-base -t toxicbase $DOCKER_DIR
}

create_slave_img(){
    # Creates the base Docker image
    out=`docker build -f $DOCKER_DIR/Dockerfile-slave -t toxicslave $DOCKER_DIR | grep 'access token:' | cut -d':' -f2`
    echo $out
}


clean(){
    rm -rf $BASE_DIST_DIR
}

# run stuff
create_dist
create_base_img
slave_token=`create_slave_img`
echo $slave_token

# clean everything after the build
clean
