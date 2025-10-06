#!/usr/bin/env python3
"""LLM interaction replay utility for Kids Weather."""
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
#     "python-dotenv",
#     "click",
# ]
# ///

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv

from llm_client import LLMClient
from settings import load_settings


@click.command()
@click.option('--log-id', type=int, required=True, help='The ID from the llm_interactions table to replay.')
@click.option('--prompt', type=str, help='New system prompt text or path to a prompt file.')
@click.option('--new-model', type=str, help='New model name to use (e.g., gpt-3.5-turbo).')
@click.option('--show-context', is_flag=True, default=False, help='Print the original weather context data.')
def main(log_id, prompt, new_model, show_context):
    """Replays a logged LLM interaction, optionally with a new prompt or model."""

    settings = load_settings()
    try:
        settings.require_llm_configured()
    except ValueError as e:
        raise click.ClickException(str(e))

    db_path = settings.llm_log_db
    if not db_path.exists():
        raise click.ClickException(
            f"Log database file not found: {db_path}. Run the main application to generate logs."
        )

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, location_name, weather_input, llm_context,
                   system_prompt, model_used, llm_output
            FROM llm_interactions
            WHERE id = ?
            """,
            (log_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise click.ClickException(f"No log entry found with ID {log_id}")

    (timestamp_str, location_name, weather_input_json, llm_context, original_prompt, original_model, llm_output_json) = row

    try:
        weather_input = json.loads(weather_input_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Could not decode stored weather input: {exc}")

    stored_output = None
    try:
        stored_output = json.loads(llm_output_json)
    except json.JSONDecodeError:
        stored_output = {"raw_output": llm_output_json}

    llm_context = llm_context or ""
    if not llm_context:
        raise click.ClickException("This log entry predates context capture; cannot replay reliably.")

    prompt_material = original_prompt
    if prompt:
        prompt_path = Path(prompt)
        if prompt_path.exists() and prompt_path.is_file():
            prompt_material = prompt_path.read_text()
            click.echo(f"Using NEW prompt loaded from file: {prompt_path}")
        else:
            prompt_material = prompt
            click.echo("Using NEW prompt text provided via --prompt option.")
    else:
        click.echo("Using ORIGINAL prompt from log.")

    click.echo(f"Using model for replay: {new_model or original_model}")

    client = LLMClient(settings.primary_llm, settings.fallback_llm, cache=None)
    new_output = client.generate(
        llm_context,
        prompt_material,
        model_override=new_model,
    )

    _print_summary(
        log_id=log_id,
        timestamp_str=timestamp_str,
        location_name=location_name,
        stored_output=stored_output,
        show_context=show_context,
        llm_context=llm_context,
        new_output=new_output,
    )


def _print_summary(
    *,
    log_id: int,
    timestamp_str: str,
    location_name: str,
    stored_output: dict,
    show_context: bool,
    llm_context: str,
    new_output: dict,
) -> None:
    original_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    local_dt = original_dt.astimezone()
    click.echo(f"--- Replaying Log ID: {log_id} ---")
    click.echo(f"Original Timestamp (Stored): {timestamp_str}")
    click.echo(f"Original Timestamp (Local): {local_dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
    click.echo(f"Location: {location_name}")
    click.echo(f"Original Description: {stored_output.get('description', 'N/A')}")
    click.echo('-' * 20)

    if show_context:
        click.echo("--- Original LLM Context ---")
        click.echo(llm_context)
        click.echo('-' * 20)

    click.echo("--- Replay Results ---")
    click.echo(f"Model Used: {new_output.get('_model_used')}")
    click.echo(json.dumps(new_output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    load_dotenv()
    main()
