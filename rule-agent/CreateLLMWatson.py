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
from genai.extensions.langchain import LangChainChatInterface
from genai.schema import TextGenerationParameters, TextGenerationReturnOptions
from genai import Client, Credentials

def createLLMWatson():
    if not 'WATSONX_APIKEY' in os.environ:
        print('Please set env variable WATSONX_APIKEY to your IBM Generative AI key')
        exit()
    if not 'WATSONX_URL' in os.environ:
        print('Please set env variable WATSONX_URL to your IBM Generative AI  endpoint URL')
        exit()
    watson_model=os.getenv("WATSONX_MODEL_NAME","mistralai/mistral-7b-instruct-v0-2")
    api_key = os.getenv("WATSONX_APIKEY")
    api_url = os.getenv("WATSONX_URL")

    creds = Credentials(api_key, api_endpoint=api_url)
    params = TextGenerationParameters(decoding_method="greedy", max_new_tokens=400)
    client = Client(credentials=creds)

    llm = LangChainChatInterface(client=client,
            model_id=watson_model, parameters=params)
    return llm
