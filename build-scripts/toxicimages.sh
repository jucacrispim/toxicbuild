#!/bin/bash

create_debian_generic(){
    docker build -f build-images/debian/Dockerfile-debian-generic -t toxic-debian-generic build-images/debian
    docker tag toxic-debian-generic jucacrispim/toxiccontainers:debian-generic
}

create_debian_generic_docker(){
    docker build -f build-images/debian/Dockerfile-debian-generic-docker -t toxic-debian-generic-docker build-images/debian
    docker tag toxic-debian-generic-docker jucacrispim/toxiccontainers:debian-generic-docker
}

create_debian_python35(){
    docker build -f build-images/debian/Dockerfile-debian-python3.5 -t toxic-debian-python35 build-images/debian
    docker tag toxic-debian-python35 jucacrispim/toxiccontainers:debian-python3.5
}

create_debian_python36(){
    docker build -f build-images/debian/Dockerfile-debian-python3.6 -t toxic-debian-python36 build-images/debian
    docker tag toxic-debian-python36 jucacrispim/toxiccontainers:debian-python3.6
}

create_debian_python37(){
    docker build -f build-images/debian/Dockerfile-debian-python3.7 -t toxic-debian-python37 build-images/debian
    docker tag toxic-debian-python37 jucacrispim/toxiccontainers:debian-python3.7
}

create_debian_python38(){
    docker build -f build-images/debian/Dockerfile-debian-python3.8 -t toxic-debian-python38 build-images/debian
    docker tag toxic-debian-python38 jucacrispim/toxiccontainers:debian-python3.8
}

create_debian_python39(){
    docker build -f build-images/debian/Dockerfile-debian-python3.9 -t toxic-debian-python39 build-images/debian
    docker tag toxic-debian-python39 jucacrispim/toxiccontainers:debian-python3.9
}

create_debian_python310(){
    docker build -f build-images/debian/Dockerfile-debian-python3.10 -t toxic-debian-python310 build-images/debian
    docker tag toxic-debian-python310 jucacrispim/toxiccontainers:debian-python3.10
}

create_debian_python311(){
    docker build -f build-images/debian/Dockerfile-debian-python3.11 -t toxic-debian-python311 build-images/debian
    docker tag toxic-debian-python311 jucacrispim/toxiccontainers:debian-python3.11
}



create_debian_go114(){
    docker build -f build-images/debian/Dockerfile-debian-go-1.14 -t toxic-debian-go114 build-images/debian
    docker tag toxic-debian-go114 jucacrispim/toxiccontainers:debian-go1.14
}

create_debian_python35_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.5-docker -t toxic-debian-python35-docker build-images/debian
    docker tag toxic-debian-python35-docker jucacrispim/toxiccontainers:debian-python3.5-docker
}

create_debian_python36_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.6-docker -t toxic-debian-python36-docker build-images/debian
    docker tag toxic-debian-python36-docker jucacrispim/toxiccontainers:debian-python3.6-docker
}

create_debian_python37_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.7-docker -t toxic-debian-python37-docker build-images/debian
    docker tag toxic-debian-python37-docker jucacrispim/toxiccontainers:debian-python3.7-docker
}

create_debian_python38_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.8-docker -t toxic-debian-python38-docker build-images/debian
    docker tag toxic-debian-python38-docker jucacrispim/toxiccontainers:debian-python3.8-docker
}

create_debian_python39_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.9-docker -t toxic-debian-python39-docker build-images/debian
    docker tag toxic-debian-python39-docker jucacrispim/toxiccontainers:debian-python3.9-docker
}

create_debian_python310_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.10-docker -t toxic-debian-python310-docker build-images/debian
    docker tag toxic-debian-python310-docker jucacrispim/toxiccontainers:debian-python3.10-docker
}

create_debian_python311_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.11-docker -t toxic-debian-python311-docker build-images/debian
    docker tag toxic-debian-python311-docker jucacrispim/toxiccontainers:debian-python3.11-docker
}



create_debian_go114_docker(){
    docker build -f build-images/debian/Dockerfile-debian-go-1.14-docker -t toxic-debian-go114-docker build-images/debian
    docker tag toxic-debian-go114-docker jucacrispim/toxiccontainers:debian-go1.14-docker
}


create_images(){
    create_debian_go114
    create_debian_go114_docker
    create_debian_generic
    create_debian_generic_docker
    create_debian_python311
    create_debian_python311_docker
    create_debian_python310
    create_debian_python310_docker
    create_debian_python39
    create_debian_python39_docker
    create_debian_python38
    create_debian_python38_docker
    create_debian_python37
    create_debian_python37_docker
    create_debian_python36
    create_debian_python36_docker
    create_debian_python35
    create_debian_python35_docker
}


upload_images(){
    docker push jucacrispim/toxiccontainers:debian-go1.14
    docker push jucacrispim/toxiccontainers:debian-go1.14-docker
    docker push jucacrispim/toxiccontainers:debian-generic
    docker push jucacrispim/toxiccontainers:debian-generic-docker
    docker push jucacrispim/toxiccontainers:debian-python3.11
    docker push jucacrispim/toxiccontainers:debian-python3.11-docker
    docker push jucacrispim/toxiccontainers:debian-python3.10
    docker push jucacrispim/toxiccontainers:debian-python3.10-docker
    docker push jucacrispim/toxiccontainers:debian-python3.9
    docker push jucacrispim/toxiccontainers:debian-python3.9-docker
    docker push jucacrispim/toxiccontainers:debian-python3.8
    docker push jucacrispim/toxiccontainers:debian-python3.8-docker
    docker push jucacrispim/toxiccontainers:debian-python3.7
    docker push jucacrispim/toxiccontainers:debian-python3.7-docker
    docker push jucacrispim/toxiccontainers:debian-python3.6
    docker push jucacrispim/toxiccontainers:debian-python3.6-docker
    docker push jucacrispim/toxiccontainers:debian-python3.5
    docker push jucacrispim/toxiccontainers:debian-python3.5-docker
}

case "$1" in

    create)
	create_images
	;;

    upload)
	upload_images
	;;

    *)
	echo "Usage toxicimages.sh {create|upload}"
	exit 1;

esac
