# Shopper's Concierge Agent (Kurly 커스텀 버전)

이 프로젝트는 Google Cloud의 Shopper's Concierge Agent 데모를 기반으로 하여, **마켓컬리(Market Kurly)** 스타일의 UI와 Mock Data, 고도화된 검색 기능을 추가한 버전입니다. 사용자의 질문을 이해하고 최적의 상품을 추천해주는 AI 쇼핑 어시스턴트 데모입니다.

---

## 📌 원본 출처 (Original Source)

이 프로젝트는 다음의 예시와, Google Cloud 공식 샘플 및 리소스를 기반으로 제작되었습니다.
- **ksmin23 - Shopper Concierge Agent with ADK**: [Shopper Concierge Agent with ADK](https://github.com/ksmin23/my-adk-python-samples/tree/main/shopper-concierge-demo))
- **ADK (Agent Development Kit)**: [Agent Development Kit (ADK)](https://goo.gle/3RGrB9T)
- **데모 영상**: [(YouTube) Build AI agents for e-commerce with ADK + Vector Search](https://www.youtube.com/watch?v=UIntXBP--gI)
- **데모 소개 영상**: [Shopper's Concierge demo video](https://goo.gle/4jRbMJb)
- **샘플 노트북**: [Shopper's Concierge sample notebook](https://goo.gle/4kMkxot)
- **관련 이슈/가이드**: [Deploying ADK agent with MCP tools on VertexAI Agent Engine](https://github.com/googleapis/python-aiplatform/issues/5372#issuecomment-3181870896)

---

## ✨ 주요 변경 사항 (Key Changes)

원본 레포지토리에서 다음과 같은 개선 및 커스텀 작업이 이루어졌습니다.

### 1. UI/UX 고도화 (Market Kurly 브랜드 적용)
- **브랜드 컬러 적용**: 마켓컬리의 아이덴티티인 보라색(`#5f0080`) 테마를 적용하여 세련되고 일관된 UI를 제공합니다.
- **Execution Trace Panel 추가**: 에이전트가 내부적으로 어떤 도구(Tool)를 호출하고 어떻게 연구(Research)를 수행하는지 실시간으로 보여주는 패널을 우측에 추가하여 데모의 신뢰성과 시각적 재미를 높였습니다.

### 2. 검색 및 임베딩 최적화 (Middleware)
- **임베딩 모델 고정**: 차원 불일치 문제를 해결하기 위해 `gemini-embedding-2-preview` 모델로 고정하여 3072 차원의 일관된 임베딩을 생성합니다.
- **Task Prefix 적용**: 최신 검색 가이드에 따라 임베딩 생성 시 `task: search result |` 접두사를 추가하여 검색의 정확도를 대폭 향상시켰습니다.

### 3. 데이터 정제 및 연동
- **실제 이미지 링크 적용**: 가짜 데이터 대신 실제 동작하는 이미지 URL을 포함하도록 제품 데이터를 업데이트했습니다.
- **BigQuery 연동**: 정제된 데이터를 BigQuery(`market_kurly.products`)에 적재하여 실시간으로 메타데이터를 조회할 수 있도록 구현했습니다.

---

## 🛠 프로젝트 구조 (Project Structure)

이 프로젝트는 Google Agent Development Kit (ADK)를 사용하며, 멀티 에이전트 아키텍처를 보여줍니다.

- **`shopper_concierge/`**: 핵심 ADK 에이전트 폴더
  - **`agent.py`**: 전체 워크플로우를 오케스트레이션하는 메인 `root_agent` 정의.
  - **`sub_agents/research_agent.py`**: Google Search를 활용해 사용자 의도를 파악하고 쿼리를 생성하는 서브 에이전트.
  - **`tools.py`**: 벡터 검색 백엔드에서 상품을 조회하는 `find_shopping_items` 도구 포함.
- **`app/`**: 사용자가 인터랙션할 수 있는 Gradio 기반의 웹 애플리케이션 (Vertex AI Agent Engine 연동).
- **`middleware_api.py`**: Vertex AI Vector Search와 BigQuery를 연결해주는 FastAPI 기반의 미들웨어.

---

## 📐 아키텍처 (Architecture)

이 데모는 3계층 아키텍처를 사용합니다: 사용자 UI, 에이전트 로직을 호스팅하는 Vertex AI Agent Engine, 그리고 상품 검색을 위한 백엔드 서비스.

```ascii
+----------+
|          |
|   User   |
|          |
+----------+
     |
     | 1. User Question (HTTPS)
     v
+-------------------------------------------------------------------+
| Google Cloud                                                      |
|                                                                   |
|  +-------------------------------------------------------------+  |
|  | Gradio Web App                                              |  |
|  | (Cloud Run)                                                 |  |
|  +-------------------------------------------------------------+  |
|                 |                                                 |
|                 | 2. Query Agent Engine                           |
|                 v                                                 |
|  +-------------------------------------------------------------+  |
|  | Vertex AI Agent Engine                                      |  |
|  |                                                             |  |   
|  |  +-----------------------+   +--------------------------+   |  |
|  |  | Shopper Concierge     |-->| Research Sub-Agent       |   |  |   
|  |  | (Root Agent)          |   | (Uses Google Search)     |   |  |   
|  |  +-----------------------+   +--------------------------+   |  |
|  |            |                                                |  |
|  +------------|------------------------------------------------+  |
|               | 3. Call Vector Search API                         |
+---------------|---------------------------------------------------+
                |
                v
+----------------------------------+
|                                  |
| Vector Search Backend            |
| (External API Endpoint)          |
|                                  |
+----------------------------------+
```

---

## 🚀 시작하기 (Getting Started)

### 1. 환경 설정 (Prerequisites)

이 프로젝트는 ADK 에이전트(`shopper_concierge`)와 Gradio UI (`app`) 두 가지 주요 컴포넌트로 구성되어 있습니다.

#### 에이전트 의존성 설치:
```bash
cd shopper-concierge-demo/shopper_concierge
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

#### Gradio 앱 의존성 설치:
```bash
cd shopper-concierge-demo/app
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. 로컬 실행 방법 (Running Locally)

로컬에서 전체 솔루션을 실행하려면 먼저 에이전트를 Vertex AI Agent Engine에 배포해야 합니다.

1. **벡터 검색 백엔드 설정**:
   - `shopper_concierge/tools.py` 파일에서 벡터 검색 엔드포인트 URL을 확인하거나 수정하세요.

2. **에이전트 배포**:
   ```bash
   gcloud auth login
   gcloud config set project [YOUR_PROJECT_ID]
   ```
   배포 명령을 실행합니다:
   ```bash
   adk deploy agent_engine shopper_concierge_demo/shopper_concierge \
     --staging_bucket="gs://[YOUR_STAGING_BUCKET]" \
     --display_name="Shopper Concierge" \
     --project="[YOUR_PROJECT_ID]" \
     --region="us-central1"
   ```
   배포가 완료되면 출력되는 `AGENT_ENGINE_ID`를 복사해 두세요.

3. **Gradio 앱 설정 및 실행**:
   - `shopper-concierge-demo/app` 디렉토리로 이동합니다.
   - `.env.example` 파일을 복사하여 `.env` 파일을 만듭니다.
   - `.env` 파일에 `AGENT_ENGINE_ID`와 Google Cloud 프로젝트 정보를 입력합니다.
   - 앱을 실행합니다:
     ```bash
     python main.py
     ```

### 3. 데이터 수정 및 관리 (Data Management)

데모에 사용되는 상품 데이터를 수정하거나 추가하려면 다음 단계를 따르세요:

1. `shopper_concierge/kurly_mock_data.jsonl` 파일을 열어 데이터를 수정합니다.
2. 수정된 데이터를 BigQuery에 반영하기 위해 다음 명령어를 실행합니다:
   ```bash
   bq load --autodetect --source_format=NEWLINE_DELIMITED_JSON \
     --replace \
     [YOUR_PROJECT_ID]:market_kurly.products \
     shopper_concierge/kurly_mock_data.jsonl
   ```

---

## 📝 사용 예시 (Example Usage)

Gradio 앱이 실행되면 다음과 같이 질문할 수 있습니다.

> "지성 피부가 사용할 만한 파운데이션을 추천해줘."

에이전트는 먼저 Research Sub-Agent를 통해 "지성 피부", "파운데이션"에 대한 검색을 수행하여 최적의 검색 쿼리를 생성합니다. 이후 Vector Search 백엔드를 조회하여 가장 적합한 상품 리스트를 사용자에게 추천합니다.
