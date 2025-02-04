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
from langchain.agents.structured_chat.prompt import FORMAT_INSTRUCTIONS

PREFIX = """<s><<SYS>>Assistant is a expert JSON builder designed to assist with a wide range of tasks.
 To answer the question of the user, the assistant can use tools. Tools available to Assistant are:
:<</SYS>>"""
FORMAT_INSTRUCTIONS = """RESPONSE FORMAT INSTRUCTIONS
----------------------------
When responding to me, please output a response in one of two formats:
**Option 1:**
Use this if you want the human to use a tool.
Markdown code snippet formatted in the following schema:
```json
{{{{
    "action": string, \\\\ The action to take. Must be one of {tool_names}
    "action_input": string \\\\ The input to the action
}}}}
```
**Option #2:**
Use this if you want to respond directly to the human. Markdown code snippet formatted in the following schema:
```json
{{{{
    "action": "Final Answer",
    "action_input": string \\\\ You should put what you want to return to use here in a human readable text.
}}}}
```"""

SUFFIX = """Begin! Remember, all actions must be formatted as markdown JSON strings.
  Question: {input}
  Thought:{agent_scratchpad}"""

PREFIX_WITH_TOOLS = f"""You are an assistant that has access to the following set of tools.
Here are the names and descriptions for each tool:"""

SUFFIX_WITH_TOOLS = """Given the user input, return the name and input of the tool to use.
The tool you return needs to be one from the list. 
Return your response as a JSON blob with 'name' and 'arguments' keys.
The value associated with the 'arguments' key should be a dictionary of parameters.
Please format dates as 'yyyy-mm-dd'.
Return the JSON blob only. Don't provide explanation. 
"""

    #    nlg_prompt_template = """
    #    You are an assistant that has access to external tools.
    #    A trusted external tool provided {result} as the correct answer to the user's input. 
    #    Simply generate a response using this correct answer.

    #   For example, if the input is: 'what is the price of a pair of shoe?', if the answer provided by the tool is 150, then your response
    #    should be: 'the price of a pair of shoe is 150'. Generate just one sentence using the correct answer provided by the tool.
    #    """

    # This prompt works more or less:
    # nlg_prompt_template = """
    #    You are an assistant that has access to external tools.
    #    A trusted external tool provided {result} as the correct answer to the user's question.
    #    Assume it's the correct answer, don't challenge it. Generate a simple response using it. 
    #    Generate one sentence only. 
    #   """

    # This prompt works quite well too:
    # nlg_prompt_template = """
    #    The user input contains a question for which the response is: {result}. 
    #    Generate the simplest sentence using this response. Don't provide any explanation.
    #    For example, if the question is "what is the price of a pair of shoes" and the response is "$89", then generate: "the price of a pair of shoes is $89.".
    #  """


    # nlg_prompt_template = """
    #    You are an Assistant with access to external tools that can be used to get reliable answers to user's questions.
    #    A trusted external tool provided {result} as the correct answer to this user's question.  
    #    This is the true answer, don't challenge it, don't try to invent another one and use it to respond with 1 sentence.
    #   """
    
# NLG_SYSTEM_PROMPT = """
#        The user input contains a question for which the response is: {result}. 
#        Generate the simplest sentence using this response. Don't provide any explanation.
#       For example, if the question is "what is the price of a pair of shoes" and the response is "$89", then generate: "the price of a pair of shoes is $89.".
#       """

