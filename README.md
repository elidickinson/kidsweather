# Kid-Friendly Weather Description Service

A Python service that generates natural, kid-friendly weather descriptions using OpenWeatherMap and an LLM API (can be a small, self hosted model).

I wrote a [blog post](https://eli.pizza/posts/eink-weather-display-for-kids/) about how I use it as part of a weather eInk display:

<img src="weather-display.jpeg" alt="Large eInk weather display showing kid-friendly weather forecast" width="400">

The display is driven by a $40 single board computer and shows weather forecasts that can be easily understood.



---

## What It Does

Transforms complex weather data into simple, engaging descriptions that kids can understand. Instead of "Partly cloudy with 70% chance of precipitation," you get "It might rain later - maybe bring an umbrella! 🌧️"

The service includes:
- Command-line weather reports with HTML rendering
- A shared service layer (`WeatherReportService`) used by every entrypoint
- API caching for performance
- LLM interaction logging and replay capabilities
- Support for multiple LLM providers with automatic fallback

## Requirements

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) for dependency management (recommended) or pip
- OpenWeatherMap API key (free tier works fine)
- LLM API key (DeepSeek, OpenAI, OpenRouter, or any OpenAI-compatible API)

## Installation

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone this repository

3. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Install dependencies:
```bash
uv sync
# OR without uv: pip install .
```

5. Copy the example environment file and configure your API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### Command-Line Script

Before running these commands, make sure your `.env` file is properly configured with API keys as described in the Installation section.

Generate a weather report for a specific location:
```bash
uv run python -m kidsweather --lat 38.9 --lon -77.0
```

Load test data from a file (files live in `test_data/` by default):
```bash
uv run python -m kidsweather --load dc1
```

Save weather data for testing (writes to `test_data/` unless you supply `--save` with a different path):
```bash
uv run python -m kidsweather --lat 38.9 --lon -77.0 --save dc_latest
```

Log LLM interactions:
```bash
uv run python -m kidsweather --lat 38.9 --lon -77.0 --log-interactions
```

See what the model was told:
```bash
uv run python -m kidsweather --lat 38.9 --lon -77.0 --verbose
```

### Render HTML

Render weather report as HTML to a file:
```bash
uv run python -m kidsweather --render page.html
```

This generates a standalone HTML file with weather information, styled for display on e-ink screens or other devices.

### LLM Replay Script

Replay logged LLM interactions with different prompts or models:
```bash
uv run python replay.py --log-id 5
uv run python replay.py --log-id 5 --new-model deepseek-coder
uv run python replay.py --log-id 5 --prompt "You are a pirate weather forecaster."
```

### Customizing Prompts

The weather report tone and style can be customized using prompt files. The system automatically combines character-specific prompts with shared technical instructions:

**Directory Structure:**
- `prompts/` - Character voice and tone files (e.g., `bluey.txt`, `default.txt`)
- `instructions/` - Shared formatting rules and technical guidelines
  - `base.txt` - JSON structure, word limits, style guide (rarely needs changing)

When you use a prompt file, the system automatically appends `instructions/base.txt` to it, so you only need to specify the character voice.

**Using a custom prompt:**
```bash
uv run python -m kidsweather --prompt prompts/bluey.txt
```

**Creating a new character:**
Create a new file in `prompts/` with just the character voice and tone. The technical instructions from `instructions/base.txt` will be added automatically.

## Example Output

```json
{
  "description": "It's cool right now, maybe wear a light jacket. 🧥 The rest of the day looks cloudy but nice!",
  "daily_forecasts": [
    "Monday: Cloudy day ☁️",
    "Tuesday: Rain coming later 🌧️",
    "Wednesday: Still rainy",
    "Thursday: Cloudy again"
  ],
  "temperature": 47,
  "feels_like": 44,
  "conditions": "overcast clouds",
  "high_temp": 59,
  "low_temp": 47,
  "icon_url": "http://openweathermap.org/img/wn/04d@4x.png",
  "alerts": [],
  "last_updated": "Friday, April 11 at 11:30 AM"
}
```

## API Keys

1. **OpenWeatherMap:** Get a free API key at https://openweathermap.org/api
2. **LLM Provider:** Choose from DeepSeek, OpenAI, OpenRouter, or any OpenAI-compatible API

## Architecture Overview

The project is organized as a Python package with a clear separation of concerns:

- **Core** (`kidsweather/core/`): Contains the main service orchestration and settings management
  - `settings.py`: Loads environment variables into a single dataclass tree and ensures required directories exist
  - `service.py`: The `WeatherReportService` orchestrates data fetch, formatting, LLM generation, and logging
- **Clients** (`kidsweather/clients/`): External API integration layers
  - `weather_client.py`: Fetches current conditions and optional historical summaries from OpenWeatherMap, applying diskcache when configured
  - `llm_client.py`: Wraps the primary and optional fallback LLM providers, normalising JSON responses and caching successful calls  
- **Formatting** (`kidsweather/formatting/`): Data preparation and output generation
  - `weather_formatter.py`: Prepares both the LLM prompt context and the data needed for display
  - `html.py`: Contains `render_to_file()` function for HTML rendering using Jinja2 templates for e-ink displays
- **Infrastructure** (`kidsweather/infrastructure/`): Cross-cutting concerns
  - `cache_provider.py`: Cache construction and management utilities
  - `llm_logging.py`: Persists LLM interactions to SQLite for replay and debugging
- **Templates** (`kidsweather/templates/`): Jinja2 templates for HTML rendering
- **Tests** (`kidsweather/tests/`): Unit and integration tests

The main CLI entry point is `kidsweather/__main__.py`, which delegates to the Click-based command interface in `main.py`.

## Technical Notes

- Uses OpenWeatherMap's One Call API 3.0
- Supports any OpenAI-compatible chat completions API
- Configuration lives in `kidsweather/core/settings.py` and is shared across every entrypoint
- Temperatures are in Fahrenheit
- Caches API and LLM responses for 10 minutes using `diskcache`
- Logs LLM interactions to `llm_log.sqlite3` for replay
- Includes optional automatic fallback between LLM providers  
- HTML rendering uses Jinja2 templates from `kidsweather/templates/`
- Organized package structure with clear separation of concerns
