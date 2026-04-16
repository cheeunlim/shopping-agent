import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from google.cloud import aiplatform
from google.cloud import bigquery
from dotenv import load_dotenv
import vertexai
from vertexai.language_models import TextEmbeddingModel
import google.generativeai as genai

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
INDEX_ENDPOINT_ID = os.getenv("INDEX_ENDPOINT_ID")
DEPLOYED_INDEX_ID = os.getenv("DEPLOYED_INDEX_ID")
BQ_TABLE = os.getenv("BQ_TABLE", "market_kurly.products")

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)
aiplatform.init(project=PROJECT_ID, location=REGION)

app = FastAPI()

class SearchRequest(BaseModel):
    query: str
    rows: Optional[int] = 5

class SearchResponse(BaseModel):
    items: List[dict]

def get_query_embedding(query_text: str) -> List[float]:
    """Generates a text embedding for the query text using gemini-embedding-2-preview."""
    try:
        model = "models/gemini-embedding-2-preview"
        formatted_query = f"task: search result | query: {query_text}"
        embedding = genai.embed_content(model=model, content=formatted_query)
        return embedding['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise e

def vector_search(embedding: List[float], limit: int) -> List[str]:
    """Queries Vertex AI Vector Search."""
    try:
        endpoint_name = f"projects/{PROJECT_ID}/locations/{REGION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        endpoint = aiplatform.MatchingEngineIndexEndpoint(endpoint_name)
        
        response = endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[embedding],
            num_neighbors=limit
        )
        
        # Extract IDs from response
        if response and response[0]:
            ids = [neighbor.id for neighbor in response[0]]
            return ids
        return []
    except Exception as e:
        print(f"Error in vector search: {e}")
        raise e

def get_metadata(ids: List[str]) -> List[dict]:
    """Fetches product metadata from BigQuery for the given IDs."""
    if not ids:
        return []
        
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        # Safe query with parameterization
        query = f"""
            SELECT id, name, description, img_url 
            FROM `{BQ_TABLE}` 
            WHERE id IN UNNEST(@ids)
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("ids", "STRING", ids)
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        items = []
        for row in results:
            items.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "img_url": row.img_url
            })
            
        # Sort results to match the order of IDs returned by Vector Search
        id_map = {id_: i for i, id_ in enumerate(ids)}
        items.sort(key=lambda x: id_map.get(x["id"], 999))
        
        return items
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        raise e

@app.post("/api/query", response_model=SearchResponse)
async def query_endpoint(request: SearchRequest):
    try:
        # 1. Get embedding for query
        embedding = get_query_embedding(request.query)
        
        # 2. Search in Vector DB
        ids = vector_search(embedding, request.rows)
        
        # 3. Get metadata from BigQuery
        results = get_metadata(ids)
        
        return SearchResponse(items=results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
