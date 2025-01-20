#!/bin/bash


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
search_and_deploy_ruleapp(){
  # Directory containing the .jar files
  directory="$DATADIR"

  # Iterate over all .jar files in the directory
  echo "$directory"**/decisionapps/*.jar
  for jar_file in "$directory"/**/decisionapps/*.jar; do
    if [[ -f "$jar_file" ]]; then
      process_jar_file "$jar_file"
    else
      echo "No .jar files found in $directory"
    fi
  done
}









