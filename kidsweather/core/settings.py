"""Application configuration models and helpers.

This module centralizes configuration state so that the rest of the
application can depend on a single, well-typed settings object rather
than importing environment variables ad hoc.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class AppSettings:
    """Application configuration with all settings in a single flat structure."""

    # Filesystem paths
    root_dir: Path
    cache_dir: Path
    prompt_dir: Path
    instructions_dir: Path
    test_data_dir: Path
    llm_log_db: Path

    # Weather API configuration
    weather_api_url: str
    weather_timemachine_url: str
    weather_units: str
    weather_cache_ttl_seconds: int
    weather_api_key: Optional[str]

    # Primary LLM configuration
    llm_api_url: Optional[str]
    llm_api_key: Optional[str]
    llm_model: Optional[str]
    llm_supports_json_mode: bool

    # Fallback LLM configuration
    fallback_llm_api_url: Optional[str] = None
    fallback_llm_api_key: Optional[str] = None
    fallback_llm_model: Optional[str] = None
    fallback_llm_supports_json_mode: bool = True

    # Default location
    default_lat: float = 38.9541848
    default_lon: float = -77.0832061
    default_location: str = "Washington, DC"

    def ensure_directories(self) -> None:
        """Create non-existent directories that the app expects."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.instructions_dir.mkdir(parents=True, exist_ok=True)
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

    def require_weather_api_key(self) -> None:
        """Ensure the weather API key is available before making live API calls."""
        if not self.weather_api_key:
            raise ValueError(
                "WEATHER_API_KEY is required to fetch live weather data. "
                "Ensure it is set in your environment or pass mock data to the service."
            )

    def require_llm_configured(self) -> None:
        """Validate that the primary LLM config is usable."""
        missing = []
        if not self.llm_api_url:
            missing.append("llm_api_url")
        if not self.llm_api_key:
            missing.append("llm_api_key")
        if not self.llm_model:
            missing.append("llm_model")

        if missing:
            details = ", ".join(missing)
            raise ValueError(
                f"Missing {details} for primary LLM configuration. Update your environment variables."
            )

    def has_fallback_llm(self) -> bool:
        """Return True if fallback LLM is configured."""
        return all([
            self.fallback_llm_api_url,
            self.fallback_llm_api_key,
            self.fallback_llm_model
        ])


@lru_cache(maxsize=1)
def load_settings(env_file: Optional[str] = None) -> AppSettings:
    """Load configuration from environment variables.

    Parameters
    ----------
    env_file:
        Optional explicit path to a .env file. When ``None`` the default search
        order used by :func:`dotenv.load_dotenv` applies.

    Returns
    -------
    AppSettings
        Fully populated settings dataclass with lazily-created directories.
    """

    load_dotenv(env_file)  # Idempotent; safe to call repeatedly.

    root_dir = Path(__file__).parent.parent.parent
    cache_dir = root_dir / "api_cache"
    prompt_dir = root_dir / "prompts"
    instructions_dir = root_dir / "instructions"
    test_data_dir = root_dir / "test_data"
    llm_log_db = root_dir / "llm_log.sqlite3"

    settings = AppSettings(
        # Paths
        root_dir=root_dir,
        cache_dir=cache_dir,
        prompt_dir=prompt_dir,
        instructions_dir=instructions_dir,
        test_data_dir=test_data_dir,
        llm_log_db=llm_log_db,
        # Weather API
        weather_api_url=os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/3.0/onecall"),
        weather_timemachine_url=os.getenv(
            "WEATHER_TIMEMACHINE_API_URL",
            "https://api.openweathermap.org/data/3.0/onecall/timemachine",
        ),
        weather_units=os.getenv("WEATHER_UNITS", "imperial"),
        weather_cache_ttl_seconds=int(os.getenv("API_CACHE_TIME", "600")),
        weather_api_key=os.getenv("WEATHER_API_KEY"),
        # Primary LLM
        llm_api_url=os.getenv("LLM_API_URL"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model=os.getenv("LLM_MODEL"),
        llm_supports_json_mode=os.getenv("LLM_SUPPORTS_JSON_MODE", "true").lower() == "true",
        # Fallback LLM
        fallback_llm_api_url=os.getenv("FALLBACK_LLM_API_URL"),
        fallback_llm_api_key=os.getenv("FALLBACK_LLM_API_KEY"),
        fallback_llm_model=os.getenv("FALLBACK_LLM_MODEL"),
        fallback_llm_supports_json_mode=os.getenv("FALLBACK_LLM_SUPPORTS_JSON_MODE", "true").lower() == "true",
        # Default location
        default_lat=float(os.getenv("DEFAULT_LAT", "38.9541848")),
        default_lon=float(os.getenv("DEFAULT_LON", "-77.0832061")),
        default_location=os.getenv("DEFAULT_LOCATION", "Washington, DC"),
    )

    settings.ensure_directories()
    return settings
