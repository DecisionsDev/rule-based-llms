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
import cx from 'classnames';
import { MachineLearning } from '@carbon/icons-react';
import styles from './ChatBot.module.scss';

export interface ChatMessage {
  id: string,
  name: string,
  message: string,
  direction: 'sent' | 'received',
  type?: 'text' | 'error'
}

type MessageProps = Omit<ChatMessage, 'id'>;

export default function Message({
  name, message, direction, type = 'text',
}: MessageProps) {
  return (
    <div>
      <div className={styles.messageContainer} style={{ alignItems: direction === 'sent' ? 'end' : 'start' }}>
        <div className={styles.nameWrapper}>
          {direction === 'received' && <MachineLearning className={styles.icon} /> }
          <div className={styles.username}>{name}</div>
        </div>
        {type === 'text' && <div className={cx(styles.message, { [styles.sent]: direction === 'sent' })}>{message}</div>}
        {type === 'error' && <div className={styles.errorMessage}>{message}</div>}
      </div>
    </div>
  );
}
