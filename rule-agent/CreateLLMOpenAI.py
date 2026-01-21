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
from langchain_openai import ChatOpenAI
import os

def createLLMOpenAI():
    """
    Create and configure an OpenAI LLM instance

    Environment variables:
    - OPENAI_API_KEY: Your OpenAI API key (required)
    - OPENAI_MODEL_NAME: Model to use (default: gpt-4)
    - OPENAI_TEMPERATURE: Temperature for responses (default: 0.7)
    - OPENAI_MAX_TOKENS: Maximum tokens in response (default: None)
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI integration")

    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
    max_tokens = os.getenv("OPENAI_MAX_TOKENS")

    print(f"Creating OpenAI LLM with model: {model_name}, temperature: {temperature}")

    llm_config = {
        "model_name": model_name,
        "openai_api_key": api_key,
        "temperature": temperature,
        "seed": 42  # Fixed seed for reproducibility (OpenAI supports this)
    }

    if max_tokens:
        llm_config["max_tokens"] = int(max_tokens)

    llm = ChatOpenAI(**llm_config)

    print(f"OpenAI LLM initialized successfully")
    return llm