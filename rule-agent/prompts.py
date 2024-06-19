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
The value associated with the 'arguments' key should be a dictionary of parameters."""

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
    
NLG_SYSTEM_PROMPT = """
        The user input contains a question for which the response is: {result}. 
        Generate the simplest sentence using this response. Don't provide any explanation.
        For example, if the question is "what is the price of a pair of shoes" and the response is "$89", then generate: "the price of a pair of shoes is $89.".
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
