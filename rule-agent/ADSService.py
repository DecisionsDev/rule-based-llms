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

class ADSService(RuleService):
    def __init__(self):
        self.server_url =  os.getenv("ADS_SERVER_URL","https://ads.ibm.com")
        if (not self.server_url.startswith("https://")):
            self.server_url = "https://" + self.server_url

        self.user_id = os.getenv("ADS_USER_ID")
        self.zen_api_key = os.getenv("ADS_ZEN_APIKEY")
        self.isConnected = self.checkADSServer()
        
    def invokeDecisionService(self, rulesetPath, decisionInputs):
        # POST
        headers = {'Content-type': 'application/json', 'Accept': 'application/json', 'Authorization': 'ZenApiKey ' + self.zen_api_key}
        params = {**decisionInputs}

        path = "/ads/runtime/api/v1/deploymentSpaces/embedded/decisions/"
        fullPath = self.server_url + path + '_' + self.user_id + rulesetPath

        try:
            # print("Send to ADS URL : "+ fullPath)

            response = requests.post(fullPath, headers=headers, json=params, verify=False)

            # print("Received response from ADS: ", response)

            # check response
            if response.status_code == 200:
                res = response.json()
                # print("Received answer from ADS: ", res)
                return res
            else:
                return {"error": "An error occured when invoking the Decision Service " + response.status_code }
        except requests.exceptions.RequestException as e:  
            # print("exception invoking the ADS Decision Service: ", e)
            return {"error": "An error occured when invoking the Decision Service. " }
    

    def checkADSServer(self):        
        print("Check connection to ADS Server; " + self.server_url)
        try:
            path = "/ads/runtime/api/v1/about"
            fullPath = self.server_url + path

            response = requests.get(fullPath, verify=False)
            if response.status_code == 200:
                print(f"Connection with ADS Server is OK")
                return True
            else:
                print("error checking ADS server: ", response.status_code)
                return False
        except requests.exceptions.RequestException as e:  
            print("Unable to reach ADS Runtime:",e)
            return False
    