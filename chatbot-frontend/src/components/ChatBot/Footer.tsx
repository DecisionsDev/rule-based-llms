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
import { Send } from '@carbon/icons-react';
import { Button } from '@carbon/react';
import { KeyboardEvent, useState } from 'react';
import cx from 'classnames';
import styles from './ChatBot.module.scss';

interface FooterProps {
  onSubmit: (msg: string) => void
  disableSubmit: boolean
}

export default function Footer({ onSubmit, disableSubmit }: FooterProps) {
  const [message, setMessage] = useState<string>('');
  const [textAreaHasFocus, setTextAreaHasFocus] = useState(false);
  const [textFocusref, setTextFocusRef] = useState<HTMLTextAreaElement | null>();

  function onSend() {
    onSubmit(message);
    setMessage('');
    if (textFocusref) textFocusref.focus();
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault();
      onSend();
    }
  }

  return (
    <div className={styles.footer}>
      <div className={cx(
        styles.inputcontainer,
        { [styles.inputcontainerHasFocus]: textAreaHasFocus },
      )}
      >
        <textarea
          className={styles.chatinput}
          onChange={(e) => setMessage(e.target.value)}
          rows={1}
          placeholder="Type something..."
          onFocus={() => setTextAreaHasFocus(true)}
          onBlur={() => setTextAreaHasFocus(false)}
          value={message}
          ref={setTextFocusRef}
          readOnly={disableSubmit}
          onKeyDown={(e) => onKeyDown(e)}
        />
        <Button
          kind="ghost"
          size="sm"
          hasIconOnly
          iconDescription="Submit"
          onClick={() => onSend()}
          disabled={disableSubmit}
          renderIcon={Send}
        />
      </div>
    </div>
  );
}
