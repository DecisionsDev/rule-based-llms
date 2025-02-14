#!/bin/bash

# Check environment variable
if [[ -z "$BACKEND_SERVICE" ]]; then
    echo "BACKEND_SERVICE Environment variable not found. Need to specify the backend Server URL location."
    exit 1
else 
    echo "Using ODM Server URL : $BACKEND_SERVICE"
fi


python3 App.py