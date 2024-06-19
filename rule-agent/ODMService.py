#
#    Copyright 2024 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import requests
from requests.auth import HTTPBasicAuth
import logging
import json
import os 
from RuleService import RuleService

class ODMService(RuleService):
    def __init__(self):

        # data to send as the POST payload
        self.payload =   {
         
        }
        self.trace={ 
            "__TraceFilter__": {
                "none": True,
                "infoTotalRulesFired": True,
                "infoRulesFired": True
                }
            }
        # authentification
        self.username = os.getenv("ODM_USERNAME","odmAdmin")
        self.password = os.getenv("ODM_PASSWORD","odmAdmin")

        self.server_url =  os.getenv("ODM_SERVER_URL","http://localhost:9060")
        
        if (not self.server_url.startswith("http://")):
            self.server_url = "http://" + self.server_url

        self.isConnected = self.checkODMServer()
        
    def invokeDecisionService(self, rulesetPath, decisionInputs):
        # POST with basic auth        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        params = {**decisionInputs, **self.trace}

        try:
            # print("URL : "+self.server_url+'/DecisionService/rest'+rulesetPath)

            response = requests.post(self.server_url+'/DecisionService/rest'+rulesetPath, headers=headers,
                                    json=params, auth=HTTPBasicAuth(self.username, self.password))

            # check response
            if response.status_code == 200:
                return response.json()
                #return "```\n"+str(json.dumps(response.json(), indent=2))+"\n```"
            else:
                print(f"Request error, status: {response.status_code}")
        except requests.exceptions.RequestException as e:  
            return {"error": "An error occured when invoking the Decision Service. "}
    


    def checkODMServer(self):

        print("Checking connection to ODM Server: " + self.server_url + '/res/api/v1/ruleapps')
        
        try:
            response = requests.get(self.server_url+"/res/api/v1/ruleapps", json=self.payload, auth=HTTPBasicAuth(self.username, self.password))
        
            if response.status_code != 200:
                print(f"Unable to reach Decision Server console, status: {response.status_code}")
                return False

            response = requests.get(self.server_url+"/DecisionService", json=self.payload, auth=HTTPBasicAuth(self.username, self.password))
        
            if response.status_code != 200:
                print(f"Unable to reach Decision Server Runtime , status: {response.status_code}")
                return False
            else:
                print(f"Connection with ODM Server is OK")
                return True
        except requests.exceptions.RequestException as e:  
            print("Unable to reach ODM Runtime:",e)
            return False
   