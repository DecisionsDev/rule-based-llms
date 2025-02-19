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

NLG_SYSTEM_PROMPT1 = """
Remet le contexte à 0.

Concevoir une phrase par action, en respectant les consignes suivantes :
- Ignorer les actions sans thème.
- Attribuer au foyer les actions sans personne.
- Pour les enfants, utiliser uniquement le prénom.
- Pour les époux, utiliser la civilité et le nom.
- Remplacer MONSIEUR par Mr.
- Remplacer MADAME par Mme.
- Préciser le solde des produits arrivés à terme, en euro.
- Séparer la partie décimale de la partie entière par une virgule.

Commencer avec le thème "Gérer le quotidien".
Le thème suivant est "Données à recueillir/enrichir".
Le thème suivant est "Se constituer un capital".
Le thème suivant est "Client / Sa relation avec la banque".
Le thème suivant est "Protéger ses biens et sa famille"
Le thème suivant est "Financer ses projets".
Terminer avec le dernier thème "Points d'attention".

*exemple* :
    Entrée : {{'personnes': [{{'id': 'Id01', 'roleRb': 'EPOUX', 'prenom': 'Marcel', 'nom': 'Dupuis', 'civilite': 'MONSIEUR'}}, {{'id': 'Id02', 'roleRb': 'EPOUSE', 'prenom': 'Géraldine', 'nom': 'Dupuis', 'civilite': 'MADAME'}}, {{'id': 'Id03', 'roleRb': 'ENFANT', 'prenom': 'Tutu', 'nom': 'Dupuis', 'civilite': 'MONSIEUR'}}, {{'id': 'Id04', 'roleRb': 'ENFANT', 'prenom': 'Tata', 'nom': 'Dupuis', 'civilite': 'MADEMOISELLE'}}], 'actions': [{{'message': 'Recommander xxx', 'personne': 'Id01', 'produit': None, 'detail': 'DDD', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}}, {{'message': 'Recommander xxx', 'personne': 'Id02', 'produit': None, 'detail': 'DDD', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}},{{'message': 'Recommander xxx', 'personne': 'Id03', 'produit': None, 'detail': 'DDD', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}},{{'message': 'Recommander xxx', 'personne': 'Id04', 'produit': None, 'detail': 'DDD', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}}, {{'message': 'Compléter xxx', 'personne': 'Id01', 'produit': None, 'detail': '', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}}, {{'message': 'Compléter xxx', 'personne': 'Id02', 'produit': None, 'detail': '', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}},{{'message': 'Recommander yyy', 'personne': 'Id01', 'produit': None, 'detail': 'DDD', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}}, {{'message': 'Recommander yyy', 'personne': 'Id01', 'produit': None, 'detail': 'UUU', 'theme': 'Thème 1', 'justification': 'Améliorer un aspect'}}, {{'message': 'Proposer zzz', 'personne': 'Id02', 'produit': None, 'detail': '', 'theme': 'Thème 2', 'justification': 'Améliorer un aspect'}}]}}
    Sortie :
      **Thème 1**
             - Recommander xxx (DDD) à Mr et Mme Dupuis, ainsi qu'à Tutu et Tata, afin d'améliorer un aspect.
             - Compléter xxx de Mr et Mme Dupuis, afin d'améliorer un aspect.
             - Recommander yyy (DDD, UUU) à Mr Dupuis, afin d'améliorer un aspect.
      **Thème 2**
             - Proposer zzz à Mme Dupuis, afin d'améliorer un aspect.
*Fin d'exemple*

Entrée : {result}
Sortie :
"""

