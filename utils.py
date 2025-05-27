#!/usr/bin/env python3
"""
Utility functions and shared tools for the Kids Weather application.
"""
import json
import hashlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
import diskcache

from config import API_CACHE_DIR, API_CACHE_TIME, LLM_LOG_DB_FILE

# Initialize shared cache
cache = diskcache.Cache(API_CACHE_DIR)

def format_time(timestamp, timezone_offset=0):
    """Convert Unix timestamp to human-readable time in local timezone."""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc) + timedelta(seconds=timezone_offset)
    return dt.strftime("%I:%M %p")  # Format: "01:30 PM"

def format_alert_time(timestamp, timezone_offset):
    """Format alert time, showing date if not today."""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc) + timedelta(seconds=timezone_offset)
    today = datetime.now(timezone(timedelta(seconds=timezone_offset))).date()
    if dt.date() == today:
        return dt.strftime("%-I%p")
    return dt.strftime("%-I%p %a")

def init_llm_log_db():
    """Initialize the SQLite database for logging LLM interactions."""
    conn = sqlite3.connect(LLM_LOG_DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            location_name TEXT,
            weather_input TEXT, -- JSON string of the raw weather API data
            llm_context TEXT,   -- The exact formatted context sent to LLM
            system_prompt TEXT,
            model_used TEXT,
            llm_output TEXT,    -- JSON string of the raw LLM response content
            description TEXT,   -- Extracted description text
            source TEXT         -- e.g., 'flask', 'script', 'replay'
        )
    ''')

    # Check if llm_context column exists, add it if not (for existing databases)
    cursor.execute("PRAGMA table_info(llm_interactions)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'llm_context' not in columns:
        cursor.execute('ALTER TABLE llm_interactions ADD COLUMN llm_context TEXT')

    conn.commit()
    conn.close()

def log_llm_interaction(location_name, weather_input, system_prompt, model_used, llm_output_raw, description, source, llm_context=None):
    """Logs the details of an LLM interaction to the database."""
    try:
        conn = sqlite3.connect(LLM_LOG_DB_FILE)
        cursor = conn.cursor()
        # Ensure complex objects are stored as JSON strings
        weather_input_json = json.dumps(weather_input)
        llm_output_json = json.dumps(llm_output_raw)

        cursor.execute('''
            INSERT INTO llm_interactions (location_name, weather_input, llm_context, system_prompt, model_used, llm_output, description, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (location_name, weather_input_json, llm_context, system_prompt, model_used, llm_output_json, description, source))
        conn.commit()
        conn.close()
        print(f"Logged LLM interaction from {source} for {location_name}")
    except sqlite3.Error as e:
        print(f"Database error during logging: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error logging LLM interaction: {e}", file=sys.stderr)

def save_weather_data(data, filename=None, data_dir=None):
    """Save weather data to a file for testing."""
    from config import TEST_DATA_DIR

    if not data_dir:
        data_dir = TEST_DATA_DIR

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weather_{timestamp}.json"

    filepath = data_dir / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    return str(filepath)

def load_weather_data(filename, data_dir=None):
    """Load weather data from a test file."""
    from config import TEST_DATA_DIR

    if not data_dir:
        data_dir = TEST_DATA_DIR

    filepath = data_dir / filename
    print(f"Loading data from {filepath}")
    with open(filepath, 'r') as f:
        return json.load(f)

def load_system_prompt(prompt_file=None):
    """Loads the system prompt from the specified file."""
    from config import DEFAULT_PROMPT_FILE

    if not prompt_file:
        prompt_file = DEFAULT_PROMPT_FILE

    try:
        with open(prompt_file, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {prompt_file}", file=sys.stderr)
        # Fallback to a minimal default prompt if file is missing
        return "You are a helpful weather assistant providing JSON output."
    except Exception as e:
        print(f"Error reading prompt file {prompt_file}: {e}", file=sys.stderr)
        return "You are a helpful weather assistant providing JSON output."

def get_cache_key(prefix, *args):
    """Generate a consistent cache key from a prefix and arguments."""
    key_parts = [prefix]

    for arg in args:
        if isinstance(arg, dict):
            # Sort dictionary keys for consistent hashing
            arg_hash = hashlib.sha256(json.dumps(arg, sort_keys=True).encode()).hexdigest()[:16]
            key_parts.append(arg_hash)
        elif isinstance(arg, (list, tuple)):
            # Hash list/tuple contents
            arg_hash = hashlib.sha256(json.dumps(arg).encode()).hexdigest()[:16]
            key_parts.append(arg_hash)
        elif isinstance(arg, str) and len(arg) > 50:
            # Hash long strings
            arg_hash = hashlib.sha256(arg.encode()).hexdigest()[:16]
            key_parts.append(arg_hash)
        else:
            # Use short strings and numbers directly
            key_parts.append(str(arg))

    return "_".join(key_parts)
