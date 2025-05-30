#!/usr/bin/env python3
"""
Command-line interface for Kids Weather application.

This script provides command-line functionality for generating
kid-friendly weather reports.
"""
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
#     "python-dotenv",
#     "click",
#     "diskcache",
# ]
# ///

import sys
import json
import click
from dotenv import load_dotenv

from utils import save_weather_data, init_llm_log_db
from weather_processor import get_weather_report

@click.command()
@click.option('--lat', type=float, help='Latitude')
@click.option('--lon', type=float, help='Longitude')
@click.option('--save', type=str, help='Save weather data to test file (without .json suffix)')
@click.option('--load', type=str, help='Load weather data from test file (without .json suffix)')
@click.option('--save-json', type=str, help='Save output to JSON file (without .json suffix)')
@click.option('--save-txt', type=str, help='Save description to text file (without .txt suffix)')
@click.option('--log-interactions', is_flag=True, default=False, help='Log LLM interaction details to the database.')
@click.option('--prompt', type=str, help='Custom system prompt text or path to a prompt file.')
def main(lat, lon, save, load, save_json, save_txt, log_interactions, prompt):
    """Generate a kid-friendly weather report."""
    try:
        source = 'script'  # Define source for script execution

        if load:
            # Use mock data from file
            result = get_weather_report(
                None, None,
                mock_file=f"{load}.json",
                log_interaction=log_interactions,
                source=source,
                prompt_override=prompt
            )
        else:
            if not lat or not lon:
                raise click.UsageError("Latitude and longitude are required when not loading from file")

            # Save raw weather data if requested
            if save:
                from api_client import fetch_weather_data
                from config import WEATHER_API_KEY

                if not WEATHER_API_KEY:
                    raise ValueError("Missing WEATHER_API_KEY in environment variables")

                raw_weather_data = fetch_weather_data(lat, lon, WEATHER_API_KEY)
                filename = f"{save}.json"
                save_path = save_weather_data(raw_weather_data, filename)
                print(f"Saved weather data to: {save_path}")

            # Get complete weather report
            result = get_weather_report(
                lat, lon,
                log_interaction=log_interactions,
                source=source,
                prompt_override=prompt
            )

        # Print results to terminal
        print(f"\nWeather Report:")
        print(f"\nDescription: {result['description']}")
        print(f"\nCurrent Temperature: {result['temperature']}°F (Feels like: {result['feels_like']}°F)")
        print(f"Conditions: {result['conditions']}")
        print(f"Today's Range: High {result['high_temp']}°F / Low {result['low_temp']}°F")

        for day, forecast in result['daily_forecasts_llm'].items():
            print(f"{day}: {forecast}")

        if result['alerts']:
            print(f"\nAlerts: {', '.join(result['alerts'])}")

        # Save output files if requested
        if save_json:
            with open(f"{save_json}.json", 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nSaved full output to: {save_json}.json")

        if save_txt:
            with open(f"{save_txt}.txt", 'w') as f:
                f.write(result['description'])
            print(f"\nSaved description to: {save_txt}.txt")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    load_dotenv()
    init_llm_log_db()  # Ensure LLM log DB is initialized
    main()