NLG_SYSTEM_PROMPT1_SANSEX = """
Process the input and generate the appropriate output based on the following instructions.
Your task is to transform a set of actions into a structured format with specific rules.

There are multiple actions, each with a message, person, product, detail, theme, and justification.
The specific rules are :
1. Ignore actions without a theme.
2. Assign actions without a person to the "foyer" (household).
3. For children, use only their first names.
4. For spouses, use their civility (Mr. or Mme.) and last name.
5. Replace "MONSIEUR" with "Mr." and "MADAME" with "Mme."
6. For products that have reached their term, specify the balance in euros, using a comma as the decimal separator.

Your approach will be:
1. Group actions by their themes.
2. For each action, determine the person or if it's for the household.
3. Apply the naming conventions based on the person's role.
4. For actions involving products at term, include the solde (balance) in euros.
5. Combine actions with different persons but the same message and no detail into a single sentence, using the message, the products, and the justification.
6. Combine actions with no person or different persons but the same message and the same detail or no detail into a single sentence, using the message, the products, and the justification.
7. Combine actions with different details but the same message and the same person into a single sentence, using the message, the products, and the justification.
8. Combine actions with different details but the same message and no person into a single sentence, using the message, the products, and the justification.

Starting with the first theme, "Gérer le quotidien".
Next theme is "Données à recueillir/enrichir".
Next theme is "Se constituer un capital".
Next theme is "Client / Sa relation avec la banque".
Next theme is "Protéger ses biens et sa famille"
Next theme is "Financer ses projets".
Finally, last theme is "Points d'attention".

Then structure each theme, combining actions where possible and applying the naming rules. 
Ensure that for products with a solde, I format the amount correctly, like 20 000,00 €.

Putting it all together, Make sure each theme is a section in bold, and each action is a bullet point under it, properly formatted.
End the output after the last sentence.

Input : {result}
Output :
"""

NLG_SYSTEM_PROMPT2 = """
Remet le contexte à 0.
Traduire "{result}" dans la langue de "{input}".
Entrée :
Sortie :
"""
       
