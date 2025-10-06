# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Commands
- Render weather HTML: `uv run python -m kidsweather --render page.html`
- Run weather script: `uv run python -m kidsweather --lat 38.9 --lon -77.0`
- Run LLM replay: `uv run python replay.py --log-id <id>`
- Deploy to server: `./deploy.sh`
- Full workflow: `./sendit.sh` (renders HTML, screenshots, pushes to e-ink)
- Source the .venv when running python scripts

## Style Guidelines
- Python 3.9+ with type hints when appropriate
- Follow PEP 8 conventions for formatting
- Use f-strings for string formatting
- Group imports: standard library, then third-party, then local
- Use docstrings for functions (single-line is sufficient)
- Error handling: Print to stderr with specific error messages
- Prefer descriptive variable/function names
- Cache API responses with diskcache when possible
- Log errors with context to aid debugging
- Keep JSON output format consistent with example templates

## Architecture Notes
- CLI tool with HTML rendering via Jinja2 templates
- OpenWeatherMap API for weather data, any OpenAI-compatible API for LLM
- Uses environment variables from .env file
- Caches API responses in api_cache/ directory
- Logs LLM interactions to llm_log.sqlite3 for replay and debugging
- Settings are in a single flat AppSettings dataclass (kidsweather/core/settings.py)
- Yesterday's weather is included in LLM context for comparison
