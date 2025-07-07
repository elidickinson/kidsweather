#!/usr/bin/env python3
"""
Weather processing module for Kids Weather application.

This module handles the core weather data processing, transforming
raw API data into a format suitable for LLM processing and display.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import (
    WEATHER_API_KEY, DEFAULT_PROMPT_FILE,
    LLM_MODEL, LLM_API_KEY
)
from utils import (
    format_alert_time,
    load_system_prompt, log_llm_interaction,
    load_weather_data
)
from api_client import (
    fetch_weather_data, fetch_yesterday_weather, call_llm_api
)

# --- Weather Data Processing ---

def format_time(timestamp_utc, timezone_offset_seconds=0):
    """Convert UTC timestamp to local time string."""
    if timestamp_utc is None:
        return "N/A"
    utc_dt = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc)
    local_dt = utc_dt + timedelta(seconds=timezone_offset_seconds)
    return local_dt.strftime('%I:%M %p')

def get_day_name(timestamp_utc, timezone_offset_seconds=0):
    """Get day name from UTC timestamp."""
    if timestamp_utc is None:
        return "N/A"
    local_dt = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc) + timedelta(seconds=timezone_offset_seconds)
    return local_dt.strftime('%A')

def describe_wind(wind_speed, wind_gust=None):
    """Create wind description."""
    if wind_speed is None:
        return "Wind data not available."
    elif wind_speed >= 25:
        desc = f"Very windy, with speeds around {wind_speed:.0f} mph."
    elif wind_speed >= 15:
        desc = f"Windy, with speeds around {wind_speed:.0f} mph."
    elif wind_speed >= 5:
        desc = f"Light winds around {wind_speed:.0f} mph."
    elif wind_speed > 1:
        desc = f"Mostly calm."
    else:
        desc = "No wind."

    if wind_gust and wind_gust > wind_speed * 1.5 and wind_gust > 5:
        desc += f" Gusts up to {wind_gust:.0f} mph."
    return desc

def describe_uvi(uvi_value):
    """Describe UV index."""
    if uvi_value is None:
        return "N/A"
    uvi = float(uvi_value)
    if uvi < 4: return f"{uvi:.1f} (low)"
    if uvi < 6: return f"{uvi:.1f} (mild)"
    if uvi < 8: return f"{uvi:.1f} - You should mention sunscreen"
    if uvi < 11: return f"{uvi:.1f} - You must mention sunscreen!"
    return f"{uvi:.1f} Very Important: You must mention sunscreen and a hat!"

def format_weather_for_llm(api_data, yesterday_data=None):
    """
    Convert raw weather API data directly to text format for LLM.
    """
    if not isinstance(api_data, dict):
        return "Error: Invalid weather data format."

    lines = []
    tz_offset = api_data.get("timezone_offset", 0)

    # Current date and time at location
    current_time = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
    # Round to nearest quarter hour to improve cache reuse
    rounded_minute = (current_time.minute // 15) * 15
    rounded_time = current_time.replace(minute=rounded_minute, second=0, microsecond=0)
    lines.append(f"Current Date and Time: {rounded_time.strftime('%A, %B %d, %Y at %I:%M %p')}")

    # Yesterday's weather summary if available
    if yesterday_data:
        lines.append(f"\nYESTERDAY'S WEATHER ({yesterday_data['date']}):")
        avg_temp = f"{round(yesterday_data['avg_temp'])}°F" if yesterday_data['avg_temp'] else "N/A"
        feels_like = f"{round(yesterday_data['avg_feels_like'])}°F" if yesterday_data['avg_feels_like'] else "N/A"
        high_temp = f"{round(yesterday_data['high_temp'])}°F" if yesterday_data['high_temp'] else "N/A"
        low_temp = f"{round(yesterday_data['low_temp'])}°F" if yesterday_data['low_temp'] else "N/A"
        lines.append(f"  Average Temperature: {avg_temp} (felt like {feels_like})")
        lines.append(f"  High: {high_temp}, Low: {low_temp}")
        lines.append(f"  Main Condition: {yesterday_data['main_condition']}")

    # Current conditions
    current = api_data.get("current", {})
    lines.append("\nTODAY'S FORECAST:")

    # Current weather
    current_desc = current.get("weather", [{}])[0].get("description", "Not available")
    current_weather_line = f"  Right Now: {current_desc} at {round(current.get('temp', 0))}°F"
    # Include "feels like" if its different enough from actual temp
    if current.get('feels_like') and (abs(round(current.get('temp', 0)) - round(current.get('feels_like'))) > 5):
        current_weather_line += f"  (feels like {round(current.get('feels_like'))}°F)."
    lines.append(current_weather_line)

    # Current precipitation
    rain_1h = current.get("rain", {}).get("1h")
    snow_1h = current.get("snow", {}).get("1h")
    if rain_1h and rain_1h > 0:
        lines.append(f"  Current Precipitation: Currently raining ({rain_1h} mm/hr).")
    elif snow_1h and snow_1h > 0:
        lines.append(f"  Current Precipitation: Currently snowing ({snow_1h} mm/hr).")
    else:
        lines.append("  Current Precipitation: none.")

    # Current conditions
    lines.append(f"  Current Wind: {describe_wind(current.get('wind_speed'), current.get('wind_gust'))}")
    lines.append(f"  Current UV Index: {describe_uvi(current.get('uvi'))}")
    lines.append(f"  Sunrise: {format_time(current.get('sunrise'), tz_offset)}, "
                f"Sunset: {format_time(current.get('sunset'), tz_offset)}.")

    # Today's daily forecast
    daily = api_data.get("daily", [])
    if daily:
        today = daily[0]
        lines.append(f"\n  Overall for Today ({get_day_name(today.get('dt'), tz_offset)}):")
        lines.append(f"  Summary: {today.get('summary', 'No summary available.')}")
        high_temp = f"{round(today.get('temp', {}).get('max'))}°F" if today.get('temp', {}).get('max') else "N/A"
        low_temp = f"{round(today.get('temp', {}).get('min'))}°F" if today.get('temp', {}).get('min') else "N/A"
        lines.append(f"  High: {high_temp}, Low for tonight: {low_temp}.")

        # Precipitation forecast
        pop = today.get("pop", 0)
        if pop < 0.1:
            precip_desc = "Low chance of precipitation."
        else:
            precip_desc = f"{int(pop * 100)}% chance of precipitation"
            rain_mm = today.get("rain")
            snow_mm = today.get("snow")
            if rain_mm and rain_mm > 0:
                precip_desc += f" ({rain_mm}mm rain)"
            if snow_mm and snow_mm > 0:
                precip_desc += f" ({snow_mm}mm snow)"
            precip_desc += "."
        lines.append(f"  Precipitation: {precip_desc}")

        lines.append(f"  Day Wind: {describe_wind(today.get('wind_speed'), today.get('wind_gust'))}")

    # Hourly forecast for next 8 hours
    hourly = api_data.get("hourly", [])
    if hourly:
        lines.append("\nNEXT 8 HOURS:")
        for hour_data in hourly[:8]:  # Next 8 hours
            hour_time = format_time(hour_data.get('dt'), tz_offset)
            temp = f"{round(hour_data.get('temp'))}°F" if hour_data.get('temp') else "N/A"
            weather_desc = hour_data.get('weather', [{}])[0].get('description', 'N/A')

            # Build hourly line
            hour_line = f"  {hour_time}: {weather_desc} at {temp}"

            # mention UVI if relevant
            uvi = hour_data.get('uvi', 0)
            if float(uvi) >= 3:
                hour_line += f" ({describe_uvi(uvi)})"

            # Add precipitation if present
            pop = hour_data.get('pop', 0)
            if pop > 0:
                rain_1h = hour_data.get('rain', {}).get('1h', 0)
                snow_1h = hour_data.get('snow', {}).get('1h', 0)
                precip_parts = [f"{int(pop * 100)}% chance precip"]
                if rain_1h > 0:
                    precip_parts.append(f"{rain_1h}mm rain")
                if snow_1h > 0:
                    precip_parts.append(f"{snow_1h}mm snow")
                hour_line += f" ({', '.join(precip_parts)})"

            lines.append(hour_line)

    # Next few days
    lines.append("\nNEXT FEW DAYS (for daily_forecasts - use these exact day names):")
    if len(daily) > 1:
        for day in daily[1:5]:  # Next 4 days after today
            lines.append(f"\n  {get_day_name(day.get('dt'), tz_offset)}:")
            lines.append(f"    Summary: {day.get('summary', 'No summary available.')}")
            high_temp = f"{round(day.get('temp', {}).get('max'))}°F" if day.get('temp', {}).get('max') else "N/A"
            low_temp = f"{round(day.get('temp', {}).get('min'))}°F" if day.get('temp', {}).get('min') else "N/A"
            lines.append(f"    High: {high_temp}, Low: {low_temp}.")

            pop = day.get("pop", 0)
            if pop < 0.1:
                precip_desc = "Low chance of precipitation."
            else:
                precip_desc = f"{int(pop * 100)}% chance of precipitation"
                rain_mm = day.get("rain")
                snow_mm = day.get("snow")
                if rain_mm and rain_mm > 0:
                    precip_desc += f" ({rain_mm}mm rain)"
                if snow_mm and snow_mm > 0:
                    precip_desc += f" ({snow_mm}mm snow)"
                precip_desc += "."
            lines.append(f"    Precipitation: {precip_desc}")
            lines.append(f"    Wind: {describe_wind(day.get('wind_speed'), day.get('wind_gust'))}")
    else:
        lines.append("  No extended forecast available.")

    return "\n".join(lines)

def extract_display_data(weather_data):
    """
    Extract just the data needed for display from raw weather data.
    This replaces the old extract_weather_context function.
    """
    current = weather_data['current']
    timezone_offset = weather_data.get('timezone_offset', 0)

    # Get today's high/low from daily forecast
    daily_today = weather_data['daily'][0] if weather_data.get('daily') else None
    today_high = daily_today['temp']['max'] if daily_today else current['temp']
    today_low = daily_today['temp']['min'] if daily_today else current['temp']

    # Format alerts
    alerts = []
    if 'alerts' in weather_data:
        for alert in weather_data['alerts']:
            alerts.append({
                'event': alert['event'],
                'start': format_alert_time(alert['start'], timezone_offset),
                'end': format_alert_time(alert['end'], timezone_offset)
            })

    # Get daily forecast for template
    daily_forecast_raw = []
    for day in weather_data.get('daily', [])[0:5]:
        daily_forecast_raw.append({
            'day': datetime.fromtimestamp(day['dt']).strftime('%A'),
            'high': round(day['temp']['max']),
            'low': round(day['temp']['min']),
            'conditions': day['weather'][0]['description'],
            'precip_prob': day.get('pop', 0) * 100,
            'icon': day['weather'][0]['icon']
        })

    return {
        'current': {
            'temp': round(current['temp']),
            'feels_like': round(current['feels_like']),
            'conditions': current['weather'][0]['description'],
            'icon': current['weather'][0]['icon']
        },
        'forecast': {
            'high_temp': round(today_high),
            'low_temp': round(today_low)
        },
        'alerts': alerts,
        'daily_forecast_raw': daily_forecast_raw,
        'location': ''
    }

def generate_weather_description(weather_data, api_key=None,
                               log_interaction=False, source='unknown',
                               model=LLM_MODEL, prompt_override=None, include_yesterday=True):
    """
    Generate kid-friendly weather description using LLM.

    Args:
        weather_data: Raw weather data from API
        api_key: DeepSeek API key (defaults to env var)
        log_interaction: Whether to log this interaction to database
        source: Source identifier for logging (flask, script, etc.)
        model: LLM model name
        prompt_override: Path to custom prompt file or prompt text
        include_yesterday: Whether to include yesterday's weather data

    Returns:
        dict: Generated weather report
    """
    # Use provided API key or get from config
    api_key = api_key or LLM_API_KEY
    if not api_key:
        raise ValueError("Missing LLM API key")

    # Determine which prompt to use
    system_prompt = None
    prompt_source_message = ""

    if prompt_override:
        prompt_path = Path(prompt_override)
        if prompt_path.is_file():
            system_prompt = prompt_path.read_text()
            prompt_source_message = f"Using prompt loaded from file: {prompt_override}"
        else:
            system_prompt = prompt_override
            prompt_source_message = "Using prompt text provided via --prompt option."

    # If no override was provided or file read failed, load the default
    if system_prompt is None:
        system_prompt = load_system_prompt()
        prompt_source_message = f"Using default prompt from: {DEFAULT_PROMPT_FILE}"

    print(prompt_source_message)

    # Fetch yesterday's weather if requested and coordinates are available
    yesterday_data = None
    if include_yesterday and 'lat' in weather_data and 'lon' in weather_data:
        yesterday_data = fetch_yesterday_weather(
            weather_data['lat'],
            weather_data['lon'],
            WEATHER_API_KEY
        )
        if yesterday_data:
            print(f"Successfully fetched yesterday's weather: {yesterday_data['date']}")

    # Format weather data as text for LLM
    llm_context = format_weather_for_llm(weather_data, yesterday_data)
    print("Using text-formatted weather context for LLM")

    # Call LLM API
    result = call_llm_api(llm_context, system_prompt, api_key=api_key, model=model)

    # Log the interaction if requested
    if log_interaction:
        description_text = result.get('description', '')

        # Create a dict for logging that includes the raw response
        log_output = {
            'raw_llm_response': result.get('_raw_llm_response', ''),
            'parsed_result': {k: v for k, v in result.items() if k != '_raw_llm_response'}
        }

        log_llm_interaction(
            weather_input=weather_data,  # Log the raw data
            system_prompt=system_prompt,
            model_used=model,
            llm_output_raw=log_output,
            description=description_text,
            source=source,
            llm_context=llm_context  # Add the formatted context
        )

    return result

def get_weather_report(lat, lon, mock_file=None,
                     log_interaction=False, source='unknown', prompt_override=None,
                     include_yesterday=True):
    """
    Main function to get complete weather report.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        mock_file: Path to mock data file for testing
        log_interaction: Whether to log LLM interaction
        source: Source identifier for logging
        prompt_override: Path to custom prompt file or prompt text
        include_yesterday: Whether to include yesterday's weather data

    Returns:
        dict: Complete weather report ready for display
    """
    weather_data = {}

    if mock_file:
        # Load mock data from file
        weather_data = load_weather_data(mock_file)
    else:
        # Get current conditions from OpenWeatherMap
        if not WEATHER_API_KEY:
            raise ValueError("Missing WEATHER_API_KEY in environment variables")

        weather_data.update(fetch_weather_data(lat, lon, WEATHER_API_KEY))

    # Generate description with LLM
    description = generate_weather_description(
        weather_data,
        log_interaction=log_interaction,
        source=source,
        prompt_override=prompt_override,
        include_yesterday=include_yesterday
    )

    # Extract display data
    display_data = extract_display_data(weather_data)

    # Return formatted response for display
    return {
        'description': description.get('description', ''),
        'daily_forecasts_llm': description.get('daily_forecasts', []),  # LLM-generated text
        'temperature': display_data['current']['temp'],
        'feels_like': display_data['current']['feels_like'],
        'conditions': display_data['current']['conditions'],
        'high_temp': display_data['forecast']['high_temp'],
        'low_temp': display_data['forecast']['low_temp'],
        'icon_url': f"http://openweathermap.org/img/wn/{display_data['current']['icon']}@4x.png",
        'alerts': [f"{alert['event']} ({alert['start']} to {alert['end']})" for alert in display_data['alerts']],
        'last_updated': datetime.fromtimestamp(weather_data['current']['dt']).strftime('%A, %B %-d at %-I:%M %p'),
        'daily_forecast_raw': display_data['daily_forecast_raw']  # Raw API data for template
    }