NLG_SYSTEM_PROMPT3 = """
Remet le contexte à 0.

Formate {result} en HTML en suivant le modèle suivant, en créant une section par thème :
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd"> <html> 
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.7.2/Chart.min.js"></script>
<style type="text/css">

html {{
	background-color: #D3D3D3;
	display: flex;
	justify-content: center;
}}


body {{
	font-family: 'Roboto', sans-serif;
	font-size: small;
	background-color: white;
	width: 1024px;
	-webkit-print-color-adjust: exact;
}}

#Carre {{
	list-style-image: url('./images/checkBox.jpg');
}}

#Rond {{
	list-style-type: circle;
}}

#Triangle {{
	list-style-image: url('./images/puce_triangle.gif');
}}

table.TableauPrelevementsMensuels {{
	border: 1px;
	width: calc(100% - 30px);
	margin-left: 30px;
	font-size: 12px;
	padding: 0 0.5em;
	border-collapse: collapse;
	line-height: 20px;
}}

table.TableauPrelevementsMensuels th {{
	text-align: left;
}}

table.TableauPrelevementsMensuels th:nth-child(2) {{
	text-align: right;
}}

table.TableauPrelevementsMensuels td {{
	padding: 0 0.5em;
	text-align: left;
	font-weight: 300;
}}

table.TableauPrelevementsMensuels td p {{
	position: relative;
}}

table.TableauPrelevementsMensuels td:nth-child(1) {{
	content: '';
	height: 1px;
	width: 300px;
	<!-- background-color: LightGrey; -->
	top: 10px;
	<!-- right: -61px; -->
}}

table.TableauPrelevementsMensuels td:nth-child(2) {{
	width: 100px;
	text-align: right;
	font-weight: bold;
	color: #294c96;
}}
table.TableauMouvementsImportants {{
	border: 1px;
	width: calc(100% - 30px); margin-left : 30px;
	font-size: 12px;
	padding: 0 0.5em;
	border-collapse: collapse;
	line-height: 20px;
	margin-left: 30px;
}}

table.TableauMouvementsImportants th {{
	text-align: left;
}}

table.TableauMouvementsImportants th:nth-child(1n+2) {{
	text-align: center;
	width: 70px;
}}

table.TableauMouvementsImportants td {{
	padding: 0 0.5em;
	text-align: left;
}}

table.TableauMouvementsImportants td p {{
	position: relative;
}}

table.TableauMouvementsImportants td:nth-child(3) {{
	text-align: right;
	font-weight: bold;
	color: #294c96;
}}

table.TableauMouvementsImportants td:nth-child(1) p::after {{
	content: '';
	position: absolute;
	height: 1px;
	width: calc(100% + 70px);
	background-color: LightGrey;
	top: 10px;
	right: -131px;
}}

table.graphes td {{
	width: 50%;
	font-size: 12px;
	border-style: hidden;
	background: white;
}}

li {{
	margin: 0;
	padding: 0.2em;
}}

.header-bg {{
	width: 100%;
	color: white;
	position: relative;
	height: 207px;
}}

.header-bg img {{
	position: absolute;
	top: 0;
	left: 0;
	z-index: 0;
}}

.header-bg>div {{
	position: absolute;
	top: 0;
	left: 0;
	z-index: 1;
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	width: 100%;
	padding-right: 10px;
	box-sizing: border-box;
	padding-top: 30px;
}}

.personne td>strong {{
	background-color: #9cb0d7;
	border-bottom: 3px solid white;
	display: inline-block;
	color: white;
	text-align: center;
	padding: 10px;
	box-sizing: border-box;
	width: 100%;
	font-size: 18px;
}}

.personne li {{
	list-style-type: none;
}}

.personne .right ul {{
	padding-right: 40px;
}}

.title {{
	background-color: #305c9f;
	color: white;
	padding-left: 70px;
	position: relative;
	padding-top: 15px;
	padding-bottom: 15px;
	font-size: 18px;
}}

.title::before {{
	content: '';
	position: absolute;
	height: 8px;
	width: 90px;
	background-color: #f0f3f8;
	transform: rotate(-45deg);
	top: 20px;
	left: -11px;
}}

.recommandations {{
	background-color: #f0f3f8;
}}

.recommandations ul {{
	padding-top: 3px;
	padding-bottom: 3px;
}}

.commentaire {{
	display: flex;
	flex-direction: row;
	align-items: center;
}}

.comm-img {{
	position: relative;
	display: inline-table;
	width:100%;
}}

.comm-img  > img{{
	width:100%;
}}

.comm-img::before {{
	content: 'Commentaires';
	position: absolute;
	height: 15px;
	width: 90px;
	top: 7px;
	left: 19px;
	font-family: 'Shadows Into Light', cursive;
	font-size: 18px;
}}

.tableau {{
	display: flex;
	flex-direction: column;
	padding-left: 30px;
}}

.tableau center {{
	text-align: left;
}}
</style>
</head>
<title>Préparation d'entretien</title>
<body>
	<div class="header-bg">
		<img width="100%" src='./images/IBM-Background.jpg' />
		<div>
			<div>
				<div style="font-size: 24px;">Document de travail strictement à usage interne</div>
				<div style="font-size: 12px; font-style: italic; text-align: right">Fiche éditée le dateRef</div>
			</div>
			<div style="padding-top: 22px">
				<div style="font-size: 18px;">Préparation de l'entretien de : civilité du client et nom du client</div>
				<div style="font-size: 12px;text-align: right; font-weight: 200; font-style: italic;">(n° de pers : id du client)</div>
				<div style="font-size: 18px;text-align: right;">Agence de rattachement : Orsay</div>
				<div style="font-size: 18px;"></div>
			</div>
		</div>
	</div>
	<!-- Core du document -->
        <!-- Section 0 -->
        <table width="100%" class="personne">
            <tr>
 				<td width="50%" style="background-color: #f0f3f8; text-align: right" class="right"><strong>civilite et nom du client</strong>
                	<ul>
                    <li>Client depuis dateEntreeRelation du client</li>
                    <li>l'âge de l'époux</li>
                    <li>Activité : profession du client</li>
                    <li>Employeur : entrepriseEmployeur du client</li>
                    <li>Segmentation : <strong>segment du client</strong></li>
                    <li>Téléphone privé : numeroTelephonePrive du client</li>
                    <li>Email privé : emailPrive du client</li>
                	</ul>
                </td>
				<td width="50%" style="background-color: #f0f3f8; text-align: left"><strong>civilite et nom de l'épouse</strong>
                	<ul>
                    <li>Cliente depuis dateEntreeRelation de l'épouse</li>
                    <li>l'âge de l'épouse</li>
                    <li>Activité : profession de l'épouse</li>
                    <li>Employeur : entrepriseEmployeur de l'épouse</li>
                    <li>Segmentation : <strong>segment de l'épouse</strong></li>
                    <li>Téléphone privé : numeroTelephonePrive de l'épouse</li>
                    <li>Email privé : emailPrive de l'épouse</li>
                	</ul>
                </td>
            </tr>
            <tr>
                <td>        </td>
                <td>        </td>
            </tr>
        </table>
		<!-- Section -->
		<div class="title">Thème</div>
		&nbsp;
		<table cellspacing="2" width="100%"
			style="background-color: #f0f3f8; border-style: hidden; border-color: white;">
			<tr>
				<td style="border-style: hidden;"><ul><li>Recommendation</li></ul></td>
			</tr>
		</table>
		<div style="display: flex; justify-content: center;">
			<div class="comm-img">
				<img src='./images/Rectangle-big.svg' />
			</div>
		</div>
		&nbsp;&nbsp;
</body>
</html>

Traduit le résultat dans la langue de {input}.
Sortie : 
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
