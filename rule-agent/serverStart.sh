#!/bin/bash
. deploy_ruleapp_to_odm.sh

# Check environment variable
if [[ -z "$DATADIR" ]]; then
    DATADIR="../data"
    echo "DATADIR Environment variable not found. Using $DATADIR to retrieve materials."
fi



search_and_deploy_ruleapp
python3 -m flask --app ChatService run --port 9000 --host 0.0.0.0