import gradio as gr
import requests
import asyncio
import os

def chatbot_response(input_text):
    return "Hello! This is a Carbon-themed chatbot."

# CSS with more white in the gradient
carbon_css = """
@import url('https://unpkg.com/carbon-components/css/carbon-components.min.css');
.header {
    border-bottom: 1px solid $border-subtle-00;
    display: flex;
    padding: .5em;
}

.gradio-container {
    font-family: 'IBM Plex Sans', sans-serif;
    background: linear-gradient(135deg, #ffffff 60%, #d0e2ff 100%);
    color: #161616;
    height: 100vh;
    padding: 20px;
}

.chatbox {
    border: 1px solid #8d8d8d;
    border-radius: 12px;
    padding: 20px;
    background-color: white;
    color: #161616;
    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1);
}

.chat-header {
    font-size: 1.5rem;
    font-weight: bold;
    color: #161616;
    padding-bottom: 10px;
    border-bottom: 2px solid #e0e0e0;
}

textarea {
    border: 1px solid #8d8d8d;
    border-radius: 8px;
    padding: 6px;
    font-size: 1rem;
    color: #161616;
}

.toggle-button {
    background-color: #0f62fe;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
}

.toggle-button:hover {
    background-color: #0043ce;
}
"""

async def send_message(message: str, use_decision_engine: bool) -> dict:
    endpoint = 'chat_with_tools' if use_decision_engine else 'chat_without_tools'
    base_url = 'http://localhost:9000'  # Replace with your actual API URL
    url = f"{base_url}/rule-agent/{endpoint}?userMessage={message}"

    response = requests.get(url, headers={'Access-Control-Allow-Origin': '*'})

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Failed to fetch data"}

def chatbot_response(input_text: str, use_decision_engine: bool):
    # Call the async function and wait for the result
    result = asyncio.run(send_message(input_text, use_decision_engine))
    return result

# Fonction de chatbot simple
def chatbot(message, use_decision_service):
    # Logique du chatbot ici
    # if use_decision_service:
    #     response = f"Decision Service activé : {message}"
    # else:
    #     response = f"Vous avez dit : {message}"
    
    return chatbot_response(message,use_decision_service)['output']


# Créer l'interface Gradio
with gr.Blocks(css=carbon_css) as demo:
    gr.HTML("""<h1 class="header">IBM LLM + Decisions Chatbot</h1>""")
    chatbot_interface = gr.Chatbot(show_copy_button=True,   
                            avatar_images=(None, (os.path.join(os.path.dirname(__file__), "bot.png"))))  
    message = gr.Textbox(show_label=False,label=None,placeholder="Type you message here ...",submit_btn=True)
    use_decision_service = gr.Checkbox(label="Decision Service", container=False)

   
    def respond(message, use_decision_service, chat_history):
        bot_message = chatbot(message, use_decision_service)
        chat_history.append((message, bot_message))
        return "", chat_history

    message.submit(respond, [message, use_decision_service, chatbot_interface], [message, chatbot_interface])

# Lancer l'application
demo.launch(allowed_paths=[], server_name="0.0.0.0",show_api=False,favicon_path=(os.path.join(os.path.dirname(__file__), "bot.png")))