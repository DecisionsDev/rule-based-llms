import os,sys

import sys
sys.path.append("..")
from langchain.globals import set_debug
import prompts
from langchain.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
llm = Ollama(base_url="http://localhost:11434",
  #              model="codellama:13b-instruct",
                model="mistral",
                temperature=0)
import json
from pprint import pprint
set_debug(True)
with open('result.json') as json_data:
    result = json.load(json_data)



input = "Détermine les actions à réaliser lors du prochain entretien avec le client pers01 le 18/01/2025."

nlg_prompt = ChatPromptTemplate.from_messages(
     [("system", prompts.NLG_SYSTEM_PROMPT), ("user", "{input}")]
    )

nlgChain = nlg_prompt | llm
#print(">RPA" + str(s['tool_call_result']))
print(nlgChain.invoke({'input': input, 'result': result}))
