#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import gradio as gr
import os
import pandas as pd
import vertexai
import uuid
import logging
import json
import re
from vertexai import agent_engines
from dotenv import load_dotenv
from PIL import Image
from google import genai
from shopper_concierge.tools import find_shopping_items
from shopper_concierge.prompts import instruction_vibe

load_dotenv()

# Configure Gemini API
client = genai.Client()


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
    logging.info(f"Event received: {event}")
    if 'content' in event and 'parts' in event['content']:
      for part in event['content']['parts']:
        if 'text' in part:
          yield 'text', part['text']
        
        if 'function_call' in part:
          func_call = part['function_call']
          yield 'trace', f"🤖 도구 실행: {func_call.get('name')}\n"
        
        if 'function_response' in part:
          func_resp = part['function_response']
          yield 'trace', f"✅ 도구 완료: {func_resp.get('name')}\n"
          if func_resp.get('name') == 'find_shopping_items':
            try:
              results = func_resp.get('response', {}).get('result', [])
              yield 'trace', f"   {len(results)}개의 상품을 찾았습니다.\n"
            except Exception as e:
              logging.error(f"Error parsing items from function_response: {e}")
          else:
            try:
              response_data = func_resp.get('response', {})
              if response_data:
                yield 'trace', f"   출력: {json.dumps(response_data, ensure_ascii=False)}\n"
            except Exception as e:
              logging.error(f"Error parsing tool response: {e}")


def render_a2ui(text):
  """Parses A2UI JSON blocks and converts them to HTML buttons."""
  pattern = r"(?m)^\s*```json\s*\n(.*?)\n\s*```"
  
  def replacer(match):
    json_str = match.group(1)
    try:
      data = json.loads(json_str)
      if data.get("component") == "Button" and data.get("text") == "카트에 담기":
        item_name = data.get("parameters", {}).get("item_name", "Item")
        # Return HTML button styled with Kurly color
        return f'<button class="kurly-btn" style="padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; margin-top: 5px;">🛒 {data["text"]} ({item_name})</button>'
    except Exception as e:
      logging.error(f"Failed to parse A2UI JSON: {e}")
    return match.group(0)
      
  return re.sub(pattern, replacer, text, flags=re.DOTALL)


