# Kid-Friendly Weather Description Service

A simple Python service that generates natural, kid-friendly weather descriptions using OpenWeatherMap and any OpenAI-compatible LLM API. It includes a command-line script, a Flask web application, API caching, and LLM interaction logging/replay capabilities.

## What's It For?

I built it as part of a *[big eInk weather display](https://eli.pizza/posts/eink-weather-display-for-kids/)* to generate a weather forecast that my kids could understand.

## Requirements

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) for dependency management (optional, but recommended)
- OpenWeatherMap API key (free tier works fine)
- LLM API key (DeepSeek, OpenAI, OpenRouter, or any OpenAI-compatible API)

## Installation

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone this repository or download the script

3. Create and activate a virtual environment with uv:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a `.env` file with your API keys:
```bash
# Weather API (required)
WEATHER_API_KEY=your_openweathermap_key

# LLM Configuration (all three required - see examples below)
LLM_API_URL=<your-api-endpoint>
LLM_API_KEY=<your-api-key>
LLM_MODEL=<model-name>
LLM_SUPPORTS_JSON_MODE=true  # Optional, defaults to true. Set to false for LM Studio

# Fallback LLM Configuration (optional - all four must be set if using)
FALLBACK_LLM_API_URL=<fallback-api-endpoint>
FALLBACK_LLM_API_KEY=<fallback-api-key>
FALLBACK_LLM_MODEL=<fallback-model-name>
FALLBACK_LLM_SUPPORTS_JSON_MODE=true  # Optional, defaults to true
```

## LLM Provider Configuration

Choose one of the following providers:

### DeepSeek
```bash
LLM_API_URL=https://api.deepseek.com/chat/completions
LLM_API_KEY=sk-your-deepseek-api-key
LLM_MODEL=deepseek-chat
```

### OpenAI
```bash
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-3.5-turbo  # or gpt-4
```

### OpenRouter
```bash
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_API_KEY=sk-or-v1-your-openrouter-key
LLM_MODEL=anthropic/claude-3-haiku  # or any model from openrouter.ai/models
```

### LM Studio (Local)
```bash
LLM_API_URL=http://localhost:1234/v1/chat/completions
LLM_API_KEY=lm-studio
LLM_MODEL=TheBloke/Mistral-7B-Instruct-v0.2-GGUF
LLM_SUPPORTS_JSON_MODE=false  # LM Studio doesn't support response_format
```

### Fallback Configuration Example

If your primary LLM provider fails, the system will automatically try the fallback:

```bash
# Primary: DeepSeek
LLM_API_URL=https://api.deepseek.com/chat/completions
LLM_API_KEY=sk-your-deepseek-api-key
LLM_MODEL=deepseek-chat

# Fallback: OpenRouter
FALLBACK_LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
FALLBACK_LLM_API_KEY=sk-or-v1-your-openrouter-key
FALLBACK_LLM_MODEL=anthropic/claude-3-haiku
```
## Usage

### Command-Line Script (`weather_cli.py`)

Generate a report for a specific location:
```bash
uv run ./weather_cli.py --lat 38.9 --lon -77.0
```

Load data from a test file (e.g., `test_data/dc1.json`):
```bash
uv run ./weather_cli.py --load dc1
```

Save the fetched weather data for later use (e.g. for testing):
```bash
uv run ./weather_cli.py --lat 38.9 --lon -77.0 --save dc_latest
```

Log the LLM interaction to `llm_log.sqlite3`:
```bash
uv run ./weather_cli.py --lat 38.9 --lon -77.0 --log-interactions
```

Save the output description or full JSON:
```bash
uv run ./weather_cli.py --lat 38.9 --lon -77.0 --save-txt report_desc
uv run ./weather_cli.py --lat 38.9 --lon -77.0 --save-json report_full
```

**Arguments:**
- `--lat`: Latitude (required unless using `--load`)
- `--lon`: Longitude (required unless using `--load`)
- `--load`: Load weather data from `test_data/<name>.json`
- `--save`: Save fetched weather data to `test_data/<name>.json`
- `--log-interactions`: Log LLM call details to `llm_log.sqlite3`
- `--save-json`: Save the final JSON report to `<name>.json`
- `--save-txt`: Save just the description text to `<name>.txt`

### Flask Web App (`app.py`)

Run the web server (defaults to port 5001):
```bash
uv run app.py
```
Then open http://127.0.0.1:5001 in your browser.

The app provides endpoints:
- `/`: HTML weather report
- `/weather.json`: JSON weather report
- `/weather.txt`: Plain text weather description

Render the HTML directly to a file:
```bash
uv run app.py --render page.html
```

### LLM Replay Script (`replay.py`)

Replay a specific logged LLM interaction (e.g., log ID 5) using the original prompt and model:
```bash
uv run replay.py --log-id 5
```

Replay log ID 5 using a different model:
```bash
uv run replay.py --log-id 5 --new-model deepseek-coder
```

Replay log ID 5 using a new system prompt text:
```bash
uv run replay.py --log-id 5 --prompt "You are a pirate weather forecaster. Be funny. Respond in JSON."
```

**Arguments:**
- `--log-id`: The ID from the `llm_interactions` table to replay (required).
- `--prompt`: New system prompt text to use for the replay. Overrides the original prompt from the log.
- `--new-model`: Name of a model to use for the replay. Overrides the original model from the log.

### Example Output
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

1. **OpenWeatherMap:** Get a free API key at https://openweathermap.org/api (One Call API 3.0 is used)
2. **LLM Provider:** Choose from:
   - DeepSeek: https://platform.deepseek.com/
   - OpenAI: https://platform.openai.com/
   - OpenRouter: https://openrouter.ai/

## Notes

- Uses OpenWeatherMap's One Call API 3.0
- Supports any OpenAI-compatible chat completions API
- Temperatures are in Fahrenheit
- Caches API responses for 10 minutes using `diskcache` in the `api_cache/` directory
- Logs LLM interactions to `llm_log.sqlite3` when run via Flask or with the `--log-interactions` flag
- The `replay.py` script allows re-running logged interactions with different prompts or models
- Includes a Flask web application (`app.py`) running on port 5001
