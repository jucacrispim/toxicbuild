#!/bin/bash

create_debian_generic(){
    docker build -f build-images/debian/Dockerfile-debian-generic -t toxic-debian-generic build-images/debian
    docker tag toxic-debian-generic jucacrispim/toxiccontainers:debian-generic
}

create_debian_generic_docker(){
    docker build -f build-images/debian/Dockerfile-debian-generic-docker -t toxic-debian-generic-docker build-images/debian
    docker tag toxic-debian-generic-docker jucacrispim/toxiccontainers:debian-generic-docker
}


create_debian_python311(){
    docker build -f build-images/debian/Dockerfile-debian-python3.11 -t toxic-debian-python311 build-images/debian
    docker tag toxic-debian-python311 jucacrispim/toxiccontainers:debian-python3.11
}


create_debian_python312(){
    docker build -f build-images/debian/Dockerfile-debian-python3.12 -t toxic-debian-python312 build-images/debian
    docker tag toxic-debian-python312 jucacrispim/toxiccontainers:debian-python3.12
}

create_debian_python313(){
    docker build -f build-images/debian/Dockerfile-debian-python3.13 -t toxic-debian-python313 build-images/debian
    docker tag toxic-debian-python313 jucacrispim/toxiccontainers:debian-python3.13
}


create_debian_go114(){
    docker build -f build-images/debian/Dockerfile-debian-go-1.14 -t toxic-debian-go114 build-images/debian
    docker tag toxic-debian-go114 jucacrispim/toxiccontainers:debian-go1.14
}

create_debian_go120(){
    docker build -f build-images/debian/Dockerfile-debian-go-1.20 -t toxic-debian-go120 build-images/debian
    docker tag toxic-debian-go120 jucacrispim/toxiccontainers:debian-go1.20
}

create_debian_python311_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.11-docker -t toxic-debian-python311-docker build-images/debian
    docker tag toxic-debian-python311-docker jucacrispim/toxiccontainers:debian-python3.11-docker
}

create_debian_python312_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.12-docker -t toxic-debian-python312-docker build-images/debian
    docker tag toxic-debian-python312-docker jucacrispim/toxiccontainers:debian-python3.12-docker
}

create_debian_python313_docker(){
    docker build -f build-images/debian/Dockerfile-debian-python3.13-docker -t toxic-debian-python313-docker build-images/debian
    docker tag toxic-debian-python313-docker jucacrispim/toxiccontainers:debian-python3.13-docker
}

create_debian_go114_docker(){
    docker build -f build-images/debian/Dockerfile-debian-go-1.14-docker -t toxic-debian-go114-docker build-images/debian
    docker tag toxic-debian-go114-docker jucacrispim/toxiccontainers:debian-go1.14-docker
}

create_debian_go120_docker(){
    docker build -f build-images/debian/Dockerfile-debian-go-1.20-docker -t toxic-debian-go120-docker build-images/debian
    docker tag toxic-debian-go120-docker jucacrispim/toxiccontainers:debian-go1.20-docker
}


create_images(){
    create_debian_go114
    create_debian_go114_docker
    create_debian_go120
    create_debian_go120_docker
    create_debian_generic
    create_debian_generic_docker
    create_debian_python313
    create_debian_python313_docker
    create_debian_python312
    create_debian_python312_docker
    create_debian_python311
    create_debian_python311_docker
}


upload_images(){
    docker push jucacrispim/toxiccontainers:debian-go1.14
    docker push jucacrispim/toxiccontainers:debian-go1.14-docker
    docker push jucacrispim/toxiccontainers:debian-go1.20
    docker push jucacrispim/toxiccontainers:debian-go1.20-docker
    docker push jucacrispim/toxiccontainers:debian-generic
    docker push jucacrispim/toxiccontainers:debian-generic-docker
    docker push jucacrispim/toxiccontainers:debian-python3.13
    docker push jucacrispim/toxiccontainers:debian-python3.13-docker
    docker push jucacrispim/toxiccontainers:debian-python3.12
    docker push jucacrispim/toxiccontainers:debian-python3.12-docker
    docker push jucacrispim/toxiccontainers:debian-python3.11
    docker push jucacrispim/toxiccontainers:debian-python3.11-docker
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
