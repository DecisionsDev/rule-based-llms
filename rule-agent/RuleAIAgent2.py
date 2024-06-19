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
from langchain_core.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages.ai import AIMessage
from DecisionServiceTools import initializeTools
import prompts
from langchain.memory import ConversationBufferWindowMemory
from langchain.globals import set_verbose
from langchain.globals import set_debug
from RuleService import RuleService

# This code does not work with generic tools:
# File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/langchain_core/tools.py", line 413, in run
#    else context.run(self._run, *tool_args, **tool_kwargs)
#         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# TypeError: GenericDecisionServiceTool._run() takes 1 positional argument but 2 were given

class RuleAIAgent2:

    def __init__(self, llm, ruleServices):
        self.llm=llm
        tools = initializeTools(ruleServices=ruleServices)
        memory = ConversationBufferWindowMemory(
        memory_key="chat_history", k=5, return_messages=True, output_key="output"
        )
        template = "\n\n".join(
            [
                prompts.PREFIX,
                "{tools}",
                prompts.FORMAT_INSTRUCTIONS,
                prompts.SUFFIX,
            ]
        )
        prompt = PromptTemplate.from_template(template)
    #     langchain.debug=True
        agent = create_structured_chat_agent(self.llm, tools,prompt=prompt)

        self.pm_agent = AgentExecutor(agent=agent, 
                                tools=tools, 
                                 verbose=True, 
                                handle_parsing_errors=True,
                                early_stopping_method="generate",
                                memory=memory)
    
    def processMessage(self, userInput: str) -> str:
        response = self.pm_agent.invoke({'input': userInput})

        textResponse = ""    

        if (isinstance(response, AIMessage)):
            textResponse = response.content
        else:
            textResponse = response    

        translation_table = str.maketrans({'"': r'\"','\n': r' ', '\t': r' ', '\r': r' ' })
        return '{ "input": "' + userInput.translate(translation_table) + '", "output": "' + textResponse.translate(translation_table) + '"}'


