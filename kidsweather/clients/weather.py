"""OpenWeatherMap client with optional caching."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests

from ..infrastructure.cache import make_cache_key
from ..core.settings import WeatherAPISettings


@dataclass(slots=True)
class WeatherClient:
    """Thin wrapper around the weather API that hides caching and error handling."""

    settings: WeatherAPISettings
    cache: Optional[Any] = None  # diskcache.Cache, but kept loose for easier testing

    def fetch_current(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch current weather plus hourly/daily forecasts."""

        self.settings.require_api_key()
        cache_key = None
        if self.cache:
            cache_key = make_cache_key("weather", [lat, lon])
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        params = {
            "lat": lat,
            "lon": lon,
            "units": self.settings.units,
            "exclude": "minutely",
            "appid": self.settings.api_key,
        }
        response = requests.get(self.settings.api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if self.cache and cache_key:
            self.cache.set(cache_key, data, expire=self.settings.cache_ttl_seconds)
        return data

    def fetch_yesterday_summary(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch a coarse summary for yesterday using the time-machine API."""

        self.settings.require_api_key()
        now = datetime.utcnow()
        yesterday_noon = now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)
        timestamp = int(yesterday_noon.timestamp())

        cache_key = None
        if self.cache:
            cache_key = make_cache_key("weather_yesterday", [lat, lon, timestamp])
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        params = {
            "lat": lat,
            "lon": lon,
            "dt": timestamp,
            "units": self.settings.units,
            "appid": self.settings.api_key,
        }
        response = requests.get(self.settings.timemachine_url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or []
        if not data:
            return None

        entry = data[0]
        summary = {
            "date": datetime.fromtimestamp(entry["dt"]).strftime("%A, %B %d"),
            "avg_temp": round(entry.get("temp"), 1) if entry.get("temp") is not None else None,
            "high_temp": round(entry.get("temp"), 1) if entry.get("temp") is not None else None,
            "low_temp": round(entry.get("temp"), 1) if entry.get("temp") is not None else None,
            "avg_feels_like": round(entry.get("feels_like"), 1)
            if entry.get("feels_like") is not None
            else None,
            "main_condition": (entry.get("weather") or [{}])[0].get("main", "Unknown"),
        }

        if self.cache and cache_key:
            self.cache.set(cache_key, summary, expire=self.settings.cache_ttl_seconds * 6)
        return summary