NLG_SYSTEM_PROMPT = """
Tu es linguiste en français, spécialisé en reformulation concise et précise respectant la grammaire et la conjugaison française.

Markdown code snippet formatted in the following schema: 
```json
{{
	"resultat": {{
		"personnes": [
			{{
				"id" : l'identifiant de la personne 
				"roleRb" : la place de la personne dans le foyer : "EPOUX", ou "EPOUSE", ou "ENFANT", etc ... 
				"prenom" : le prénom de la personne
				"nom" : le nom de la personne
				"civilite" : la civilité de la personne : "MONSIEUR", ou "MADAME", ou "MADEMOISELLE"
			}}
		],
		"actions": [
			{{
				"message" : le libellé de l'action
				"personne" : l'identifiant optionnel de la personne de l'action
				"produit": {{
					"type" : le type du produit de l'action
					"id" : l'identifiant du produit de l'action
					"libelle" : le libellé du produit de l'action
					"solde" : le solde du produit de l'action
				}},
				"detail" : le détail supplémentaire optionnel de l'action,
				"theme" : le thème de l'action,
				"justification" : la justification de l'action
			}}
		]
	}}
}}

Les personnes sont précisées par leur prénom et leur nom, sauf si le prénom n'est pas fourni, auquel cas seul le nom est utilisé. Si le nom est absent utiliser le terme foyer.
Regrouper les actions par thème.

Reformuler les actions de {result} de même justification en une phrase, en incluant toutes les données de ces actions : les messages, les personnes, les libellés des produits, et les détails.
Pour les produits arrivés à terme, préciser leur solde.

Mise en forme :
- commencer les actions par des tirets.
- les thèmes sont en gras, et séparés par des sauts de ligne.

S'arrêter au dernier thème, sans fournir de texte supplémentaire.

Voici un 1er exemple : 

    Entrée : {{
        "resultat": {{
            "personnes": [
                {{
                    "id": "pers01",
                    "roleRb": "EPOUX",
                    "prenom": "Toto",
                    "nom": "Dupuis",
                    "civilite": "MONSIEUR"
                }}
            ],
            "actions": [
                {{
                    "message": "Recommander LivretA_LDD",
                    "personne": "pers01",
                    "produit": null,
                    "detail": "",
                    "theme" : "Se constituer un capital",
                    "justification" : "Rémunérer l'épargne disponible"
                }}
            ]
        }}
    }}
    
    Sortie : 
    Se constituer un capital : 
    - recommander à Mr Dupuis l'ouverture d'un Livret A et d'un LDD, pour rémunérer son épargne disponible.
    
Voici un 2ème exemple : 

    Entrée : {{
        "resultat": {{
            "personnes": [
                {{
                    "id": "pers03",
                    "roleRb": "ENFANT",
                    "prenom": "Riri",
                    "nom": "Dupuis",
                    "civilite": "MONSIEUR"
                }},
                {{
                    "id": "pers04",
                    "roleRb": "ENFANT",
                    "prenom": "Fifi",
                    "nom": "Dupuis",
                    "civilite": "MADEMOISELLE"
                }}
            ],
            "actions": [
                {{
                    "message": "Recommander Epargne Enfant",
                    "personne": "pers04",
                    "produit": null,
                    "detail": "livret d'épargne liquide",
                    "theme" : "Se constituer un capital ",
                    "justification" : "Rémunérer l'épargne disponible"
                }},
                {{
                    "message": "Recommander Epargne Enfant",
                    "personne": "pers03",
                    "produit": null,
                    "detail": "livret d'épargne liquide",
                    "theme" : "Se constituer un capital ",
                    "justification" : "Rémunérer l'épargne disponible"
                }}
            ]
        }}
    }}
    
    Sortie : 
    Se constituer un capital : 
    - recommander un livret d'épargne liquide pour les enfants Arthur et Mélanie, afin de rémunérer l'épargne disponible.

Voici un dernier exemple : 
    Entrée : {{
        "resultat": {{
            "personnes": [
                {{
                    "id": "pers01",
                    "roleRb": "EPOUX",
                    "prenom": "Toto",
                    "nom": "Dupuis",
                    "civilite": "MONSIEUR"
                }}
            ],
            "actions": [
                {{
                    "message": "Alerter sur l'arrivée à terme",
                    "personne": "pers01",
                    "produit": {{
                        "type": "epargne",
                        "versementPeriodique": null,
                        "id": "pea01",
                        "libelle": "PEA",
                        "solde": 30000.0,
                        "soldeMaximum": 0.0,
                        "taux": 0.0
                    }},
                    "detail": "",
                    "theme" : "Client / Sa relation avec la banque",
                    "justification" : "Planifier la gestion du produit à son échéance"
                }}
            ]
        }}
    }}
    
    Sortie : Client / Sa relation avec la banque : 
    - alerter Mr Dupuis sur l'arrivée à terme de son PEA, avec un solde de 30000 €, afin de planifier la gestion du produit à son échéance.

Fin des exemples.
       """


INSTRUCTIONS_WITH_CONTEXT = """
            <s> [INST] You are an assistant for question-answering tasks. Use the following pieces of retrieved context 
            to answer the question. If you don't know the answer, just say that you don't know. Use three sentences
             maximum and keep the answer concise and limited to the response to the question. [/INST] </s> 
            [INST] Question: {input} 
            Context: {context} 
            Answer: [/INST]
        """

INSTRUCTIONS = """
            <s> [INST] You are an assistant for question-answering tasks. If you don't know the answer, just say that you don't know. Use three sentences
             maximum and keep the answer concise and limited to the response to the question. [/INST] </s> 
            [INST] Question: {input} 
            Answer: [/INST]
        """
