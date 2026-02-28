"""OpenWeatherMap client with optional caching."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

import requests

from ..core.settings import AppSettings


@dataclass(slots=True)
class WeatherClient:
    """Thin wrapper around the weather API that hides caching and error handling."""

    settings: AppSettings
    cache: Optional[Any] = None  # diskcache.Cache, but kept loose for easier testing

    def _get_or_cache(
        self,
        cache_key: str,
        fetch_fn: Callable,
        no_refresh: bool,
        error_msg: str
    ) -> Any:
        """Generic cache retrieval or API fetch pattern."""
        if self.cache and not no_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        elif self.cache and no_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
            raise ValueError(error_msg)

        data = fetch_fn()
        if self.cache and cache_key and not no_refresh:
            self.cache.set(cache_key, data, expire=self._get_cache_ttl(cache_key))
        return data

    def _get_cache_ttl(self, cache_key: str) -> int:
        """Return appropriate TTL based on cache key type."""
        return self.settings.weather_cache_ttl_seconds * (6 if "yesterday" in cache_key else 1)

    def fetch_current(self, lat: float, lon: float, *, no_refresh: bool = False) -> Dict[str, Any]:
        """Fetch current weather plus hourly/daily forecasts."""

        self.settings.require_weather_api_key()
        cache_key = f"weather_{lat}_{lon}"
        error_msg = f"No cached weather data found for coordinates {lat}, {lon} and --no-refresh-weather was specified"

        def fetch_current_weather():
            params = {
                "lat": lat,
                "lon": lon,
                "units": self.settings.weather_units,
                "exclude": "minutely",
                "appid": self.settings.weather_api_key,
            }
            response = requests.get(self.settings.weather_api_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        return self._get_or_cache(cache_key, fetch_current_weather, no_refresh, error_msg)

    def fetch_yesterday_summary(self, lat: float, lon: float, *, no_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch a coarse summary for yesterday using the time-machine API."""

        self.settings.require_weather_api_key()
        now = datetime.utcnow()
        yesterday_noon = now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)
        timestamp = int(yesterday_noon.timestamp())

        cache_key = f"weather_yesterday_{lat}_{lon}_{timestamp}"
        error_msg = f"No cached yesterday weather data found for coordinates {lat}, {lon} and --no-refresh-weather was specified"

        def fetch_yesterday_weather():
            params = {
                "lat": lat,
                "lon": lon,
                "dt": timestamp,
                "units": self.settings.weather_units,
                "appid": self.settings.weather_api_key,
            }
            response = requests.get(self.settings.weather_timemachine_url, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or []
            if not data:
                return None

            entry = data[0]
            return {
                "date": datetime.fromtimestamp(entry["dt"]).strftime("%A, %B %d"),
                "avg_temp": round(entry.get("temp"), 1) if entry.get("temp") is not None else None,
                "high_temp": round(entry.get("temp"), 1) if entry.get("temp") is not None else None,
                "low_temp": round(entry.get("temp"), 1) if entry.get("temp") is not None else None,
                "avg_feels_like": round(entry.get("feels_like"), 1)
                if entry.get("feels_like") is not None
                else None,
                "main_condition": (entry.get("weather") or [{}])[0].get("main", "Unknown"),
            }

        return self._get_or_cache(cache_key, fetch_yesterday_weather, no_refresh, error_msg)
