#!/bin/bash

DOCKER_DIR="ops/docker"
BASE_DIST_DIR="$DOCKER_DIR/dist"
DIST_DIR="$BASE_DIST_DIR/toxicbuild"
TEST_DIST_DIR="$DOCKER_DIR/test-dist"



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
    mkdir -p $TEST_DIST_DIR

    find . -iname '*.pyc' | xargs rm &> /dev/null

    cp setup.py $DIST_DIR
    cp requirements.txt $DIST_DIR
    cp MANIFEST.in $DIST_DIR
    cp README $DIST_DIR
    cp -r toxicbuild $DIST_DIR
    cp -r scripts $DIST_DIR

    # files may be here from tests
    find . -iname '*.log' | xargs rm &> /dev/null
    rm -rf "tests/functional/data/master/src/"
    rm -rf "tests/functional/data/poller/src/"
    rm -rf "tests/functional/data/slave/src/"

    cp pylintrc $TEST_DIST_DIR
    cp toxicslave.conf $TEST_DIST_DIR
    cp settings.py $TEST_DIST_DIR
    cp -r build-scripts $TEST_DIST_DIR
    cp -r tests $TEST_DIST_DIR
    cp -r .git $DIST_DIR
}


pull_imgs(){
    create_images=$1
    # pull the required docker images
    docker pull mongo:4.2.1
    docker pull rabbitmq:3.7.23-alpine
    docker pull zookeeper:3.5.6
    docker pull python:3.7.4-slim-buster

    if [ $create_images -eq "1" ]
    then
	docker pull jucacrispim/toxicbuild:slave
	docker pull jucacrispim/toxicbuild:output
	docker pull jucacrispim/toxicbuild:integrations
	docker pull jucacrispim/toxicbuild:master
	docker pull jucacrispim/toxicbuild:poller
	docker pull jucacrispim/toxicbuild:web
    fi
}


create_base_img(){
    # Creates the base Docker image
    docker build -f $DOCKER_DIR/Dockerfile-base -t toxicbase $DOCKER_DIR
}

create_runtime_img(){
    # Creates the base Docker image
    docker build -f $DOCKER_DIR/Dockerfile-runtime -t toxicruntime $DOCKER_DIR
}

create_base_test_img(){
    docker build -f $DOCKER_DIR/Dockerfile-testbase -t toxictestbase $DOCKER_DIR
}

create_test_img(){
    docker build -f $DOCKER_DIR/Dockerfile-test -t toxictest $DOCKER_DIR
}

create_test_selenium_img(){
        docker build -f $DOCKER_DIR/Dockerfile-selenium -t toxictest-selenium $DOCKER_DIR
}

create_slave_img(){
    docker build -f $DOCKER_DIR/Dockerfile-slave -t toxicslave $DOCKER_DIR
    docker tag toxicslave jucacrispim/toxicbuild:slave
}

create_output_img(){
    docker build -f $DOCKER_DIR/Dockerfile-output -t toxicoutput $DOCKER_DIR
    docker tag toxicoutput jucacrispim/toxicbuild:output
}


create_master_img(){
    docker build -f $DOCKER_DIR/Dockerfile-master -t toxicmaster $DOCKER_DIR
    docker tag toxicmaster jucacrispim/toxicbuild:master
}


create_poller_img(){
    docker build -f $DOCKER_DIR/Dockerfile-poller -t toxicpoller $DOCKER_DIR
    docker tag toxicpoller jucacrispim/toxicbuild:poller
}

create_integrations_img(){
    docker build -f $DOCKER_DIR/Dockerfile-integrations -t toxicintegrations $DOCKER_DIR
    docker tag toxicintegrations jucacrispim/toxicbuild:integrations
}


create_web_img(){
    docker build -f $DOCKER_DIR/Dockerfile-web -t toxicweb $DOCKER_DIR
    docker tag toxicweb jucacrispim/toxicbuild:web
}


create_imgs(){
    create_base_img
    create_runtime_img
    create_slave_img
    create_output_img
    create_master_img
    create_poller_img
    create_integrations_img
    create_web_img
}

