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


create_images(){
    create_debian_generic
    create_debian_generic_docker
    create_debian_python37
    create_debian_python37_docker
    create_debian_python36
    create_debian_python36_docker
    create_debian_python35
    create_debian_python35_docker
}


upload_images(){
    docker push jucacrispim/toxiccontainers:debian-generic
    docker push jucacrispim/toxiccontainers:debian-generic-docker
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
