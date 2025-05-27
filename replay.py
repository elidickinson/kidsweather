#!/usr/bin/env python3
"""
LLM interaction replay utility for Kids Weather.

This module allows replaying previous LLM interactions from the database,
optionally with different prompts or models.
"""
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
#     "python-dotenv",
#     "click",
# ]
# ///

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import click
from dotenv import load_dotenv

from config import LLM_LOG_DB_FILE, LLM_API_KEY
from api_client import call_llm_api

@click.command()
@click.option('--log-id', type=int, required=True, help='The ID from the llm_interactions table to replay.')
@click.option('--prompt', type=str, help='New system prompt text or path to a prompt file.')
@click.option('--new-model', type=str, help='New model name to use (e.g., gpt-3.5-turbo, deepseek-coder).')
@click.option('--show-context', is_flag=True, default=False, help='Print the original weather context data.')
def main(log_id, prompt, new_model, show_context):
    """Replays a logged LLM interaction, optionally with a new prompt or model."""
    # Check for API key
    if not LLM_API_KEY:
        print("Error: Missing LLM API key. Set LLM_API_KEY or provider-specific key in environment variables (.env file)", file=sys.stderr)
        sys.exit(1)

    conn = None
    try:
        if not os.path.exists(LLM_LOG_DB_FILE):
            print(f"Error: Log database file not found: {LLM_LOG_DB_FILE}", file=sys.stderr)
            print("Please run the main script or Flask app first to generate logs.", file=sys.stderr)
            sys.exit(1)

        # Connect to the database
        conn = sqlite3.connect(LLM_LOG_DB_FILE)
        cursor = conn.cursor()
        
        # Fetch the log entry
        cursor.execute("""
            SELECT timestamp, location_name, weather_input, llm_context, system_prompt, model_used, llm_output
            FROM llm_interactions
            WHERE id = ?
        """, (log_id,))
        row = cursor.fetchone()

        if not row:
            print(f"Error: No log entry found with ID {log_id}", file=sys.stderr)
            sys.exit(1)

        # Unpack the row
        original_timestamp, location_name, weather_input_str, llm_context_str, original_prompt, original_model, original_output_str = row

        # Parse the JSON strings
        try:
            original_weather_data = json.loads(weather_input_str)
        except json.JSONDecodeError:
            print(f"Error: Could not decode weather_input JSON for log ID {log_id}", file=sys.stderr)
            print(f"Raw data: {weather_input_str}", file=sys.stderr)
            sys.exit(1)
        
        # Use the exact LLM context if available, otherwise format from weather data
        if llm_context_str:
            original_context = llm_context_str
            print("Using exact LLM context from log.")
        else:
            # Fallback for older logs without llm_context
            from weather_processor import format_weather_for_llm
            original_context = format_weather_for_llm(original_weather_data)
            print("Formatting context from weather data (legacy log).")
            
        try:
            original_output = json.loads(original_output_str)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode original llm_output JSON for log ID {log_id}. Displaying raw.", file=sys.stderr)
            original_output = {"raw_output": original_output_str}  # Provide fallback

        # Format the timestamp
        try:
            # SQLite's CURRENT_TIMESTAMP format is 'YYYY-MM-DD HH:MM:SS'
            original_dt_utc = datetime.strptime(original_timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            # Convert to local timezone
            local_dt = original_dt_utc.astimezone()
            local_timestamp_str = local_dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')  # Format with AM/PM and timezone name
        except ValueError:
            print(f"Warning: Could not parse original timestamp '{original_timestamp}'. Displaying as is.", file=sys.stderr)
            local_timestamp_str = "N/A"

        # Display original info
        print(f"--- Replaying Log ID: {log_id} (Location: {location_name}) ---")
        print(f"Original Timestamp (Stored): {original_timestamp}")
        print(f"Original Timestamp (Local): {local_timestamp_str}")
        print(f"Original Model: {original_model}")
        print(f"Original Description: {original_output.get('description', 'N/A')}")

        # Optionally print the original context
        if show_context:
            print("\n--- Original Weather Context ---")
            if isinstance(original_context, str):
                print("LLM Context (formatted text):")
                print(original_context)
            else:
                # Legacy format
                print("Current Conditions:")
                print(json.dumps(original_context.get('current', {}), indent=2, ensure_ascii=False))
                print("\nForecast Data:")
                print(json.dumps(original_context.get('forecast', {}), indent=2, ensure_ascii=False))
            print("-" * 20)
        else:
            print("-" * 20)  # Print separator even if context isn't shown

        # Determine the prompt and model for the replay
        prompt_to_use = original_prompt
        prompt_source_message = "Using ORIGINAL prompt from log."
        if prompt:
            prompt_path = Path(prompt)
            if prompt_path.is_file():
                try:
                    prompt_to_use = prompt_path.read_text()
                    prompt_source_message = f"Using NEW prompt loaded from file: {prompt}"
                except Exception as e:
                    print(f"Warning: Could not read prompt file '{prompt}'. Using original prompt. Error: {e}", file=sys.stderr)
                    prompt_to_use = original_prompt  # Fallback to original on read error
                    prompt_source_message = "Error reading prompt file. Using ORIGINAL prompt from log."
            else:
                # Use the provided string directly if it's not a file
                prompt_to_use = prompt
                prompt_source_message = "Using NEW prompt text provided via --prompt option."

        print(prompt_source_message)  # Print how the prompt was determined

        model_to_use = new_model if new_model else original_model
        print(f"Using model for replay: {model_to_use}")
        print("-" * 20)

        # Call the API using our refactored module
        new_output = call_llm_api(original_context, prompt_to_use, api_key=LLM_API_KEY, model=model_to_use)

        # Display results
        print("\n--- Replay Results ---")
        print(f"Model Used: {model_to_use}")
        print(f"\nNew LLM Output (JSON):\n{json.dumps(new_output, indent=2, ensure_ascii=False)}")

    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during replay: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    load_dotenv()  # Load environment variables
    main()