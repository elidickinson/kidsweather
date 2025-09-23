"""Application configuration models and helpers.

This module centralizes configuration state so that the rest of the
application can depend on a single, well-typed settings object rather
than importing environment variables ad hoc. The dataclasses capture the
shape of both weather and LLM configuration while keeping side effects
(such as reading `.env` or creating directories) explicit at the call
site.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class LLMProviderSettings:
    """Configuration for a single LLM provider endpoint."""

    api_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    supports_json_mode: bool = True

    def is_configured(self) -> bool:
        """Return True when all required fields are present."""

        return all([self.api_url, self.api_key, self.model])

    def require_complete(self, label: str) -> None:
        """Raise if any required field is missing.

        Parameters
        ----------
        label:
            Identifier for the provider (e.g., "primary" or "fallback") to
            help pinpoint which configuration needs attention.
        """

        missing = [
            name
            for name, value in (
                ("api_url", self.api_url),
                ("api_key", self.api_key),
                ("model", self.model),
            )
            if not value
        ]
        if missing:
            details = ", ".join(missing)
            raise ValueError(
                f"Missing {details} for {label} LLM configuration. Update your environment variables."
            )


@dataclass(slots=True)
class WeatherAPISettings:
    """Configuration for OpenWeatherMap access."""

    api_url: str
    timemachine_url: str
    units: str
    cache_ttl_seconds: int
    api_key: Optional[str]

    def require_api_key(self) -> None:
        """Ensure the key is available before making live API calls."""

        if not self.api_key:
            raise ValueError(
                "WEATHER_API_KEY is required to fetch live weather data. "
                "Ensure it is set in your environment or pass mock data to the service."
            )


@dataclass(slots=True)
class AppPaths:
    """Filesystem locations used by the application."""

    root_dir: Path
    cache_dir: Path
    prompt_dir: Path
    test_data_dir: Path
    llm_log_db: Path

    def ensure_directories(self) -> None:
        """Create non-existent directories that the app expects."""

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.test_data_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class AppSettings:
    """Aggregate application configuration."""

    paths: AppPaths
    weather_api: WeatherAPISettings
    primary_llm: LLMProviderSettings
    fallback_llm: Optional[LLMProviderSettings]
    default_lat: float
    default_lon: float
    default_location: str

    def ensure_llm_ready(self) -> None:
        """Validate that the primary (and optional fallback) LLM configs are usable."""

        self.primary_llm.require_complete("primary")
        if self.fallback_llm:
            self.fallback_llm.require_complete("fallback")


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

    root_dir = Path(__file__).parent
    cache_dir = root_dir / "api_cache"
    prompt_dir = root_dir / "prompts"
    test_data_dir = root_dir / "test_data"
    llm_log_db = root_dir / "llm_log.sqlite3"

    primary_llm = LLMProviderSettings(
        api_url=os.getenv("LLM_API_URL"),
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("LLM_MODEL"),
        supports_json_mode=os.getenv("LLM_SUPPORTS_JSON_MODE", "true").lower() == "true",
    )

    fallback = LLMProviderSettings(
        api_url=os.getenv("FALLBACK_LLM_API_URL"),
        api_key=os.getenv("FALLBACK_LLM_API_KEY"),
        model=os.getenv("FALLBACK_LLM_MODEL"),
        supports_json_mode=os.getenv("FALLBACK_LLM_SUPPORTS_JSON_MODE", "true").lower() == "true",
    )
    fallback_llm = fallback if fallback.is_configured() else None

    settings = AppSettings(
        paths=AppPaths(
            root_dir=root_dir,
            cache_dir=cache_dir,
            prompt_dir=prompt_dir,
            test_data_dir=test_data_dir,
            llm_log_db=llm_log_db,
        ),
        weather_api=WeatherAPISettings(
            api_url=os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/3.0/onecall"),
            timemachine_url=os.getenv(
                "WEATHER_TIMEMACHINE_API_URL",
                "https://api.openweathermap.org/data/3.0/onecall/timemachine",
            ),
            units=os.getenv("WEATHER_UNITS", "imperial"),
            cache_ttl_seconds=int(os.getenv("API_CACHE_TIME", "600")),
            api_key=os.getenv("WEATHER_API_KEY"),
        ),
        primary_llm=primary_llm,
        fallback_llm=fallback_llm,
        default_lat=float(os.getenv("DEFAULT_LAT", "38.9541848")),
        default_lon=float(os.getenv("DEFAULT_LON", "-77.0832061")),
        default_location=os.getenv("DEFAULT_LOCATION", "Washington, DC"),
    )

    settings.paths.ensure_directories()
    return settings
