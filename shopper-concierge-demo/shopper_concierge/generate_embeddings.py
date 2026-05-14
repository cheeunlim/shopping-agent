import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env from parent directory if run from within shopper_concierge
# or from current directory if run from root.
# Default load_dotenv() searches parent directories, so it should work.
load_dotenv(dotenv_path="/Users/cheeunlim/Desktop/26/data-agent/shopping-agent/shopper-concierge-demo/.env")

# Initialize Gemini Client (uses GEMINI_API_KEY from env)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

src = "shopper_concierge/kurly_expanded_data.jsonl"
dst = "shopper_concierge/kurly_embeddings.jsonl"

print(f"Reading items from {src}...")
items = []
if not os.path.exists(src):
    print(f"Source file {src} not found.")
    exit(1)

with open(src, "r") as f:
    for line in f:
        if line.strip():
            items.append(json.loads(line))

print(f"Loaded {len(items)} items.")

def get_embedding(text: str) -> list:
    model = "gemini-embedding-2"
    formatted_query = f"task: search result | query: {text}"
    try:
        result = client.models.embed_content(
            model=model,
            contents=formatted_query
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

print(f"Generating embeddings and saving to {dst}...")
success_count = 0
with open(dst, "w") as f:
    for i, item in enumerate(items):
        # Use name and description for embedding
        text_to_embed = f"{item.get('name', '')} {item.get('description', '')}"
        print(f"Processing {i+1}/{len(items)}: {item.get('name')}")
        
        embedding = get_embedding(text_to_embed)
        if embedding:
            output_item = {
                "id": str(item.get("id")),
                "embedding": embedding
            }
            f.write(json.dumps(output_item) + "\n")
            success_count += 1
        else:
            print(f"Failed to generate embedding for item {item.get('id')}")
            
        time.sleep(0.5) # Avoid rate limits
        
print(f"Finished. Successfully generated {success_count} embeddings.")
