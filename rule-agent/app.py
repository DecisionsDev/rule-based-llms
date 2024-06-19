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
import os
from langchain_community.llms import Ollama
from RuleAIAgent2 import RuleAIAgent2
from CreateLLM import createLLM
from ODMService import ODMService
from ADSService import ADSService

# create a LLM service
llm = createLLM()

# create Decision services (ODM and ADS)
odmService = ODMService()
adsService = ADSService()
ruleServices = { "odm": odmService, "ads": adsService}
pm_agent = ruleAIAgent = RuleAIAgent2(llm, ruleServices)

query="John wook is an IBM employee who has been hired on November 1st, 2000. How many vacation day the employee John Doe can take each year?"
print ("Query : "+query)

res =  pm_agent.processMessage(query);
print("Result from the LLM using Rules : "+res['output'])
