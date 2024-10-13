import os
import pandas as pd
from dotenv import dotenv_values
import streamlit as st
from groq import Groq

def parse_groq_stream(stream):
    for chunk in stream:
        if chunk.choices:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

# streamlit page configuration
st.set_page_config(
    page_title="Grapevine",
    page_icon="🍇",
    layout="centered",
)

try:
    secrets = dotenv_values("env.txt")  # for dev env
    GROQ_API_KEY = secrets["GROQ_API_KEY"]
except:
    secrets = st.secrets  # for streamlit deployment
    GROQ_API_KEY = secrets["GROQ_API_KEY"]

# save the api_key to environment variable
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

INITIAL_RESPONSE = secrets["INITIAL_RESPONSE"]
INITIAL_MSG = secrets["INITIAL_MSG"]
CHAT_CONTEXT = secrets["CHAT_CONTEXT"]

client = Groq()

# Load the CSV dataset
csv_file_path = "Combined_Connections.csv"
connections_df = pd.read_csv(csv_file_path)

# initialize the chat history if not present as streamlit session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant",
         "content": INITIAL_RESPONSE
         },
    ]

# page title
st.title("Hi, I am your LinkedIn assistant🍇!")
st.caption("I will analyze your profile and assist you with LinkedIn queries")

# display chat history
for message in st.session_state.chat_history:
    if message["role"] == "assistant":
        with st.chat_message("assistant", avatar='🍇'):
            st.markdown(message["content"])
    else:
        with st.chat_message("user", avatar="🍇"):
            st.markdown(message["content"])

# user input field
user_prompt = st.chat_input("Hello, I am LinkedIn Assistant. Please ask me a question?")

if user_prompt:
    with st.chat_message("user", avatar="🍇"):
        st.markdown(user_prompt)
    st.session_state.chat_history.append(
        {"role": "user", "content": user_prompt})

    # Check if the user prompt is about looking for people with a specific job position
    if "looking for" in user_prompt.lower() and "position" in user_prompt.lower():
        # Extract the job position from the user prompt
        job_position = user_prompt.lower().split("position")[-1].strip()
        filtered_df = connections_df[connections_df['Position'].str.contains(job_position, case=False, na=False)]

        if not filtered_df.empty:
            response_content = "Here are some connections matching the job position '{}':\n".format(job_position)
            for index, row in filtered_df.iterrows():
                response_content += "- {} {} - [{}]({})\n".format(row['First Name'], row['Last Name'], row['Position'], row['URL'])
        else:
            response_content = "Sorry, I couldn't find any connections matching the job position '{}'.".format(job_position)
    else:
        # get a response from the LLM
        messages = [
            {"role": "system", "content": CHAT_CONTEXT},
            {"role": "assistant", "content": INITIAL_MSG},
            *st.session_state.chat_history
        ]

        # Display assistant response in chat message container
        with st.chat_message("assistant", avatar='🍇'):
            response_placeholder = st.empty()  # Create a placeholder for dynamic content
            stream = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                stream=True  # for streaming the message
            )
            response_content = ""
            update_frequency = 5  # Update UI after every 5 chunks
            chunk_counter = 0
            for content in parse_groq_stream(stream):
                response_content += content
                chunk_counter += 1
                if chunk_counter % update_frequency == 0:
                    response_placeholder.markdown(response_content)  # Update the placeholder with new content
            response_placeholder.markdown(response_content)  # Final update with complete content

    st.session_state.chat_history.append(
        {"role": "assistant", "content": response_content})