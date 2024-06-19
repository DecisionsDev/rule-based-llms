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
import { useState } from 'react';

import {
  Header, SkipToContent, HeaderName, Content, Theme, Toggle,
} from '@carbon/react';

import ChatBot from './components/ChatBot/ChatBot';

function App() {
  const [useDE, setUseDE] = useState(false);

  return (
    <>
      <Theme theme="g100">
        <Header aria-label="Chatbot">
          <SkipToContent />
          <HeaderName href="#" prefix="IBM">
            LLM+Decisions Chatbot
          </HeaderName>
        </Header>
      </Theme>
      <Content>
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <div>
            <div style={{ marginBottom: '1em' }}>
              <Toggle
                id="de-toggle"
                labelA="Do not use Decision Services"
                labelB="Use Decision Services"
                labelText="Use this toggle to allow this bot to leverage your corporate decision services."
                size="sm"
                onToggle={(checked) => setUseDE(checked)}
              />
            </div>
            <ChatBot useDE={useDE} />
          </div>
        </div>
      </Content>
    </>
  );
}

export default App;
