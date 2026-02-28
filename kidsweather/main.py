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

from typing import Optional

import json
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv

from .core.settings import load_settings
from .core.service import build_default_service
from .formatting.html import render_to_file


def save_weather_data(data: dict, filename: Optional[str] = None, *, directory: Optional[Path] = None) -> Path:
    """Persist raw weather data to disk for later replay or testing."""
    settings = load_settings()
    target_dir = directory or settings.test_data_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weather_{timestamp}.json"

    path = target_dir / filename
    path.write_text(json.dumps(data, indent=2))
    return path


def load_weather_data(filename: str, *, directory: Optional[Path] = None) -> dict:
    """Load weather data previously saved for deterministic runs."""
    settings = load_settings()
    target_dir = directory or settings.test_data_dir
    path = target_dir / filename
    return json.loads(path.read_text())


@click.command()
@click.option('--lat', type=float, help='Latitude')
@click.option('--lon', type=float, help='Longitude')
@click.option('--save', type=str, help='Save weather data to test file (without .json suffix)')
@click.option('--load', type=str, help='Load weather data from test file (without .json suffix)')
@click.option('--render', type=str, help='Render HTML output to specified file')
@click.option('--log-interactions', is_flag=True, default=False, help='Log LLM interaction details to the database.')
@click.option('--prompt', type=str, help='Custom system prompt text or path to a prompt file.')
@click.option('--model', type=str, help='Override the LLM model for this invocation.')
@click.option('--verbose', is_flag=True, default=False, help='Show progress details and the LLM context dump.')
@click.option('--no-refresh-weather', is_flag=True, default=False, help='Force use of cached weather API data.')
@click.option('--no-refresh-llm', is_flag=True, default=False, help='Force use of cached LLM response (implies --no-refresh-weather).')
@click.option('--force-refresh-llm', is_flag=True, default=False, help='Force fresh LLM response (overrides --no-refresh-llm).')
def main(lat, lon, save, load, render, log_interactions, prompt, model, verbose, no_refresh_weather, no_refresh_llm, force_refresh_llm):
    """Generate a kid-friendly weather report."""

    if verbose:
        click.echo('Loading settings...')
    
    # --no-refresh-llm implies --no-refresh-weather
    if no_refresh_llm:
        no_refresh_weather = True
    
    # --force-refresh-llm overrides --no-refresh-llm
    if force_refresh_llm and no_refresh_llm:
        click.echo("Warning: --force-refresh-llm overrides --no-refresh-llm", err=True)
        no_refresh_llm = False

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
            no_refresh_weather=no_refresh_weather,
            no_refresh_llm=no_refresh_llm,
            force_refresh_llm=force_refresh_llm,
        )
    else:
        if lat is None or lon is None:
            raise click.UsageError("Latitude and longitude are required when not loading from file")

        if save:
            if verbose:
                msg = 'Using cached weather data for snapshot...' if no_refresh_weather else \
                      'Fetching live weather data before saving snapshot...'
                click.echo(msg)
            weather_payload = service._fetch_weather_data(lat, lon, no_refresh_weather)
            save_path = save_weather_data(weather_payload, f"{save}.json")
            click.echo(f"Saved weather data to: {save_path}")

        report = service.build_report(
            latitude=lat,
            longitude=lon,
            weather_data_override=weather_payload,
            log_interaction=log_interactions,
            source='script',
            prompt_override=prompt,
            model_override=model,
            no_refresh_weather=no_refresh_weather,
            no_refresh_llm=no_refresh_llm,
            force_refresh_llm=force_refresh_llm,
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

    if report.get('alerts'):
        click.echo(f"\nAlerts: {', '.join(report['alerts'])}")

    if render:
        render_to_file(report, render)
        click.echo(f"\nRendered HTML to: {render}")


if __name__ == '__main__':
    load_dotenv()
    main()
