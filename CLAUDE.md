# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run Flask web app: `./app.py`
- Run weather script: `./weather_script.py --lat 38.9 --lon -77.0`
- Run LLM replay: `./replay_llm.py --log-id <id>`
- Deploy to server: `./deploy.sh`
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
- Flask for web interface (port 5001)
- OpenWeatherMap and DeepSeek APIs
- Uses environment variables from .env file
- Caches API responses in api_cache/ directory
- Logs LLM interactions to llm_log.sqlite3
