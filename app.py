import streamlit as st
import pandas as pd
import os

import requests
import time

# Set up the OpenAI API key
server_url = os.environ["ngrok_url"]

# App information and setup
project_title = "LLM Sampler"
project_icon = "icon.png"
st.set_page_config(page_title=project_title, initial_sidebar_state='expanded', page_icon=project_icon)

#######################################################################################################################

if "input_value" not in st.session_state:
    st.session_state.input_value = ""
if "input_disabled" not in st.session_state:
    st.session_state.input_disabled = False
# if "reverse_conv" not in st.session_state:
#     st.session_state.reverse_conv = False
if "conversation_display" not in st.session_state:
    st.session_state.conversation_display = False

if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = None
# Initialize the conversation history
if st.session_state.get("conversation_history") is None:
    st.session_state["conversation_history"] = pd.DataFrame(columns=["User Prompts","Bot Responses"])
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

def parse_conversation(conversation_history, count_from_last = 20, display_only = True, reverse=False):
    conversation = ""
    conv_len = len(conversation_history)
    parsing_dict = {"user":"### User: ", "assistant":"### LLM Chatbot: "}
    if conv_len > count_from_last:
        for i in range((conv_len-1) - (count_from_last-1), conv_len):
            conversation += parsing_dict[conversation_history[i]["role"]] + conversation_history[i]["content"] + "\n\n"
    else:
        for message in conversation_history:
            conversation += parsing_dict[message["role"]] + message["content"] + "\n\n"

    return conversation

def generate_response(prompt, conversation_history):
    conversation = parse_conversation(conversation_history, display_only=False)
    context = """### System:\nYou are 'LLM Chatbot', an AI that follows instructions extremely well. 
    Help as much as you can. 
    Use less emotes or emojis, but you can employ other methods to appear 'friendly'.
    Do not include the previous messages in your reply.
    Do not include the '###' tags.
    Remember, be safe, and don't do anything illegal.\n\n"""
    
    # new_prompt = f"{context}{conversation}### User: {prompt}\n\n### LLM Chatbot: "
    new_prompt = f"{context}{conversation}### LLM Chatbot: "
    print(f"Prompt sent to ChatGPT: \n{new_prompt}")

    try:
        # Generate the response
        response = requests.post(f'{server_url}/chat', data={'prompt': new_prompt})
    except Exception as e:
        st.error(f"An error has occurred in the request: {e}")
    
    if response.status_code == 200:
        # Add user assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response.json()['response']})
        print(f"LLM's returned response: {response.json()['response']}")
        return response.json()['response']
    else:
        st.error(f"Request failed: {response.json()['response']}")     

def get_models():
    response = requests.get(f'{server_url}/get-models')
    dict = response.json()
    st.session_state.model_loaded = dict['loaded_model'].split('_')[1] if dict['loaded_model'] is not None else dict['loaded_model']
    return dict['model_list']
    
def main():
    try:
        response = requests.get(f'{server_url}/ping')
        if response.text == "pong":
            st.success("• Connected to the server.")
        else:
            st.warning(f"• Server is running but returned unexpected response.")
    except requests.exceptions.ConnectionError:
        st.error("• Could not connect to the server.")

    # Reset chat
    reset_chat = st.button("Reset Chat")
    if reset_chat:
        st.session_state.messages = []
        st.success("Chat has been reset.")        
    st.markdown("***")
#########################################
    with st.sidebar:
        # model list dropdown
        model_name = st.selectbox("Model", get_models(), 2)
        load_model_button = st.button("Load Model")

        if load_model_button:
            try:
                response = requests.post(f'{server_url}/load-model', data={'model_name': model_name})
                dict = response.json()
                if dict['status'] == "success":
                    st.success(dict['message'])
                    st.session_state.model_loaded = dict['message'].split(':')[1].split('_')[1]
                elif dict['status'] == "error":
                    st.warning(dict['message'])
            except requests.exceptions.ConnectionError:
                st.error("• Could not connect to the server.")
        st.write(f"Model loaded:\n{st.session_state.model_loaded}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input(placeholder=st.session_state.input_value, key="user_message", disabled=st.session_state.input_disabled):
        if st.session_state.model_loaded is not None:
            st.session_state.input_value = "Generating response, please wait 😊"
            st.session_state.input_disabled = True
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            assistant_response = generate_response(prompt, st.session_state.messages)

            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                # Simulate stream of response with milliseconds delay
                for chunk in assistant_response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    # Add a blinking cursor to simulate typing
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            # Reset values
            st.session_state.input_value = ""
            st.session_state.input_disabled = False
            st.experimental_rerun()
        else:
            st.warning("Please load a model first.")

# Run the chatbot
if __name__ == "__main__":
    main()