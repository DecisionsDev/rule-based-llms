import os,sys

import sys
sys.path.append("..")
from langchain.globals import set_debug
import prompts
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
llm = Ollama(base_url="http://localhost:11434",
  #              model="codellama:13b-instruct",
                model="granite3-moe:3b",
                temperature=0)
import json
from pprint import pprint
set_debug(True)

TEST_PROMPT = """Tu es un assistant expert en analyse et reformulation d'actions pour les conseillers bancaires.

Mon contexte est le suivant : je suis un conseiller bancaire qui reçoit une liste d'actions à prendre sous forme de données JSON. 
Chaque action contient un message principal, la personne concernée, et parfois un détail supplémentaire. 
Chaque personne est identifiée par son id. 

Voici le format json à analyser : 
```json
{{
	"result": {{
		"personnes": [
			{{
				"id": string, \\\\ L'identifiant de la personne 
				"roleRb": string, \\\\ La place de la personne dans la famille : "EPOUX", ou "EPOUSE", ou "ENFANT", etc ... 
				"prenom": string, \\\\ Le prénom de la personne
				"nom": string, \\\\ Le nom de la personne
				"civilite": string \\\\ La civilité de la personne : "MONSIEUR", ou "MADAME", ou "MADEMOISELLE"
			}}
		],
		"actions": [
			{{
				"message": string, \\\\ Le libellé de l'action
				"personne": string, \\\\ L'identifiant de la personne concernée par l'action
				"detail": string \\\\ Détail supplémentaire optionel de l'action
			}}
        ]
    }}
}}
```
Reformule chaque action en une phrase claire et concise que le conseiller pourra facilement comprendre et exécuter.
"""
       
with open('result.json') as json_data:
    result = json.load(json_data)

input = ""

nlg_prompt = ChatPromptTemplate.from_messages(
     [("system", TEST_PROMPT)]
    )

nlgChain = nlg_prompt | llm
print(nlgChain.invoke({'input': input, 'result': result}))
