#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import json
import logging
import os
import requests
from typing import Any, Dict, List

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def call_vector_search(url: str, query: str, rows: int | None = None) -> Dict | None:
  """
  Calls the Vector Search backend for querying.

  Args:
    url: The URL of the search endpoint.
    query: The query string.
    rows: The number of result rows to return. Defaults to None.

  Returns:
    The JSON response from the API, or None if an error occurs. The JSON
    response is expected to have a 'result' key, which contains a list of
    item objects. Each item object includes details such as 'id', 'name',
    'description', 'img_url', and various search relevance scores.
  """
  # Build HTTP headers and a payload
  headers = {"Content-Type": "application/json"}
  payload = {
    "query": query,
    "rows": rows,
    "dataset_id": "mercari3m_mm",  # Use Mercari 3M multimodal index
    "use_dense": True,  # Use multimodal search
    "use_sparse": True,  # Use keyword search too
    "rrf_alpha": 0.5,  # Both results are merged with the same weights
    "use_rerank": True,  # Use Ranking API for reranking
  }

  # Send an HTTP request to the search endpoint
  try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()
  except requests.exceptions.RequestException as e:
    logging.error(f"Error calling the API: {e}")
    return None


def find_shopping_items(queries: List[str]) -> List[Dict[str, Any]]:
  """
  Find shopping items from the e-commerce site with the specified list of
  queries. This function calls a Vector Search backend to find items.

  Args:
    queries: the list of queries to run.
  Returns:
    A list of item objects found on the e-commerce site. Each object is a
    dictionary containing details like 'id', 'name', 'description',
    and 'img_url'.
  """
  url = os.environ.get("SHOPPER_SEARCH_API_URL", "https://middleware-api-794936295458.asia-northeast3.run.app/api/query")

  items = []
  for query in queries:
    # Clean up query: remove markdown bold and numbering
    query = query.strip().replace("**", "")
    if query and query[0].isdigit() and ". " in query:
      query = query.split(". ", 1)[1]
      
    result = call_vector_search(
      url=url,
      query=query,
      rows=3,
    )
    if result and "items" in result:
      items.extend(result["items"])

  # Fetch prices from BigQuery
  if items:
    from google.cloud import bigquery
    project_id = os.environ.get("PROJECT_ID", "sigma-firmament-450004-r3")
    bq_table = "market_kurly.products"
    client = bigquery.Client(project=project_id)
    
    item_ids = [item["id"] for item in items if "id" in item]
    if item_ids:
      # Remove duplicates
      item_ids = list(set(item_ids))
      
      # Build SQL IN clause
      id_list_str = ", ".join([f"'{id}'" for id in item_ids])
      sql = f"""
          SELECT id, price 
          FROM `{project_id}.{bq_table}` 
          WHERE id IN ({id_list_str})
      """
      
      try:
        results = client.query(sql).result()
        price_map = {row.id: row.price for row in results}
        
        # Update items with price
        for item in items:
          if "id" in item and item["id"] in price_map:
            item["price"] = price_map[item["id"]]
      except Exception as e:
        logging.error(f"Error querying product prices: {e}")

  logging.debug("-----")
  logging.debug(f"User queries: {queries}")
  logging.debug(f"Found: {len(items)} items")
  logging.debug("-----")

  return items


def query_reviews(query: str) -> List[Dict[str, Any]]:
  """
  Queries product reviews from BigQuery containing the specified keyword.

  Args:
    query: The keyword to search for in reviews.

  Returns:
    A list of dictionaries containing 'product_id' and 'content' of the reviews.
  """
  from google.cloud import bigquery
  
  project_id = os.environ.get("PROJECT_ID", "sigma-firmament-450004-r3")
  bq_table = "market_kurly.reviews"
  
  client = bigquery.Client(project=project_id)
  
  keywords = [kw.strip('\'",') for kw in query.split()]
  logging.info(f"query_reviews called with query: '{query}'")
  logging.info(f"Keywords extracted: {keywords}")
  if not keywords:
    return []
    
  # Build dynamic SQL with OR conditions
  where_clauses = []
  query_parameters = []
  for i, kw in enumerate(keywords):
    param_name = f"kw_{i}"
    where_clauses.append(f"content LIKE @{param_name}")
    query_parameters.append(bigquery.ScalarQueryParameter(param_name, "STRING", f"%{kw}%"))
    
  where_str = " OR ".join(where_clauses)
  
  # Safe query with parameterization
  sql = f"""
      SELECT r.product_id, r.content, p.name, p.description
      FROM `{project_id}.{bq_table}` r
      LEFT JOIN `{project_id}.market_kurly.products` p ON r.product_id = p.id
      WHERE {where_str}
      LIMIT 10
  """
  
  logging.info(f"Generated SQL: {sql}")
  job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
  
  try:
    results = client.query(sql, job_config=job_config).result()
    reviews = []
    for row in results:
      reviews.append({
          "product_id": row.product_id,
          "content": row.content,
          "product_name": row.name,
          "product_description": row.description
      })
    logging.info(f"Found {len(reviews)} reviews.")
    return reviews
  except Exception as e:
    logging.error(f"Error querying reviews: {e}")
    return []