upload_images(){
    echo "Uploading slave"
    docker push jucacrispim/toxicbuild:slave
    echo "Uploading output"
    docker push jucacrispim/toxicbuild:output
    echo "Uploading master"
    docker push jucacrispim/toxicbuild:master
    echo "Uploading poller"
    docker push jucacrispim/toxicbuild:poller
    echo "Uploading integrations"
    docker push jucacrispim/toxicbuild:integrations
    echo "Uploading web"
    docker push jucacrispim/toxicbuild:web
}


create_debian_generic_img(){
    docker build -f build-images/debian/Dockerfile-debian-generic -t toxic-debian-generic build-images/debian
    docker tag toxic-debian-generic jucacrispim/toxiccontainers:debian-generic
}


create_debian_py35_img(){
    docker build -f build-images/debian/Dockerfile-debian-generic -t toxic-debian-py35 build-images/debian
    docker tag toxic-debian-py35 jucacrispim/toxiccontainers:debian-python3.5
}


create_debian_py36_img(){
    docker build -f build-images/debian/Dockerfile-debian-generic -t toxic-debian-py36 build-images/debian
    docker tag toxic-debian-py36 jucacrispim/toxiccontainers:debian-python3.6
}


create_debian_py37_img(){
    docker build -f build-images/debian/Dockerfile-debian-generic -t toxic-debian-py37 build-images/debian
    docker tag toxic-debian-py36 jucacrispim/toxiccontainers:debian-python3.7
}


create_build_images(){
    create_debian_generic_img;
    create_debian_py35_img;
    create_debian_py36_img;
    create_debian_py37_img;
}


upload_build_images(){
    docker push jucacrispim/toxiccontainers:debian-generic
    docker push jucacrispim/toxiccontainers:debian-python3.5
    docker push jucacrispim/toxiccontainers:debian-python3.6
    docker push jucacrispim/toxiccontainers:debian-python3.7
}


create_test_env(){
    echo "Creating test environment"

    create_base_img
    create_base_test_img
    create_test_img
    docker-compose -f $DOCKER_DIR/docker-compose.yml up --no-color --exit-code-from setup-env setup-env
}


