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
from flask import Flask, request
from flask_cors import CORS
from RuleAIAgent import RuleAIAgent
from AIAgent import AIAgent
from RuleAIAgent2 import RuleAIAgent2
from CreateLLM import createLLM
from ODMService import ODMService
from ADSService import ADSService
import json,os
from Utils import find_descriptors

ROUTE="/rule-agent"

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# create a LLM service
llm = createLLM()

print("Using LLM model: ", llm.model_id)

# Try to create adsService, If ADSService is not defined or fails to initialize, fall back to odmService
def get_rule_services():
    try:
        adsService = ADSService()
        return {"ads": adsService}
    except (NameError, AttributeError):
        pass
    odmService = ODMService()
    return {"odm": odmService}

ruleServices = {"odm": ODMService()}


# create Decision services (ODM and ADS)
#odmService = ODMService()
#adsService = ADSService()
#ruleServices = { "odm": odmService, "ads": adsService}

# create an AI Agent using Decision Services
ruleAIAgent = RuleAIAgent(llm, ruleServices)
# alternative way to implement a chain using tools
# ruleAIAgent = RuleAIAgent2(llm, ruleServices)

# create an AI Agent using RAG only
aiAgent = AIAgent(llm)

def ingestAllDocuments(directory_path):
    """Reads all PDF files in a directory and returns a list of document to load.

    :param directory_path: The path to the directory containing the JSON files.
    :return: A list of ToolDescriptor instances.
    """
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            print("Ingesting document : "+file_path)
            aiAgent.ingestDocument(file_path)

catalog_dirs = find_descriptors('catalog')
for directory in catalog_dirs:
    ingestAllDocuments(directory)
    
# Web Service routes

@app.route(ROUTE + '/chat_with_tools', methods=['GET'])
def chat_with_tools():
#    if (not odmService.isConnected and not adsService.isConnected):
#        print("Error: Not connected to any Decision runtime")
#        return {'output' : 'Not connected to any Decision runtime', 'type' : 'error'}

    userInput = request.args.get('userMessage')    
    print("chat_with_tools: received request ", userInput) 
    response = ruleAIAgent.processMessage(userInput)    
    # response = ruleAIAgent2.processMessage(userInput)
    # print("response: ", response)  
    return response

@app.route(ROUTE + '/chat_without_tools', methods=['GET'])
def chat_without_tools():
    userInput = request.args.get('userMessage')    
    print("chat_without_tools: received request ", userInput) 
    response = aiAgent.processMessage(userInput)  
    # print("response: ", response)  
    return response

print ('Running chat service')

if __name__ == '__main__':
    app.run(debug=True)
