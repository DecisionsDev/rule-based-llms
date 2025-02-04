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


TEST_PROMPT = """
J'ai besoin de connaître la liste des actions à prendre pour des personnes.
Tu es un assistant expert en analyse et reformulation d'actions pour les conseillers bancaires.
Voici le format json à analyser : 
```json
{{
	"result": {{
		"personne":
			{{
				"id": string, \\\\ L'identifiant de la personne 
				"roleRb": string, \\\\ Le rôle de la personne ("EPOUX", ou "EPOUSE", ou "ENFANT", etc ... )
				"prenom": string, \\\\ Le prénom de la personne
				"nom": string \\\\ Le nom de la personne
			}},
		"actions": [
			{{
				"message": string, \\\\ Le libellé de l'action
				"personne": string, \\\\ L'identifiant de la personne de l'action
				"detail": string \\\\ Le détail supplémentaire optionel de l'action
			}}
        ]
    }}
}}
```
Regrouper les actions d'une même personne depuis {result} puis les énumérer en français.
"""
       
TEST_PROMPT_2 = """
Enumérer en français les actions de {result} que je dois prendre, en combinant en une phrase le libellé de l'action avec le nom de la personne éventuellement associée à l'action.

Je suis un conseiller bancaire et j'ai besoin de connaître la liste des actions à prendre pour des personnes.
Tu es un assistant expert en analyse et reformulation d'actions pour les conseillers bancaires.
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
				"personne": string, \\\\ L'identifiant optionel de la personne de l'action
				"produit": {{ \\\\ Le produit optionnel de l'action
					"type": string, \\\\ Le type du produit
					"id": string, \\\\ L'identifiant du produit
					"libelle": string, \\\\ Le libellé du produit
					"solde": number \\\\ Le solde du produit
				}},
				"detail": string \\\\ Le détail supplémentaire optionel de l'action
			}}
        ]
    }}
}}
```
Reformuler en français les actions de {result} comme s'il s'agissait d'un courrier.
"""
       
with open('result.json') as json_data:
    result = json.load(json_data)

input = ""

nlg_prompt = ChatPromptTemplate.from_messages(
     [("system", TEST_PROMPT)]
    )

nlgChain = nlg_prompt | llm
print(nlgChain.invoke({'input': input, 'result': result}))
