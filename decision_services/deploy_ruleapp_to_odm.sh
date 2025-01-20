#!/bin/bash

# Check environment variable
if [[ -z "$ODM_SERVER_URL" ]]; then
    echo "ODM_SERVER Environment variable not found. Using http://localhost:9060 URL."
    ODM_SERVER_URL=http://localhost:9060
fi


# Function to be called for each .jar file
process_jar_file() {
  local jar_file="$1"
  echo "Processing $jar_file"
  # Deploy the Decision Service
  result=$(curl -o /dev/null -s -w "%{http_code}" $ODM_SERVER_URL/res/api/v1/ruleapps -u odmAdmin:odmAdmin -q | grep -q ^200 && echo 0 || echo 1)
  if [[ $result -eq 0 ]]; then

    deployed=$(curl -X POST --data-binary @$1 $ODM_SERVER_URL/res/api/v1/ruleapps -H "Content-Type: application/octet-stream" -u odmAdmin:odmAdmin -s)

    isDeployed=$(echo "$deployed" | grep -q "succeeded>true</succeeded")
    if [[ $isDeployed -eq 0 ]]; then
      echo "Ruleapp $jar_file is successfully deployed !."
    else
      echo "Cannot deploy Rules archive"
      echo "Please Verify your ODM Server".
    fi 
  else 
    echo "Cannot connect to the ODM Server URL : $ODM_SERVER_URL. Exiting"
    exit 1
  fi 
}

process_jar_file $1

