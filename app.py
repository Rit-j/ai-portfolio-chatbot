import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader

# =========================
# LOAD ENV
# =========================
load_dotenv()

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

# fallback for Streamlit Cloud
if not openrouter_api_key:
    openrouter_api_key = st.secrets["OPENROUTER_API_KEY"]

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
)

# =========================
# PUSHOVER (OPTIONAL)
# =========================
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(message):
    if pushover_user and pushover_token:
        payload = {
            "user": pushover_user,
            "token": pushover_token,
            "message": message
        }
        requests.post(pushover_url, data=payload)

# =========================
# TOOLS
# =========================
def record_user_details(email, name="Not provided", notes=""):
    push(f"User interested: {name}, {email}, {notes}")
    return {"status": "recorded"}

def record_unknown_question(question):
    push(f"Unknown question: {question}")
    return {"status": "recorded"}

tools = [
    {
        "type": "function",
        "function": {
            "name": "record_user_details",
            "description": "Capture user contact info",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_unknown_question",
            "description": "Log unanswered questions",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"}
                },
                "required": ["question"]
            }
        }
    }
]

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        if name == "record_user_details":
            result = record_user_details(**args)
        elif name == "record_unknown_question":
            result = record_unknown_question(**args)
        else:
            result = {}

        results.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id
        })
    return results

# =========================
# LOAD YOUR DATA
# =========================
reader = PdfReader("me/Profile_Ritik_merged.pdf")
linkedin = ""

for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text

with open("me/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()

name = "Ritik Joshi"

system_prompt = f"""
You are acting as {name}. You are answering questions on {name}'s portfolio website.

Use the following info:
Summary:
{summary}

LinkedIn:
{linkedin}

Be professional, helpful, and concise.
"""

# =========================
# CHAT FUNCTION
# =========================
def chat(user_input, history):
    messages = [{"role": "system", "content": system_prompt}] + history + [
        {"role": "user", "content": user_input}
    ]

    while True:
        response = openrouter.chat.completions.create(
            # model="nvidia/nemotron-3-super-120b-a12b:free",
            model=stepfun/step-3.5-flash:free,
            messages=messages,
            tools=tools
        )

        msg = response.choices[0].message

        # Tool call case
        if msg.tool_calls:
            tool_results = handle_tool_calls(msg.tool_calls)
            messages.append(msg)
            messages.extend(tool_results)
        else:
            return msg.content

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="Chat with Ritik", page_icon="🤖")

st.title("🤖 Chat with Ritik")
st.write("Ask anything about my experience, skills, or projects!")

# Chat memory
if "history" not in st.session_state:
    st.session_state.history = []

# Display previous messages
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input
user_input = st.chat_input("Ask me anything...")

if user_input:
    # Show user message
    st.chat_message("user").write(user_input)

    # Get response
    response = chat(user_input, st.session_state.history)

    # Save to history
    st.session_state.history.append({"role": "user", "content": user_input})
    st.session_state.history.append({"role": "assistant", "content": response})

    # Show response
    st.chat_message("assistant").write(response)
