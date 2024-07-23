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
from CreateLLMLocal import createLLMLocal
from CreateLLMWatson import  createLLMWatson
from CreateLLMBAM import  createLLMBAM

def createLLM():
    llm_type = os.getenv("LLM_TYPE","LOCAL_OLLAMA")
    if llm_type == "LOCAL_OLLAMA":
        print("Using LLM Service: Ollama")
        return createLLMLocal()
    elif llm_type == "BAM":
        print("Using LLM Service: IBM BAM")
        return createLLMBAM()
    elif llm_type == "WATSONX":
        print("Using LLM Service: IBM watsonx.ai")
        return createLLMWatson()
    else:
        print ("Env variable LLM_TYPE not defined.")
        return None
    

