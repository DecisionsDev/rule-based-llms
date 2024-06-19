#!/bin/bash

podman run -e LICENSE=accept  -m 2048M --memory-reservation 2048M -p 9060:9060 -p 9443:9443 -v $PWD:/data/ -e SAMPLE=false  icr.io/cpopen/odm-k8s/odm:8.12


