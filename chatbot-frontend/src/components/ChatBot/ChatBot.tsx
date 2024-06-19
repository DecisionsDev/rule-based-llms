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
import { InlineLoading } from '@carbon/react';
import { v4 as uuidv4 } from 'uuid';
import Header from './Header';
import Footer from './Footer';
import Message, { ChatMessage } from './Message';

import styles from './ChatBot.module.scss';
import { sendMessage } from '../../api/rule-agent';

interface ChatBotProps {
  useDE: boolean
}

export default function ChatBot({ useDE }: ChatBotProps) {
  const botName = 'Bot';
  const backendName = useDE ? 'Using Decision Services' : 'Using RAG';
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: uuidv4(),
    name: botName,
    message: "Hi, I'm an AI to answer your questions. I can leverage your corporate decision services to generate answers compliant to your business policies",
    direction: 'received',
  }]);
  const [isProcessingAnswer, setProcessingAnswer] = useState(false);

  function addMessage(newMessage: ChatMessage) {
    setMessages((prev) => prev.concat(newMessage));
    setTimeout(() => {
      document.getElementById('bottom')?.scrollIntoView({ block: 'end', behavior: 'smooth' });
    }, 0);
  }

  async function handleSubmit(newMessage: string) {
    const currentDate = new Date();
    const timestamp = currentDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (newMessage === '') return;
    addMessage({
      id: uuidv4(),
      name: `You ${timestamp}`,
      message: newMessage,
      direction: 'sent',
    });
    const messageName = `${botName} (${backendName}) ${timestamp}`;
    try {
      setProcessingAnswer(true);
      const messageResponse = await sendMessage(newMessage, useDE);
      addMessage({
        id: uuidv4(),
        name: messageName,
        message: messageResponse.output,
        type: (messageResponse.type == 'error')?'error':'text',
        direction: 'received',
      });
    } catch (e) {
      addMessage({
        id: uuidv4(),
        name: messageName,
        message: 'Failed to get chat response',
        direction: 'received',
        type: 'error',
      });
    } finally {
      setProcessingAnswer(false);
    }
  }

  return (
    <div className={styles.chatbot}>
      <Header />
      <div className={styles.messages}>
        {messages.map((message) => <Message key={message.id} {...message} />)}
        <div id="bottom" style={{ marginTop: '2em' }} />
      </div>
      <div style={{ padding: '0 1em' }}>
        {isProcessingAnswer
                && <InlineLoading status="active" iconDescription="Loading" description={isProcessingAnswer ? `${botName} is thinking...` : ''} />}
      </div>
      <Footer onSubmit={handleSubmit} disableSubmit={isProcessingAnswer} />
    </div>
  );
}
