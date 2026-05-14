import json
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
# Use the hardcoded key that worked before
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

try:
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Could not initialize gemini-2.5-flash: {e}")
    print("Falling back to gemini-1.5-flash")
    model = genai.GenerativeModel('gemini-1.5-flash')

src = "shopper_concierge/kurly_expanded_data.jsonl"
dst = "shopper_concierge/kurly_reviews.jsonl"

# Read and filter items
selected_items = []
if os.path.exists(src):
    with open(src, "r") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                name = item.get("name", "")
                if "샴푸" in name or "우유" in name or "돼지" in name or "삼겹살" in name or "목살" in name:
                    selected_items.append(item)
else:
    print(f"Source file {src} not found.")
    exit(1)

print(f"Found {len(selected_items)} matching items.")
# Limit to 200
selected_items = selected_items[:200]
print(f"Selected {len(selected_items)} items for review generation.")

def generate_reviews(item):
    prompt = f"""
    다음 상품에 대해 한국 소비자들이 작성했을 법한 생생한 리뷰 20개를 작성해줘.
    각 리뷰는 줄글로 1~5문장 정도로 작성하고, 실제 소비자의 입장에서 쓸만한 리뷰로 다양하게 작성해줘. 마켓컬리 소비자들이 쓸만한 내용으로. 이 내용이 최대한 
    칭찬하는 포인트(가격, 품질, 효과 등)를 다양하게 하고, 가끔은 아쉬운 점도 포함해줘.
    
    상품 ID: {item['id']}
    상품 이름: {item['name']}
    상품 설명: {item['description']}
    상품 카테고리: {item['category']}
    상품 가격: {item['price']}원

    출력 형식은 JSON Lines 형식이어야 하며, 각 줄은 다음과 같은 필드를 가진 JSON 객체여야 해:
    - review_id: 'REV_0001'부터 시작해서 고유한 ID
    - product_id: '{item['id']}'
    - content: 리뷰 내용 (줄글)

    출력은 오직 JSON Lines 데이터만 포함해야 해. 다른 설명이나 마크다운 태그는 포함하지 마.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "```" in text:
            text = text.split("```")[1].split("```")[0]
            if text.startswith("json"):
                text = text[4:]
        
        text = text.strip()
        
        # Try to parse as JSON array first (in case model outputs a list)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback to JSON lines
            reviews = []
            for line in text.split("\n"):
                if line.strip():
                    try:
                        reviews.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Ignore lines like [ or ] or , if it was a malformed array
                        pass
            return reviews
            
    except Exception as e:
        print(f"Error generating reviews for {item['id']}: {e}")
        return []

# Process and append
review_counter = 1
with open(dst, "w") as f:
    pass # Start with a clean file

for i, item in enumerate(selected_items):
    print(f"Processing item {i+1}/{len(selected_items)}: {item['id']}...")
    reviews = generate_reviews(item)
    
    if not reviews:
        print(f"Failed to generate reviews for {item['id']}. Retrying once...")
        time.sleep(5)
        reviews = generate_reviews(item)
        
    with open(dst, "a") as f:
        for review in reviews:
            if isinstance(review, dict):
                # Ensure product_id matches the item ID
                review['product_id'] = item['id']
                # Override review_id to be sequential across all items
                review['review_id'] = f"REV_{review_counter:04d}"
                f.write(json.dumps(review, ensure_ascii=False) + "\n")
                review_counter += 1
    
    time.sleep(2) # Avoid rate limit

print(f"Finished! Generated {review_counter - 1} reviews for {len(selected_items)} items.")
