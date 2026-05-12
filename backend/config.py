"""
Application configuration module.
Centralizes all environment variables, settings, and constants.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ─── Load Environment ────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ─── Logging (configured FIRST, before any other module uses it) ─────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("grocery_analytics")

# ─── Database ─────────────────────────────────────────────────────────
MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME: str = os.environ.get('DB_NAME', 'grocery_analytics')

# ─── API Keys ─────────────────────────────────────────────────────────
OPENAI_API_KEY: str | None = os.environ.get('OPENAI_API_KEY')
EMERGENT_LLM_KEY: str | None = os.environ.get('EMERGENT_LLM_KEY')
INTEGRATION_PROXY_URL: str = os.environ.get(
    'INTEGRATION_PROXY_URL',
    'https://integrations.emergentagent.com'
).rstrip('/')

# ─── CORS ─────────────────────────────────────────────────────────────
CORS_ORIGINS_RAW: str = os.environ.get("CORS_ORIGINS", "")
CORS_ALLOW_CREDENTIALS: bool = os.environ.get(
    "CORS_ALLOW_CREDENTIALS", "false"
).lower() in ("1", "true", "yes")

# ─── Application Constants ───────────────────────────────────────────
MAX_UPLOAD_SIZE_MB: int = 50
CHATBOT_MAX_TOKENS: int = 1000
CHATBOT_TEMPERATURE: float = 0.7
CHATBOT_MODEL: str = "gpt-4o"
IMAGE_EXTRACTION_MODEL: str = "gpt-4o"
IMAGE_EXTRACTION_MODEL_FALLBACK: str = "gpt-4o-mini"

# ABC Analysis thresholds
ABC_A_THRESHOLD: float = 80.0   # Top 80% revenue = Category A
ABC_B_THRESHOLD: float = 95.0   # Next 15% revenue = Category B
                                 # Remaining 5% = Category C

# Capital blocking
CAPITAL_BLOCKING_INFINITE_DAYS: int = 9999

# Forecast
FORECAST_MIN_PERIODS: int = 2
FORECAST_RECOMMENDED_PERIODS: int = 3

# Monthly summary items limit for API response
SUMMARY_ITEMS_DISPLAY_LIMIT: int = 100
