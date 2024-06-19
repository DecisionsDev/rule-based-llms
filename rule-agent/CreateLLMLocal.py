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
from langchain_community.llms import Ollama
import os


def createLLMLocal():
    ollama_server_url=os.getenv("OLLAMA_SERVER_URL","http://localhost:11434")
    ollama_model=os.getenv("OLLAMA_MODEL_NAME","mistral")
    print("Using Ollma Server: "+str(ollama_server_url))
    return Ollama(base_url=ollama_server_url,model=ollama_model)


