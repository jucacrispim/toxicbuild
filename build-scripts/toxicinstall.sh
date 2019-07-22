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

pull_imgs(){
    # pull the required docker images
    docker pull mongo:4.0
    docker pull rabbitmq:3.7-alpine
    docker pull zookeeper:3.5
    docker pull python:3.7.4-slim-buster
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


create_output_img(){
    _=`docker build -f $DOCKER_DIR/Dockerfile-output -t toxicoutput $DOCKER_DIR`
}


create_output_token(){
    out=`docker-compose -f $DOCKER_DIR/docker-compose.yml up create_output_token 2> /dev/null | grep 'access token:' | cut -d':' -f2`
    _=`docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_output_token 2> /dev/null `
    _=`docker rm docker_create_output_token_1`
    echo $out
}

create_master_img(){
    notification_token=$1
    out=`docker build -f $DOCKER_DIR/Dockerfile-master -t toxicmaster $DOCKER_DIR --build-arg notification_token=$notification_token 2> /dev/null  | grep 'access token:' | cut -d':' -f2`
    echo $out
}

create_scheduler_img(){
    _=`docker build -f $DOCKER_DIR/Dockerfile-scheduler -t toxicscheduler $DOCKER_DIR 2> /dev/null`
}

create_poller_img(){
    _=`docker build -f $DOCKER_DIR/Dockerfile-poller -t toxicpoller $DOCKER_DIR 2> /dev/null`
}

create_user(){
    email=$1
    password=$2
    out=`export TOXICMASTER_USER_EMAIL=$email && export TOXICMASTER_USER_PASSWORD=$password && docker-compose -f $DOCKER_DIR/docker-compose.yml up create_user 2> /dev/null  | grep 'with id:' | cut -d':' -f2`
    _=`docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_user 2> /dev/null `
    _=`docker rm docker_create_user_1`
    echo $out
}

add_slave(){
    slave_token=$1
    owner_id=$2
    _=`export SLAVE_ACCESS_TOKEN=$slave_token && export SLAVE_OWNER_ID=$owner_id && docker-compose -f $DOCKER_DIR/docker-compose.yml up add_slave 2> /dev/null`
    _=`docker rm docker_add_slave_1`
}

create_integrations_img(){
    output_token=$1
    cookie_secret=$2
    _=`docker build -f $DOCKER_DIR/Dockerfile-integrations -t toxicintegrations $DOCKER_DIR --build-arg notification_token=$output_token --build-arg cookie_secret=$cookie_secret`
}

create_web_img(){
    master_token=$1
    output_token=$2
    root_user_id=$3
    cookie_secret=$4
    _=`docker build -f $DOCKER_DIR/Dockerfile-web -t toxicweb $DOCKER_DIR --build-arg master_token=$master_token --build-arg notification_token=$output_token --build-arg root_user_id=$root_user_id --build-arg cookie_secret=$cookie_secret`
}


start_local(){
    docker-compose -f ops/docker/docker-compose.yml up web
}


create_local_install(){
    create_dist

    echo '- Pulling required images'
    pull_imgs
    echo '- Creating toxicbase image. Be patient.'
    create_base_img
    echo '- Creating toxicslave'
    slave_token=`create_slave_img`

    echo '- Creating toxicoutput'
    create_output_img
    output_token=`create_output_token`

    echo '- Creating toxicmaster'
    master_token=`create_master_img $output_token`

    echo -n "  email: "
    read email
    echo -n "  password: "
    read password

    user_id=`create_user $email $password`
    add_slave $slave_token $user_id
    echo '- Creating toxicscheduler'
    create_scheduler_img
    echo '- Creating toxicpoller'
    create_poller_img
    cookie_secret=`python -c 'import secrets; print(secrets.token_urlsafe(), end="")'`
    echo '- Creating toxicintegrations'
    create_integrations_img $output_token $cookie_secret
    echo '- Creating toxicweb'
    create_web_img $master_token $output_token $user_id $cookie_secret

}


clean(){
    rm -rf $BASE_DIST_DIR
}

clean_images(){
    # removes the toxic images except toxicbase
    docker ps -a | egrep 'toxic\w' | cut -d ' ' -f 1 | xargs docker stop
    docker ps -a | egrep 'toxic\w' | cut -d ' ' -f 1 | xargs docker rm
    docker rmi toxicslave
    docker rmi toxicoutput
    docker rmi toxicmaster
    docker rmi toxicscheduler
    docker rmi toxicpoller
    docker rmi toxicintegrations
    docker rmi toxicweb
    docker exec -it docker_mongo_1 mongo localhost/toxicbuild --eval "db.dropDatabase()"
}

case "$1" in
    create-local)
	create_local_install
	clean
	;;

    clean-local)
	clean_images
	;;

    start-local)
	start_local
	;;

    *)
	echo "Usage: toxicinstall.sh {create-local|clean-local|start-local}";
	exit 1;

esac
