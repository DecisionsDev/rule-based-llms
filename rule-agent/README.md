# Rule Agent Service

This is a Python Rule Agent Service implementing a REST API to interface LLMs and Decision Services. 

## Setup 

In the directory, install Python requirements: 
```
pip3 install -r requirements.txt
```

To run the service, use the following command:
```
python3 -m flask --app ChatService run --port 9000
```

Note: if you want to deploy the ODM ruleapp for the HR Service sample, use the ```serverStart.sh``` shell script. 

## Usage

To invoke the API, use the following Curl command:

```
curl -G "http://localhost:9000/rule-agent/chat_with_tools" --data-urlencode "userMessage=John Doe is an Acme Corp employee who has been hired on November 1st, 1999. How many vacation day the employee John Doe can take each year?"
```

```
curl -G "http://localhost:9000/rule-agent/chat_without_tools" --data-urlencode "userMessage=John Doe is an Acme Corp employee who has been hired on November 1st, 1999. How many vacation day the employee John Doe can take each year?"
```

```
curl -G "http://localhost:9000/rule-agent/chat_without_tools" --data-urlencode "userMessage=How many US holidays Acme Corp employees observe?"
```
