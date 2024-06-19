/* 
*
*  Copyright 2024 IBM Corp.
*
*  Licensed under the Apache License, Version 2.0 (the "License");
*  you may not use this file except in compliance with the License.
*  You may obtain a copy of the License at
*
*      http://www.apache.org/licenses/LICENSE-2.0
*
*  Unless required by applicable law or agreed to in writing, software
*  distributed under the License is distributed on an "AS IS" BASIS,
*  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*  See the License for the specific language governing permissions and
*  limitations under the License. 
* 
*/

interface APIMessage {
  input: string,
  output: string,
  type: string
}

export async function sendMessage(
  message: string,
  useDecisionEngine: boolean,
): Promise<APIMessage> {
  const endpoint = useDecisionEngine ? 'chat_with_tools' : 'chat_without_tools';
  const searchParams = new URLSearchParams({ userMessage: message });
  const baseUrl = import.meta.env.VITE_API_URL;
  const url = `${baseUrl}/rule-agent/${endpoint}?${searchParams.toString()}`;

  const response = await fetch(url, {
    mode: 'cors',
    headers: {
      'Access-Control-Allow-Origin': '*',
    },
  });

  const data = (await response.json()) as APIMessage;

  return data;
}

export default {
  sendMessage,
};
