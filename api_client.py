#!/usr/bin/env python3
"""
API client module for weather data fetching and LLM interactions.

This module handles all external API calls to weather services and language models,
with built-in caching, error handling, and standardized response formats.
"""
import json
import sys
import requests
import hashlib
import re
from datetime import datetime, timedelta

from config import (
    WEATHER_API_URL, WEATHER_TIMEMACHINE_API_URL, API_CACHE_TIME, WEATHER_UNITS,
    LLM_API_URL, LLM_MODEL, LLM_API_KEY, LLM_SUPPORTS_JSON_MODE,
    FALLBACK_LLM_API_URL, FALLBACK_LLM_MODEL, FALLBACK_LLM_API_KEY,
    FALLBACK_LLM_SUPPORTS_JSON_MODE, FALLBACK_LLM_ENABLED
)
from utils import cache, get_cache_key

def fetch_weather_data(lat, lon, api_key):
    """
    Fetch weather data from OpenWeatherMap with caching.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        api_key: OpenWeatherMap API key

    Returns:
        dict: Weather data response
    """
    cache_key = get_cache_key("weather_api", lat, lon)

    # Try to get cached response
    if cache_key in cache:
        print(f"Cache hit for weather API: {cache_key}")
        return cache.get(cache_key)

    print(f"Cache miss for weather API: {cache_key}")

    params = {
        "lat": lat,
        "lon": lon,
        "units": WEATHER_UNITS,
        "exclude": "minutely",  # Keep hourly and daily forecasts
        "appid": api_key
    }

    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Cache the response with expiration
        cache.set(cache_key, data, expire=API_CACHE_TIME)
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            print(f"Response body: {e.response.text}", file=sys.stderr)
        raise


def fetch_yesterday_weather(lat, lon, api_key):
    """
    Fetch yesterday's weather data from OpenWeatherMap One Call Timemachine API.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        api_key: OpenWeatherMap API key

    Returns:
        dict: Yesterday's weather data with averaged values
    """
    # Calculate yesterday at noon (middle of the day)
    now = datetime.now()
    yesterday_noon = now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)

    # Convert to Unix timestamp
    yesterday_timestamp = int(yesterday_noon.timestamp())

    cache_key = get_cache_key("weather_timemachine", lat, lon, yesterday_timestamp)

    # Try to get cached response
    if cache_key in cache:
        print(f"Cache hit for weather timemachine API: {cache_key}")
        return cache.get(cache_key)

    print(f"Cache miss for weather timemachine API: {cache_key}")

    params = {
        "lat": lat,
        "lon": lon,
        "dt": yesterday_timestamp,
        "units": WEATHER_UNITS,
        "appid": api_key
    }

    try:
        response = requests.get(WEATHER_TIMEMACHINE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Process timemachine data to get summary
        if 'data' in data and data['data']:
            # The timemachine API returns a single data point for the specified timestamp
            # To get a full day's data, we'd need multiple API calls
            # For now, we'll use the single data point as representative of yesterday

            weather_data = data['data'][0]

            # Get weather condition
            main_condition = "Unknown"
            if 'weather' in weather_data and weather_data['weather']:
                main_condition = weather_data['weather'][0]['main']

            # Get the date from the data
            yesterday_date = datetime.fromtimestamp(weather_data['dt']).strftime("%A, %B %d")

            yesterday_summary = {
                "date": yesterday_date,
                "avg_temp": round(weather_data['temp'], 1) if 'temp' in weather_data else None,
                "high_temp": round(weather_data['temp'], 1) if 'temp' in weather_data else None,  # Using same temp since we only have one data point
                "low_temp": round(weather_data['temp'], 1) if 'temp' in weather_data else None,
                "avg_feels_like": round(weather_data['feels_like'], 1) if 'feels_like' in weather_data else None,
                "main_condition": main_condition,
                "conditions_breakdown": {main_condition: 1}  # Single data point
            }

            # Cache the processed result
            cache.set(cache_key, yesterday_summary, expire=API_CACHE_TIME * 6)  # Cache for 1 hour
            return yesterday_summary

        print("No historical data available in response", file=sys.stderr)
        return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical weather data: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            print(f"Response body: {e.response.text}", file=sys.stderr)
        # Return None instead of raising to allow graceful degradation
        return None


def _call_single_llm(context, system_prompt, api_url, api_key, model, supports_json_mode):
    """
    Internal function to call a single LLM endpoint.

    Args:
        context: Dictionary with weather context data or text string
        system_prompt: System prompt text
        api_url: LLM API endpoint URL
        api_key: API key for the language model
        model: Model identifier string
        supports_json_mode: Whether the LLM supports JSON response format

    Returns:
        dict: Parsed JSON response from the language model
    """
    print(f"Calling LLM API (Model: {model}) at {api_url}")

    # Prepare request payload
    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context if isinstance(context, str) else json.dumps(context)}
        ],
        "stream": False
    }

    # Only add response_format if the provider supports it
    if supports_json_mode:
        request_payload["response_format"] = {"type": "json_object"}

    # Debug logging
    print(f"Request URL: {api_url}")

    response = requests.post(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=request_payload,
        timeout=200
    )
    response.raise_for_status()

    response_data = response.json()
    if 'choices' not in response_data or not response_data['choices']:
        raise ValueError("No choices in LLM response")

    raw_content = response_data['choices'][0]['message']['content']

    print(raw_content)

    # Process content for JSON parsing
    content = raw_content.strip()

    # Strip <think>...</think> tags if present (common with some local LLMs)
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # Handle OpenRouter's temperature: prefix
    if content.startswith('temperature:'):
        content = content.split('temperature:')[1].strip()

    # Handle JSON code blocks
    if content.startswith('```json'):
        content = content[7:]  # Remove ```json
    elif content.startswith('```'):
        content = content[3:]  # Remove ```

    if content.endswith('```'):
        content = content[:-3]  # Remove ```

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM JSON response. Content: {content[:200]}...", file=sys.stderr)
        raise ValueError(f"LLM did not return valid JSON: {e}")

    # Return both raw and parsed content
    return {
        'raw_response': raw_content,
        'parsed_result': result
    }


