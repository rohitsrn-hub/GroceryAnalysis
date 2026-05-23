"""
Semantic Service — Vector embeddings for product search and manual categorization training.
"""
import os
import math
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

from database import db
from config import logger

# In-memory cache for embeddings
# Format: [{"item_name": "...", "product_group": "...", "embedding": np.array([...])}]
_EMBEDDINGS_CACHE: List[Dict[str, Any]] = []

def _cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


async def load_embeddings_to_cache():
    """Load all product embeddings into memory for fast cosine similarity search."""
    global _EMBEDDINGS_CACHE
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_file = os.path.join(base_dir, "embeddings_cache.pkl")
    
    # 1. Try loading from local pickle file first
    if os.path.exists(cache_file):
        try:
            import pickle
            logger.info(f"Loading semantic embeddings from local cache: {cache_file}...")
            with open(cache_file, "rb") as f:
                cache = pickle.load(f)
            
            # Ensure they are loaded as np.ndarray
            for item in cache:
                if not isinstance(item["embedding"], np.ndarray):
                    item["embedding"] = np.array(item["embedding"], dtype=np.float32)
                    
            _EMBEDDINGS_CACHE = cache
            logger.info(f"Successfully loaded {len(_EMBEDDINGS_CACHE)} item embeddings from local cache.")
            return
        except Exception as e:
            logger.error(f"Failed to load embeddings from local cache file: {e}")
            
    # 2. Fallback to MongoDB if local cache is not available
    try:
        logger.info("Local cache not found. Fallback: loading semantic embeddings from MongoDB (this may time out)...")
        import asyncio
        docs = await asyncio.wait_for(
            db.item_embeddings.find({}, {"item_name": 1, "product_group": 1, "embedding": 1}).to_list(length=10000),
            timeout=60.0
        )
        cache = []
        for doc in docs:
            if "embedding" in doc:
                cache.append({
                    "item_name": doc["item_name"],
                    "product_group": doc.get("product_group", "Unknown"),
                    "embedding": np.array(doc["embedding"], dtype=np.float32)
                })
        
        _EMBEDDINGS_CACHE = cache
        logger.info(f"Successfully loaded {len(_EMBEDDINGS_CACHE)} item embeddings from MongoDB fallback.")
        
        # Save to local cache for future boots
        try:
            import pickle
            with open(cache_file, "wb") as f:
                pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Saved MongoDB embeddings to local cache: {cache_file}")
        except Exception as save_err:
            logger.error(f"Failed to save fetched embeddings to local cache: {save_err}")
            
    except Exception as e:
        logger.error(f"Failed to load embeddings from MongoDB fallback: {e}")


async def generate_all_embeddings():
    """Fetch all unique items, generate embeddings via OpenAI, and save to DB."""
    from openai import AsyncOpenAI
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    
    client = AsyncOpenAI(api_key=api_key)
    
    logger.info("Starting embedding generation for all unique items...")
    
    # Get all unique items with their groups
    pipeline = [
        {"$group": {"_id": "$item_name", "product_group": {"$first": "$product_group"}}}
    ]
    unique_items = await db.sales_records.aggregate(pipeline).to_list(None)
    
    # Prepare text for embedding
    items_to_embed = []
    for item in unique_items:
        if item["_id"]:
            # Combining group and item name provides rich semantic context
            text = f"Category: {item.get('product_group', 'Unknown')} - Item: {item['_id']}"
            items_to_embed.append({"item_name": item["_id"], "product_group": item.get('product_group', 'Unknown'), "text": text})
    
    total = len(items_to_embed)
    logger.info(f"Found {total} unique items to embed.")
    
    # Process in batches of 1000 to respect API limits
    batch_size = 1000
    for i in range(0, total, batch_size):
        batch = items_to_embed[i:i + batch_size]
        texts = [b["text"] for b in batch]
        
        logger.info(f"Calling OpenAI Embeddings API for batch {i} to {i+len(batch)}...")
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        
        # Save to DB
        operations = []
        for j, data in enumerate(response.data):
            item_info = batch[j]
            embedding_vector = data.embedding
            
            # Upsert into item_embeddings collection
            from pymongo import UpdateOne
            operations.append(UpdateOne(
                {"item_name": item_info["item_name"]},
                {"$set": {
                    "item_name": item_info["item_name"],
                    "product_group": item_info["product_group"],
                    "embedding": embedding_vector,
                    "updated_at": datetime.now()
                }},
                upsert=True
            ))
            
        if operations:
            await db.item_embeddings.bulk_write(operations)
            
    logger.info("Finished generating embeddings.")
    # Reload cache
    await load_embeddings_to_cache()
    return {"status": "success", "items_processed": total}


async def add_manual_mapping(category: str, item_names: List[str]):
    """Manually train the AI by mapping specific items to a category."""
    category = category.lower().strip()
    
    # Get existing mapping or create new
    existing = await db.semantic_mappings.find_one({"category": category})
    if existing:
        # Merge lists and ensure uniqueness
        current_items = set(existing.get("item_names", []))
        current_items.update(item_names)
        new_list = list(current_items)
        
        await db.semantic_mappings.update_one(
            {"category": category},
            {"$set": {"item_names": new_list, "updated_at": datetime.now()}}
        )
    else:
        await db.semantic_mappings.insert_one({
            "category": category,
            "item_names": item_names,
            "updated_at": datetime.now()
        })
        
    return {"status": "success", "category": category, "mapped_items": len(item_names)}


async def semantic_search_items(query: str, top_k: int = 20) -> List[str]:
    """Find the most relevant item names for a given semantic query."""
    from openai import AsyncOpenAI
    
    query = query.lower().strip()
    results_set = []
    
    # 1. Check manual training overrides FIRST
    override = await db.semantic_mappings.find_one({"category": {"$regex": f"^{query}$", "$options": "i"}})
    if override and "item_names" in override:
        results_set.extend(override["item_names"])
    
    # Check partial matches in overrides (e.g. if query is "luggage trolley" and override is "luggage")
    # For a robust system, we can do a text search on the categories, but simple matching is fine for now.
    
    # 2. Perform Vector Search to find more items
    if len(_EMBEDDINGS_CACHE) > 0:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY missing for semantic search.")
        else:
            try:
                client = AsyncOpenAI(api_key=api_key)
                response = await client.embeddings.create(
                    model="text-embedding-3-small",
                    input=[query]
                )
                query_vector = np.array(response.data[0].embedding, dtype=np.float32)
                
                # Calculate similarities
                scored_items = []
                for item in _EMBEDDINGS_CACHE:
                    # Skip items already in our manual overrides to avoid duplicates
                    if item["item_name"] in results_set:
                        continue
                        
                    sim = _cosine_similarity(query_vector, item["embedding"])
                    scored_items.append((sim, item["item_name"]))
                
                # Sort by highest similarity
                scored_items.sort(reverse=True, key=lambda x: x[0])
                
                # Append top matches
                for sim, name in scored_items[:top_k]:
                    if sim > 0.2: # basic threshold to avoid completely unrelated items
                        results_set.append(name)
                        
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                
    # If cache is empty or OpenAI fails, just do a basic regex fallback
    if not results_set:
        fallback = await db.sales_records.distinct("item_name", {"item_name": {"$regex": query, "$options": "i"}})
        results_set.extend(fallback[:top_k])
        
    # Deduplicate and truncate
    seen = set()
    final_results = []
    for item in results_set:
        if item not in seen:
            seen.add(item)
            final_results.append(item)
            
    return final_results[:top_k]
