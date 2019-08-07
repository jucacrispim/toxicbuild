#!/bin/bash

DOCKER_DIR="ops/docker"
BASE_DIST_DIR="$DOCKER_DIR/dist"
DIST_DIR="$BASE_DIST_DIR/toxicbuild"



is_in_array () {
    # checks if a element is contained by a array
    # from here https://stackoverflow.com/questions/3685970
    local e match="$1"
    shift
    for e; do [[ "$e" == "$match" ]] && return 0; done
    return 1
}


create_dist(){
    # Copy the source files to a dist/ dir in the docker env
    mkdir -p $DIST_DIR
    cp setup.py $DIST_DIR
    cp requirements.txt $DIST_DIR
    cp MANIFEST.in $DIST_DIR
    cp README $DIST_DIR
    cp -r toxicbuild $DIST_DIR
    cp -r scripts $DIST_DIR
    cp -r build-scripts $DIST_DIR
}


pull_imgs(){
    create_images=$1
    # pull the required docker images
    docker pull mongo:4.0
    docker pull rabbitmq:3.7-alpine
    docker pull zookeeper:3.5
    docker pull python:3.7.4-slim-buster

    if [ $create_images -eq "1" ]
    then
	docker pull jucacrispim/toxicbuild:slave
	docker pull jucacrispim/toxicbuild:output
	docker pull jucacrispim/toxicbuild:integrations
	docker pull jucacrispim/toxicbuild:master
	docker pull jucacrispim/toxicbuild:scheduler
	docker pull jucacrispim/toxicbuild:poller
	docker pull jucacrispim/toxicbuild:web
    fi
}


create_base_img(){
    # Creates the base Docker image
    docker build -f $DOCKER_DIR/Dockerfile-base -t toxicbase $DOCKER_DIR
}

create_slave_img(){
    # Creates the base Docker image
    docker build -f $DOCKER_DIR/Dockerfile-slave -t toxicslave $DOCKER_DIR
}

create_output_img(){
    docker build -f $DOCKER_DIR/Dockerfile-output -t toxicoutput $DOCKER_DIR
}


create_master_img(){
    docker build -f $DOCKER_DIR/Dockerfile-master -t toxicmaster $DOCKER_DIR
}

create_scheduler_img(){
    docker build -f $DOCKER_DIR/Dockerfile-scheduler -t toxicscheduler $DOCKER_DIR
}

create_poller_img(){
    docker build -f $DOCKER_DIR/Dockerfile-poller -t toxicpoller $DOCKER_DIR
}

create_integrations_img(){
    docker build -f $DOCKER_DIR/Dockerfile-integrations -t toxicintegrations $DOCKER_DIR &> /dev/null
}


create_web_img(){
    docker build -f $DOCKER_DIR/Dockerfile-web -t toxicweb $DOCKER_DIR &> /dev/null
}


create_imgs(){
    create_base_img
    create_slave_img
    create_output_img
    create_master_img
    create_scheduler_img
    create_poller_img
    create_integrations_img
    create_web_img
}


create_slave_token(){
    out=`docker-compose -f $DOCKER_DIR/docker-compose.yml run create_slave_token 2> /dev/null`
    enc_token=`echo $out | cut -d':' -f2 | cut -d' ' -f1`
    token=`echo $out | cut -d':' -f3 | cut -d' ' -f1`
    echo "SLAVE_ENCRYPTED_TOKEN=$enc_token" > $DOCKER_DIR/slave.env
    docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_slave_token &> /dev/null
    echo $token
}

create_output_token(){
    out=`docker-compose -f $DOCKER_DIR/docker-compose.yml run create_output_token 2> /dev/null | grep 'access token:' | cut -d':' -f2`
    docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_output_token &> /dev/null
    echo "NOTIFICATIONS_API_TOKEN=$out" > $DOCKER_DIR/master.env
    echo "NOTIFICATIONS_API_TOKEN=$out" > $DOCKER_DIR/integrations.env
    echo "NOTIFICATIONS_API_TOKEN=$out" > $DOCKER_DIR/web.env
    echo $out
}

create_master_token(){
    out=`docker-compose -f $DOCKER_DIR/docker-compose.yml run create_master_token 2> /dev/null`
    enc_token=`echo $out | cut -d':' -f2 | cut -d' ' -f1`
    token=`echo $out | cut -d':' -f3 | cut -d' ' -f1`
    echo "MASTER_ENCRYPTED_TOKEN=$enc_token" > $DOCKER_DIR/master.env
    docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_master_token &> /dev/null
    echo $token
}


create_user(){
    email=$1
    password=$2
    out=`export TOXICMASTER_USER_EMAIL=$email && export TOXICMASTER_USER_PASSWORD=$password && docker-compose -f $DOCKER_DIR/docker-compose.yml up create_user 2> /dev/null  | grep 'with id:' | cut -d':' -f2`
    docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_user &> /dev/null
    docker rm docker_create_user_1 &> /dev/null
    echo $out
}

add_slave(){
    slave_token=$1
    owner_id=$2
    export SLAVE_ACCESS_TOKEN=$slave_token && export SLAVE_OWNER_ID=$owner_id && docker-compose -f $DOCKER_DIR/docker-compose.yml up add_slave &> /dev/null
    docker rm docker_add_slave_1 &> /dev/null
}

update_envfiles(){
    master_token=$1
    root_user_id=$2
    cookie_secret=$3
    output_token=$4
    echo "HOLE_TOKEN=$master_token" > $DOCKER_DIR/web.env
    echo "NOTIFICATIONS_API_TOKEN=$output_token" >> $DOCKER_DIR/web.env
    echo "NOTIFICATIONS_API_TOKEN=$output_token" >> $DOCKER_DIR/integrations.env
    echo "WEB_ROOT_USER_ID=$root_user_id" >> $DOCKER_DIR/web.env
    echo "COOKIE_SECRET=$cookie_secret" >> $DOCKER_DIR/web.env

}


start_local(){
    docker-compose -f ops/docker/docker-compose.yml up web 2> /dev/null
}


create_local_install(){
    create_images=$1

    echo '- Pulling required images'
    pull_imgs $create_images

    if [ $create_images -eq "0" ]
    then
	echo '- Creating docker images'
	create_dist
	create_imgs
    fi

    echo '- Creating environment. Be patient...'

    slave_token=`create_slave_token`
    output_token=`create_output_token`
    master_token=`create_master_token`
    echo -n "  email: "
    read email
    echo -n "  password: "
    read password
    user_id=`create_user $email $password`
    add_slave $slave_token $user_id
    cookie_secret=`python -c 'import secrets; print(secrets.token_urlsafe(), end="")'`
    update_envfiles  $master_token $user_id $cookie_secret $output_token

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
    docker rmi toxicbase
    docker exec -it docker_mongo_1 mongo localhost/toxicbuild --eval "db.dropDatabase()"
}


case "$1" in
    create-local)
	is_in_array "--create-images" "${@}"
	create_images=$?
	create_local_install $create_images
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