def call_llm_api(context, system_prompt, api_key=None, model=None):
    """
    Call the language model API with context and prompt, with automatic fallback.

    Args:
        context: Dictionary with weather context data or text string
        system_prompt: System prompt text
        api_key: API key for the language model
        model: Model identifier string

    Returns:
        dict: Parsed JSON response from the language model
    """
    # Use defaults if not provided
    api_key = api_key or LLM_API_KEY
    model = model or LLM_MODEL

    # JSON format instructions
#     json_instructions = """\n\nIMPORTANT: You MUST respond with ONLY valid JSON, no other text before or after."""
# Your response must be a JSON object with this exact structure:
# {
#   "description": "A kid-friendly weather description",
#   "daily_forecasts": ["Day 1 forecast", "Day 2 forecast", "Day 3 forecast", "Day 4 forecast"],
#   "temperature": 72,
#   "feels_like": 70,
#   "conditions": "clear sky",
#   "high_temp": 78,
#   "low_temp": 65,
#   "icon_url": "http://openweathermap.org/img/wn/01d@4x.png",
#   "alerts": [],
#   "last_updated": "Monday, December 4 at 3:30 PM"
# }"""
    print(context)
    # Create a cache key based on context, prompt, and model
    prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
    cache_key = get_cache_key("llm", context, prompt_hash, model)

    # Check cache first
    if cache_key in cache:
        print(f"Cache hit for LLM: {cache_key}")
        return cache.get(cache_key)

    print(f"Cache miss for LLM: {cache_key}")

    # Try primary LLM first
    try:
        llm_response = _call_single_llm(
            context=context,
            system_prompt=system_prompt,
            api_url=LLM_API_URL,
            api_key=api_key,
            model=model,
            supports_json_mode=LLM_SUPPORTS_JSON_MODE
        )

        # For backward compatibility, cache and return the parsed result
        # but add the raw response to it
        result = llm_response['parsed_result']
        result['_raw_llm_response'] = llm_response['raw_response']

        # Cache successful result
        cache.set(cache_key, result, expire=API_CACHE_TIME)
        return result

    except Exception as e:
        print(f"Primary LLM failed: {e}", file=sys.stderr)

        # Try fallback if available
        if FALLBACK_LLM_ENABLED:
            print(f"Attempting fallback LLM (Model: {FALLBACK_LLM_MODEL})", file=sys.stderr)

            try:
                llm_response = _call_single_llm(
                    context=context,
                    system_prompt=system_prompt,
                    api_url=FALLBACK_LLM_API_URL,
                    api_key=FALLBACK_LLM_API_KEY,
                    model=FALLBACK_LLM_MODEL,
                    supports_json_mode=FALLBACK_LLM_SUPPORTS_JSON_MODE
                )

                print(f"Fallback LLM succeeded", file=sys.stderr)

                # For backward compatibility, cache and return the parsed result
                # but add the raw response to it
                result = llm_response['parsed_result']
                result['_raw_llm_response'] = llm_response['raw_response']

                # Cache successful result
                cache.set(cache_key, result, expire=API_CACHE_TIME)
                return result

            except Exception as fallback_e:
                print(f"Fallback LLM also failed: {fallback_e}", file=sys.stderr)
                # Re-raise the original error with additional context
                raise RuntimeError(f"Both primary and fallback LLMs failed. Primary error: {e}. Fallback error: {fallback_e}")
        else:
            # No fallback configured, re-raise the original error
            raise
