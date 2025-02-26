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
from langchain_ibm import ChatWatsonx
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames
            

def createLLMWatson():
    if not 'WATSONX_APIKEY' in os.environ:
        print('Please set env variable WATSONX_APIKEY to your IBM watsonx.ai service API Key')
        exit()
    if not 'WATSONX_URL' in os.environ:
        print('Please set env variable WATSONX_URL to your IBM Generative AI  endpoint URL')
        exit()
    if not 'WATSONX_PROJECT_ID' in os.environ:
        print('Please set env variable WATSONX_PROJECT_ID to your IBM watsonx.ai Project ID')
        exit()
    watsonx_model=os.getenv("WATSONX_MODEL_NAME","mistralai/mistral-7b-instruct-v0-2")
    api_key = os.getenv("WATSONX_APIKEY")
    api_url = os.getenv("WATSONX_URL")
    project_id = os.getenv("WATSONX_PROJECT_ID")

    parameters = {
        GenTextParamsMetaNames.DECODING_METHOD: "greedy",
        GenTextParamsMetaNames.MIN_NEW_TOKENS: 0,
        GenTextParamsMetaNames.MAX_NEW_TOKENS: 600,
        GenTextParamsMetaNames.REPETITION_PENALTY : 1
    }

    llm = ChatWatsonx(
        model_id=watsonx_model,
        url=api_url,
        api_key=api_key,
        project_id=project_id,
        params=parameters)
    return llm