def chat_with_agent(user_input, image_input, history, session_state):
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

  if image_input:
    logging.info("Vibe Search requested with image.")
    history.append({"role": "user", "content": user_input or "이미지 검색 요청"})
    history.append({"role": "assistant", "content": ""})
    trace_content = "이미지 분석 중...\n"
    yield history, session_state, trace_content, ""
    
    try:
      # Call Gemini
      prompt = f"{instruction_vibe}\n\nUser Query: {user_input}"
      response = client.models.generate_content(
          model='gemini-3.1-flash-lite',
          contents=[image_input, prompt]
      )
      
      trace_content += "이미지 분석 완료. 쿼리 생성 중...\n"
      yield history, session_state, trace_content, ""
      
      queries_text = response.text
      trace_content += f"생성된 쿼리:\n{queries_text}\n"
      yield history, session_state, trace_content, ""
      
      # Extract queries
      queries = []
      for line in queries_text.split('\n'):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
          parts = line.split('.', 1) if '.' in line else [line]
          query = parts[-1].strip()
          if query:
            queries.append(query)
        elif line and not line.startswith('Here are') and not line.startswith('Queries:'):
          queries.append(line)
          
      if not queries:
         queries = [l.strip() for l in queries_text.split('\n') if l.strip()][:5]
         
      trace_content += f"추출된 쿼리: {queries}\n"
      trace_content += "상품 검색 중...\n"
      yield history, session_state, trace_content, ""
      
      # Call find_shopping_items
      items = find_shopping_items(queries)
      
      # Limit to 10 items
      items = items[:10]
      
      trace_content += f"검색 완료: {len(items)}개의 상품을 찾았습니다.\n"
      yield history, session_state, trace_content, ""
      
      # Synthesis Step: Call Gemini to generate reasons for the found items
      trace_content += "답변 생성 중...\n"
      yield history, session_state, trace_content, ""
      
      synthesis_prompt = f"""
      사용자의 요청: "{user_input}"
      검색된 상품들:
      {json.dumps([{ 'name': item.get('name'), 'description': item.get('description') } for item in items], ensure_ascii=False)}
      
      위 상품들 중 사용자의 요청(분위기, 상황 등)에 어울리는 상품들만 엄선하여 추천 이유와 함께 JSON 리스트로 반환해줘.
      각 상품별로 추천하는 이유를 한 문장으로 요약해서 설명해줘.
      
      [주의사항]
      - 사용자의 요청과 무관한 상품(예: 브런치 요청인데 쌀, 화장품, 어묵탕 등)은 결과 리스트에서 제외해줘.
      - 제외한 상품에 대한 안내나 참고 메시지(예: "무관한 상품은 제외했습니다")는 절대 포함하지 마. 오직 추천할 상품들의 JSON 데이터만 반환해줘.
      - 불필요한 정보(예: 브런치 요청인데 캠핑이나 안주 언급)는 제외하고, 사용자의 요청에 맞춰서 재료를 추천하는 이유를 적어줘.
      
      [출력 형식]
      반드시 다음 형식의 JSON 리스트로 반환해줘. 코드 블록(`json`)으로 감싸줘.
      [
        {{
          "name": "[컬리단독] 수제 치아바타 생지 (3개)",
          "reason": "갓 구운 빵 특유의 고소한 향으로 홈브런치 특유의 여유로운 분위기를 연출해 줍니다."
        }}
      ]
      """
      
      try:
        synthesis_response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=synthesis_prompt
        )
        json_str = synthesis_response.text
        if "```json" in json_str:
          json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
          json_str = json_str.split("```")[1].split("```")[0]
          
        recommended_items = json.loads(json_str.strip())
        
        response_text = f"이미지를 분석하여 다음 상품들을 찾았습니다:\n\n"
        for r_item in recommended_items:
          name = r_item.get('name')
          reason = r_item.get('reason')
          response_text += f"- **{name}**: {reason}\n"
          
          # Add A2UI button right after the item
          a2ui_json = {
            "component": "Button",
            "text": "카트에 담기",
            "action": "add_to_cart",
            "parameters": {
              "item_name": name
            }
          }
          response_text += f"```json\n{json.dumps(a2ui_json, ensure_ascii=False)}\n```\n\n"
          
      except Exception as e:
        logging.error(f"Error in synthesis or parsing: {e}")
        # Fallback to raw descriptions if synthesis fails
        response_text = f"이미지를 분석하여 다음 상품들을 찾았습니다:\n\n"
        for item in items:
          response_text += f"- **{item.get('name')}**: {item.get('description')}\n"
          a2ui_json = {
            "component": "Button",
            "text": "카트에 담기",
            "action": "add_to_cart",
            "parameters": {
              "item_name": item.get('name')
            }
          }
          response_text += f"```json\n{json.dumps(a2ui_json, ensure_ascii=False)}\n```\n\n"
          
      history[-1]["content"] = render_a2ui(response_text)
      yield history, session_state, trace_content, ""
      return
      
    except Exception as e:
      logging.error(f"Error in vibe search: {e}")
      trace_content += f"❌ 에러 발생: {e}\n"
      history[-1]["content"] = "죄송합니다. 이미지를 처리하는 중 오류가 발생했습니다."
      yield history, session_state, trace_content, ""
      return

  # Initialize history and trace
  history.append({"role": "user", "content": user_input})
  history.append({"role": "assistant", "content": ""})
  trace_content = "검색을 시작합니다...\n"
  yield history, session_state, trace_content, ""

  response_text = ""
  for msg_type, data in query_vertex_agent(user_input, user_id, session_id):
    if msg_type == 'text':
      response_text += data
      history[-1]["content"] = render_a2ui(response_text)
    elif msg_type == 'trace':
      trace_content += data
    
    yield history, session_state, trace_content, ""

custom_css = """
#chatbot { height: 500px !important; }
.kurly-title { color: #5f0080 !important; font-weight: bold; }
.kurly-btn { background-color: #5f0080 !important; color: white !important; }
.kurly-btn:hover { background-color: #4a0066 !important; }
"""

# Gradio UI Configuration
with gr.Blocks(title="AI 쇼핑 어시스턴트", css=custom_css) as demo:
  session_state = gr.State({})

  gr.Markdown(
    """
    # <span class="kurly-title">Kurly AI Shopping Assistant</span> 🤖
    
    무엇을 도와드릴까요? 찾으시는 상품에 대해 자유롭게 물어보세요.
    (e.g., "지성 피부가 사용할 만한 파운데이션을 추천해줘.")
    """
  )

  with gr.Row():
    with gr.Column(scale=3):
      chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": "안녕하세요! 오늘 어떤 상품을 찾아드릴까요?"}],
        elem_id="chatbot",
      )

      with gr.Accordion(label="이미지 업로드 (Vibe Search)", open=False):
        img_input = gr.Image(show_label=False, type="pil", sources=["upload"])

      with gr.Row():
        txt = gr.Textbox(
          show_label=False,
          placeholder="메시지를 입력하세요...",
          container=False,
          scale=10
        )
        submit_btn = gr.Button("전송", variant="primary", scale=1, elem_classes=["kurly-btn"])

    with gr.Column(scale=1):
      gr.Markdown("### 🔍 Agent Research Process")
      trace_box = gr.Textbox(
        label="실행 과정",
        interactive=False,
        lines=23,
        placeholder="검색 과정이 여기에 표시됩니다..."
      )

  # Event Handlers
  txt.submit(
    chat_with_agent,
    [txt, img_input, chatbot, session_state],
    [chatbot, session_state, trace_box, txt]
  )
  submit_btn.click(
    chat_with_agent,
    [txt, img_input, chatbot, session_state],
    [chatbot, session_state, trace_box, txt]
  )

if __name__ == "__main__":
  logging.info(f"Connecting to Vertex AI Agent Engine: {AGENT_ENGINE_ID}")
  demo.launch(debug=True, theme=gr.themes.Soft(primary_hue="purple"))
