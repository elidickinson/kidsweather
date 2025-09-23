#!/usr/bin/env python3
"""Command-line interface for Kids Weather application."""
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
#     "python-dotenv",
#     "click",
#     "diskcache",
# ]
# ///

import json

import click
from dotenv import load_dotenv

from settings import load_settings
from utils import load_weather_data, save_weather_data
from weather_service import build_default_service


@click.command()
@click.option('--lat', type=float, help='Latitude')
@click.option('--lon', type=float, help='Longitude')
@click.option('--save', type=str, help='Save weather data to test file (without .json suffix)')
@click.option('--load', type=str, help='Load weather data from test file (without .json suffix)')
@click.option('--save-json', type=str, help='Save output to JSON file (without .json suffix)')
@click.option('--save-txt', type=str, help='Save description to text file (without .txt suffix)')
@click.option('--log-interactions', is_flag=True, default=False, help='Log LLM interaction details to the database.')
@click.option('--prompt', type=str, help='Custom system prompt text or path to a prompt file.')
@click.option('--model', type=str, help='Override the LLM model for this invocation.')
@click.option('--verbose', is_flag=True, default=False, help='Show progress details and the LLM context dump.')
def main(lat, lon, save, load, save_json, save_txt, log_interactions, prompt, model, verbose):
    """Generate a kid-friendly weather report."""

    if verbose:
        click.echo('Loading settings...')
    load_settings()  # Ensure environment variables are available.
    if verbose:
        click.echo('Initialising weather report service...')
    service = build_default_service()

    weather_payload = None
    if load:
        if verbose:
            click.echo(f"Loading weather data from saved fixture: {load}.json")
        weather_payload = load_weather_data(f"{load}.json")
        if verbose:
            click.echo('Generating report from saved data via LLM...')
        report = service.build_report(
            latitude=None,
            longitude=None,
            weather_data_override=weather_payload,
            log_interaction=log_interactions,
            source='script',
            prompt_override=prompt,
            model_override=model,
        )
    else:
        if lat is None or lon is None:
            raise click.UsageError("Latitude and longitude are required when not loading from file")

        if save:
            if verbose:
                click.echo('Fetching live weather data before saving snapshot...')
            weather_payload = service.weather_client.fetch_current(lat, lon)
            save_path = save_weather_data(weather_payload, f"{save}.json")
            click.echo(f"Saved weather data to: {save_path}")

        if verbose:
            message = 'Fetching live weather data and requesting LLM summary...'
            if weather_payload is not None:
                message = 'Generating report from saved live data via LLM...'
            click.echo(message)
        report = service.build_report(
            latitude=lat,
            longitude=lon,
            weather_data_override=weather_payload,
            log_interaction=log_interactions,
            source='script',
            prompt_override=prompt,
            model_override=model,
        )

    if verbose:
        prompt_text = (service.last_system_prompt or '').strip()
        context_text = (service.last_llm_context or '').strip()
        click.echo("\nSystem Prompt:\n" + (prompt_text or '[prompt unavailable]'))
        click.echo("\nLLM Context:\n" + (context_text or '[context unavailable]'))
        click.echo("\n" + '-' * 60)

    click.echo("\nWeather Report:")
    click.echo(f"\nDescription: {report['description']}")
    click.echo(f"\nCurrent Temperature: {report['temperature']}°F (Feels like: {report['feels_like']}°F)")
    click.echo(f"Conditions: {report['conditions']}")
    click.echo(f"Today's Range: High {report['high_temp']}°F / Low {report['low_temp']}°F")

    daily_forecasts = report.get('daily_forecasts_llm', {})
    if isinstance(daily_forecasts, dict):
        for day, forecast in daily_forecasts.items():
            click.echo(f"{day}: {forecast}")
    elif isinstance(daily_forecasts, list):
        for idx, forecast in enumerate(daily_forecasts, start=1):
            click.echo(f"Day {idx}: {forecast}")

    if report.get('alerts'):
        click.echo(f"\nAlerts: {', '.join(report['alerts'])}")

    if save_json:
        with open(f"{save_json}.json", 'w') as fh:
            json.dump(report, fh, indent=2)
        click.echo(f"\nSaved full output to: {save_json}.json")

    if save_txt:
        with open(f"{save_txt}.txt", 'w') as fh:
            fh.write(report['description'])
        click.echo(f"\nSaved description to: {save_txt}.txt")



if __name__ == '__main__':
    load_dotenv()
    main()
