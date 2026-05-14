# Demo Scenarios - Shopper's Concierge

This document summarizes the demo scenarios for the Shopper's Concierge agent, highlighting different AI capabilities.

## Scenario 1: Research & Recommendation (Sub-Agent)
*   **User Query**: "엄마 생일 선물로 화장품 사드릴 거 추천해줘. 60대 여성이셔." (Recommend cosmetics for my mom's birthday. She is in her 60s.)
*   **Capability**: `Research Sub-Agent` uses Google Search to understand trends for 60s women's cosmetics, generates queries, and finds products.

## Scenario 2: Review-Based Comparative Search
*   **User Query**: "아보카도 중에서 가성비가 좋은 제품 순서로 추천해줄 수 있어?" (Can you recommend avocado products in order of cost-effectiveness?)
*   **Capability**: `Review Sub-Agent` queries the review vector index, analyzes customer feedback, and ranks products by value/satisfaction.

## Scenario 3: Multimodal Vibe Search
*   **User Query**: "이런 감성의 브런치 테이블을 만들고 싶어" + [Upload Image] (I want to make a brunch table with this vibe)
*   **Capability**: Gemini analyzes the image to extract items across categories (Food, Decor, Vibe) and generates search queries for the catalog.
*   **Note**: This approach leverages Gemini's native multimodality and reasoning to generate text queries, avoiding the need for a full multimodal vector search pipeline for the demo.

+ Multimodal: Mercardi Demo?


Focus: Vector Search + Embedding + BQ(리뷰 및 상품 데이터) + ADK + Agent Engine > 원큐에 가능하다
