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
from langchain_core.exceptions import OutputParserException
from langchain.agents import AgentOutputParser
from typing import Union
from langchain.schema import  AgentAction, AgentFinish
import re
import json
from langchain.output_parsers.json import parse_json_markdown
from prompts import FORMAT_INSTRUCTIONS

class CustomParser(AgentOutputParser):

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> AgentAction | AgentFinish:
        try:
            #indexObservation = text.index('Observation:');
            #if indexObservation > 0:
            # text = text[0:indexObservation];
            # this will work IF the text is a valid JSON with action and action_input
            response = parse_json_markdown(text)
            action, action_input = response["action"], ""
            if 'action_input' in response:
              action_input = response["action_input"]


            if action == "Final Answer":
                #if action input is a dictionaty
                if isinstance(action_input, dict) :
                  if 'answer' in action_input:
                     action_input = action_input['answer'];
                  if 'response' in action_input:
                     action_input = action_input['response'];
                  else:
                    action_input = str(action_input);

                # this means the agent is finished so we call AgentFinish
                return AgentFinish({"output": action_input}, text)
            else:
                # otherwise the agent wants to use an action, so we call AgentAction
                return AgentAction(action, action_input, text)
        except Exception as e:
            print(e)
            # sometimes the agent will return a string that is not a valid JSON
            # often this happens when the agent is finished
            # so we just return the text as the output
            return AgentFinish({"output": text}, text)

    @property
    def _type(self) -> str:
        return "conversational_chat"