create_test_selenium_env(){
    echo "Creating selenium test environment"

    create_base_img
    create_base_test_img
    create_test_img
    create_test_selenium_img
    create_local_install "0" "test@bla.com" "123"
    docker-compose -f $DOCKER_DIR/docker-compose.yml up --no-color --exit-code-from setup-env setup-env
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

create_poller_token(){
    out=`docker-compose -f $DOCKER_DIR/docker-compose.yml run create_poller_token 2> /dev/null`
    enc_token=`echo $out | cut -d':' -f2 | cut -d' ' -f1`
    token=`echo $out | cut -d':' -f3 | cut -d' ' -f1`
    echo "POLLER_ENCRYPTED_TOKEN=$enc_token" > $DOCKER_DIR/poller.env
    docker-compose -f $DOCKER_DIR/docker-compose.yml stop create_poller_token &> /dev/null
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
    poller_token=$5
    echo "HOLE_TOKEN=$master_token" >> $DOCKER_DIR/web.env
    echo "HOLE_TOKEN=$master_token" >> $DOCKER_DIR/integrations.env
    echo "NOTIFICATIONS_API_TOKEN=$output_token" >> $DOCKER_DIR/web.env
    echo "NOTIFICATIONS_API_TOKEN=$output_token" >> $DOCKER_DIR/integrations.env
    echo "WEB_ROOT_USER_ID=$root_user_id" >> $DOCKER_DIR/web.env
    echo "WEB_ROOT_USER_ID=$root_user_id" >> $DOCKER_DIR/integrations.env
    echo "COOKIE_SECRET=$cookie_secret" >> $DOCKER_DIR/web.env
    echo "COOKIE_SECRET=$cookie_secret" >> $DOCKER_DIR/integrations.env
    echo "POLLER_TOKEN=$poller_token" >> $DOCKER_DIR/master.env
}


start_local(){
    docker-compose -f ops/docker/docker-compose.yml up -d web 2> /dev/null
}

stop_local(){
    docker-compose -f ops/docker/docker-compose.yml stop web 2> /dev/null
    docker-compose -f ops/docker/docker-compose.yml stop master 2> /dev/null
    docker-compose -f ops/docker/docker-compose.yml stop output 2> /dev/null
    docker-compose -f ops/docker/docker-compose.yml stop poller 2> /dev/null
    docker-compose -f ops/docker/docker-compose.yml stop integrations 2> /dev/null
    docker-compose -f ops/docker/docker-compose.yml stop slave 2> /dev/null
}


create_local_install(){
    create_images=$1
    user_email=$2
    user_password=$3

    echo '- Pulling required images'
    pull_imgs $create_images # &> /dev/null

    if [ $create_images -eq "0" ]
    then
	echo '- Creating docker images'
	create_dist &> /dev/null
	create_imgs &> /dev/null
	clean &> /dev/null
    fi

    echo '- Creating environment. Be patient...'

    slave_token=`create_slave_token`
    output_token=`create_output_token`
    master_token=`create_master_token`
    poller_token=`create_poller_token`

    if [ "$user_email" == "" ]
    then
	echo -n "  email: "
	read email
    else
	email=$user_email
    fi

    if [ "$user_password" == "" ]
    then
	echo -n "  password: "
	read password
    else
	password=$user_password
    fi

    user_id=`create_user $email $password`
    add_slave "$slave_token" "$user_id"
    cookie_secret=`python -c 'import secrets; print(secrets.token_urlsafe(), end="")'`
    update_envfiles "$master_token" "$user_id" "$cookie_secret" "$output_token" "$poller_token"

}


clean(){
    rm -rf $BASE_DIST_DIR
    rm -rf $TEST_DIST_DIR
}

create_empty_envs(){
    [ ! -f $DOCKER_DIR/web.env ] && echo '' > $DOCKER_DIR/web.env
    [ ! -f $DOCKER_DIR/output.env ] && echo '' > $DOCKER_DIR/output.env
    [ ! -f $DOCKER_DIR/master.env ] && echo '' > $DOCKER_DIR/master.env
    [ ! -f $DOCKER_DIR/poller.env ] && echo '' > $DOCKER_DIR/poller.env
    [ ! -f $DOCKER_DIR/slave.env ] && echo '' > $DOCKER_DIR/slave.env
    [ ! -f $DOCKER_DIR/integrations.env ] && echo '' > $DOCKER_DIR/integrations.env
}

drop_db(){
    docker exec -it docker_mongo_1 mongo localhost/toxicbuild --eval "db.dropDatabase()"
    docker kill docker_mongo_1
    docker rm docker_mongo_1
}

clean_images(){
    # removes the toxic images except toxicbase
    docker ps -a | egrep 'toxic\w' | cut -d ' ' -f 1 | xargs docker stop
    docker ps -a | egrep 'toxic\w' | cut -d ' ' -f 1 | xargs docker rm
    docker rmi toxicslave
    docker rmi toxicoutput
    docker rmi toxicmaster
    docker rmi toxicpoller
    docker rmi toxicintegrations
    docker rmi toxicweb
    docker rmi toxictest
    docker rmi toxictest-selenium
    docker rmi toxicruntime
    docker rmi toxicbase
    drop_db
}


case "$1" in
    create-local)
	is_in_array "--create-images" "${@}"
	create_images=$?
	create_local_install $create_images
	clean
	;;

    clean-local)
	clean
	clean_images
	;;

    start-local)
	start_local
	;;

    stop-local)
	stop_local
	;;

    create-images)
	create_dist
	create_imgs
	clean
	;;

    upload-images)
	upload_images
	;;

    create-build-images)
	create_build_images
	;;

    upload-build-images)
	upload_build_images
	;;

    create-test-env)
	drop_db
	create_empty_envs
	create_dist
	create_test_env
	clean
	;;

    create-test-selenium-env)
	drop_db
	create_empty_envs
	create_dist
	create_test_selenium_env
	clean
	;;

    *)
	echo "Usage: toxicinstall.sh OP";
	echo "OPs are:"
	echo " - create-local"
	echo " - clean-local"
	echo " - start-local"
	echo " - stop-local"
	echo " - create-images"
	echo " - upload-images"
	echo " - create-build-images"
	echo " - upload-build-images"
	echo " - create-test-env"
	echo " - create-test-selenium-env"
	exit 1;

esac
