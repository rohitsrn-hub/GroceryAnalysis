"""
Database connection and index management module.
Replaces global db object with managed lifecycle.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME, logger

# ─── MongoDB Connection ──────────────────────────────────────────────
client = AsyncIOMotorClient(
    MONGO_URL,
    maxPoolSize=20,
    minPoolSize=5,
    maxIdleTimeMS=30000,
)
db = client[DB_NAME]

# Note: Grocery app uses URCloh1GrocerySales database
# Liquor app uses URCloh1LiquorSales database
# This provides complete data separation without collection prefixes


# ─── Index Definitions ───────────────────────────────────────────────
INDEX_DEFINITIONS = {
    "sales_records": [
        {"keys": [("data_period", 1), ("upload_source", 1)], "name": "idx_period_source"},
        {"keys": [("pluno", 1), ("data_period", 1)], "name": "idx_pluno_period"},
        {"keys": [("upload_batch_id", 1)], "name": "idx_batch_id"},
        {"keys": [("product_group", 1)], "name": "idx_product_group"},
        {"keys": [("item_name", "text")], "name": "idx_item_name_text"},
        {"keys": [("item_name", 1)], "name": "idx_item_name"},
        {"keys": [("r_amt", -1)], "name": "idx_revenue_desc"},
        {"keys": [("gp_index_no", 1)], "name": "idx_gp_index"},
    ],
    "upload_history": [
        {"keys": [("upload_type", 1), ("data_date", 1)], "name": "idx_type_date"},
        {"keys": [("id", 1)], "name": "idx_upload_id"},
        {"keys": [("status", 1), ("upload_date", -1)], "name": "idx_status_date"},
    ],
    "financial_data": [
        {"keys": [("date", 1)], "name": "idx_fin_date"},
        {"keys": [("id", 1)], "name": "idx_fin_id"},
    ],
    "chat_history": [
        {"keys": [("session_id", 1), ("timestamp", -1)], "name": "idx_session_time"},
    ],
    "monthly_summaries": [
        {"keys": [("period", 1), ("summary_type", 1)], "name": "idx_period_type"},
    ],
    "customer_searches": [
        {"keys": [("timestamp", -1)], "name": "idx_search_timestamp"},
        {"keys": [("query", 1)], "name": "idx_search_query"},
        {"keys": [("is_available", 1)], "name": "idx_search_avail"},
    ],
}


async def ensure_indexes():
    """Create all required indexes on startup.

    Uses create_index which is idempotent — safe to call on every boot.
    """
    for collection_name, indexes in INDEX_DEFINITIONS.items():
        collection = db[collection_name]
        for idx in indexes:
            try:
                await collection.create_index(
                    idx["keys"],
                    name=idx["name"],
                    background=True,
                )
                logger.info(f"✓ Index {idx['name']} on {collection_name}")
            except Exception as e:
                logger.warning(f"Index {idx['name']} on {collection_name} skipped: {e}")


async def close_connection():
    """Close MongoDB connection gracefully."""
    client.close()
    logger.info("MongoDB connection closed")
