#!/usr/bin/env python3
"""
Configuration module for the Kids Weather application.
Contains all constants, paths, and environment variable handling.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directory paths
ROOT_DIR = Path(__file__).parent
TEST_DATA_DIR = ROOT_DIR / "test_data"
API_CACHE_DIR = ROOT_DIR / "api_cache"
PROMPT_DIR = ROOT_DIR / "prompts"

# Ensure directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
API_CACHE_DIR.mkdir(exist_ok=True)

# File paths
LLM_LOG_DB_FILE = ROOT_DIR / 'llm_log.sqlite3'
DEFAULT_PROMPT_FILE = PROMPT_DIR / "default.txt"

# API URLs
WEATHER_API_URL = "https://api.openweathermap.org/data/3.0/onecall"
WEATHER_TIMEMACHINE_API_URL = "https://api.openweathermap.org/data/3.0/onecall/timemachine"

# LLM Configuration - all required from environment
LLM_API_URL = os.getenv('LLM_API_URL')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL')
LLM_SUPPORTS_JSON_MODE = os.getenv('LLM_SUPPORTS_JSON_MODE', 'true').lower() == 'true'

# Fallback LLM Configuration - optional
FALLBACK_LLM_API_URL = os.getenv('FALLBACK_LLM_API_URL')
FALLBACK_LLM_API_KEY = os.getenv('FALLBACK_LLM_API_KEY')
FALLBACK_LLM_MODEL = os.getenv('FALLBACK_LLM_MODEL')
FALLBACK_LLM_SUPPORTS_JSON_MODE = os.getenv('FALLBACK_LLM_SUPPORTS_JSON_MODE', 'true').lower() == 'true'

# Cache settings
API_CACHE_TIME = 600  # 10 minutes cache TTL in seconds

# API keys with fallbacks for easier testing
def get_api_key(key_name, fallback=None):
    """Get API key from environment with optional fallback for testing"""
    value = os.getenv(key_name)
    if not value and fallback is not None:
        return fallback
    return value

# Get API keys
WEATHER_API_KEY = get_api_key('WEATHER_API_KEY')

# Validate LLM configuration
if not LLM_API_URL:
    raise ValueError("LLM_API_URL environment variable is required")
if not LLM_API_KEY:
    raise ValueError("LLM_API_KEY environment variable is required")
if not LLM_MODEL:
    raise ValueError("LLM_MODEL environment variable is required")

# Check if fallback is properly configured when provided
FALLBACK_LLM_ENABLED = bool(FALLBACK_LLM_API_URL and FALLBACK_LLM_API_KEY and FALLBACK_LLM_MODEL)
if FALLBACK_LLM_API_URL or FALLBACK_LLM_API_KEY or FALLBACK_LLM_MODEL:
    # If any fallback var is set, all must be set
    if not FALLBACK_LLM_ENABLED:
        raise ValueError("If using fallback LLM, all FALLBACK_LLM_* variables must be set (API_URL, API_KEY, MODEL)")

# Default settings
DEFAULT_LAT = 38.9541848  # Washington, DC
DEFAULT_LON = -77.0832061  # Washington, DC
DEFAULT_LOCATION = "Washington, DC"

# Weather units
WEATHER_UNITS = "imperial"  # Use Fahrenheit