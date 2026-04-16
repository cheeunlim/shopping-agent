#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import gradio as gr
import os
import pandas as pd
import vertexai
import uuid
import logging
from vertexai import agent_engines
from dotenv import load_dotenv

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# --- Vertex AI Agent Engine Configuration ---
# Get Vertex AI related information from environment variables
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")

# Check for required environment variables
if not all([PROJECT_ID, LOCATION, AGENT_ENGINE_ID]):
  raise ValueError(
    "Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and "
    "AGENT_ENGINE_ID environment variables must be set."
  )

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Load the deployed agent
try:
  remote_agent = agent_engines.get(AGENT_ENGINE_ID)
except Exception as e:
  raise RuntimeError(f"Failed to load Vertex AI Agent Engine: {e}")
# ------------------------------------

def query_vertex_agent(user_query, user_id, session_id):
  """Sends a query to the Vertex AI Agent Engine and yields events."""
  logging.info(f"Querying Vertex AI agent for user '{user_id}' in session '{session_id}': '{user_query}'...")

  for event in remote_agent.stream_query(
    user_id=user_id,
    session_id=session_id,
    message=user_query
  ):
    # Extract text response
    if event.get('content', {}).get('parts', [{}])[0].get('text'):
      yield 'text', event['content']['parts'][0]['text']

    # Extract tool call information
    if 'content' in event and 'parts' in event['content']:
      for part in event['content']['parts']:
        if 'function_call' in part:
          func_call = part['function_call']
          yield 'trace', f"🤖 Triggering Tool: {func_call.get('name')}\n"
        
        if 'function_response' in part:
          func_resp = part['function_response']
          yield 'trace', f"✅ Tool Completed: {func_resp.get('name')}\n"
          if func_resp.get('name') == 'find_shopping_items':
            try:
              results = func_resp.get('response', {}).get('result', [])
              yield 'trace', f"   Found {len(results)} items.\n"
            except Exception as e:
              logging.error(f"Error parsing items from function_response: {e}")

def chat_with_agent(user_input, history, session_state):
  """
  Handles the conversation with the Vertex AI agent and yields updates for Gradio.
  """
  history = history or []

  # Get user_id and session_id from the session state
  user_id = session_state.get("user_id")
  session_id = session_state.get("session_id")

  # If a session has not started, create a new one
  if not user_id:
    user_id = f"gradio_user_{uuid.uuid4()}"
    session_state["user_id"] = user_id
    logging.info(f"New user connected: {user_id}")

  if not session_id:
    session_id = remote_agent.create_session(user_id=user_id)["id"]
    session_state["session_id"] = session_id
    logging.info(f"New session created for user '{user_id}': {session_id}")

  # Initialize history and trace
  history.append({"role": "user", "content": user_input})
  history.append({"role": "assistant", "content": ""})
  trace_content = "Starting search...\n"
  yield history, session_state, trace_content

  response_text = ""
  for msg_type, data in query_vertex_agent(user_input, user_id, session_id):
    if msg_type == 'text':
      response_text += data
      history[-1]["content"] = response_text
    elif msg_type == 'trace':
      trace_content += data
    
    yield history, session_state, trace_content

custom_css = """
#chatbot { height: 500px !important; }
.kurly-title { color: #5f0080 !important; font-weight: bold; }
.kurly-btn { background-color: #5f0080 !important; color: white !important; }
.kurly-btn:hover { background-color: #4a0066 !important; }
"""

# Gradio UI Configuration
with gr.Blocks(title="AI Shopping Assistant", css=custom_css) as demo:
  session_state = gr.State({})

  gr.Markdown(
    """
    # <span class="kurly-title">Kurly AI Shopping Assistant</span> 🤖
    
    How can I help you? Feel free to ask about the products you're looking for.
    (e.g., "지성 피부가 사용할 만한 파운데이션을 추천해줘.")
    """
  )

  with gr.Row():
    with gr.Column(scale=3):
      chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": "Hello! How can I help you find the perfect product today?"}],
        elem_id="chatbot",
      )

      with gr.Row():
        txt = gr.Textbox(
          show_label=False,
          placeholder="Enter your message here...",
          container=False,
          scale=10
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1, elem_classes=["kurly-btn"])

    with gr.Column(scale=1):
      gr.Markdown("### 🔍 Agent Research Process")
      trace_box = gr.Textbox(
        label="Execution Trace",
        interactive=False,
        lines=23,
        placeholder="Search process will be displayed here..."
      )

  # Event Handlers
  txt.submit(
    chat_with_agent,
    [txt, chatbot, session_state],
    [chatbot, session_state, trace_box]
  )
  submit_btn.click(
    chat_with_agent,
    [txt, chatbot, session_state],
    [chatbot, session_state, trace_box]
  )

if __name__ == "__main__":
  logging.info(f"Connecting to Vertex AI Agent Engine: {AGENT_ENGINE_ID}")
  demo.launch(debug=True, theme=gr.themes.Soft(primary_hue="purple"))
