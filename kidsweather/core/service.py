"""High level orchestration for building kid-friendly weather reports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import diskcache
import requests

from ..clients.llm import LLMClient
from ..infrastructure.logging import LLMInteractionLogger
from .settings import AppSettings, load_settings
from ..clients.weather import WeatherClient
from ..formatting.weather import extract_display_data, format_for_llm

CWG_API_URL = "https://cwg.eli.pw/api/cwg.json"
CWG_TIMEOUT = 10
CWG_MAX_AGE_HOURS = 12


def fetch_cwg_forecast(max_age_hours: int = CWG_MAX_AGE_HOURS) -> Optional[str]:
    """Fetch the CWG forecast and return plain text with age label.

    Uses server-side fields (latest_post_text, latest_post_age_hours) and the
    max_age_hours query parameter so no HTML parsing or timezone guessing is needed.
    """
    try:
        resp = requests.get(
            CWG_API_URL,
            params={"max_age_hours": max_age_hours},
            timeout=CWG_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    text = data.get("latest_post_text")
    if not text:
        return None
    age = data.get("latest_post_age_hours", 0)
    headline = data.get("main_headline", "")
    hours = int(age)
    age_label = f"Posted about {hours} hour{'s' if hours != 1 else ''} ago" if hours >= 1 else "Posted less than an hour ago"
    parts = []
    if headline:
        parts.append(headline)
    parts.append(f"({age_label})")
    parts.append(text)
    return "\n".join(parts)


@dataclass(slots=True)
class WeatherReportService:
    """Coordinates weather retrieval, formatting, LLM generation, and logging."""

    settings: AppSettings
    weather_client: WeatherClient
    llm_client: LLMClient
    logger: Optional[LLMInteractionLogger] = None
    last_llm_context: Optional[str] = None
    last_system_prompt: Optional[str] = None

    def build_report(
        self,
        *,
        latitude: Optional[float],
        longitude: Optional[float],
        prompt_override: Optional[str] = None,
        include_yesterday: bool = True,
        log_interaction: bool = False,
        source: str = "unknown",
        weather_data_override: Optional[Dict[str, Any]] = None,
        model_override: Optional[str] = None,
        no_refresh_weather: bool = False,
        no_refresh_llm: bool = False,
        force_refresh_llm: bool = False,
    ) -> Dict[str, Any]:
        """Return a fully populated report ready for display layers."""

        weather_data = weather_data_override or self._fetch_weather_data(latitude, longitude, no_refresh_weather)
        yesterday = None
        if (
            include_yesterday
            and weather_data
            and weather_data.get("lat")
            and weather_data.get("lon")
            and self.settings.weather_api_key
        ):
            yesterday = self._fetch_yesterday_data_cached(weather_data["lat"], weather_data["lon"], no_refresh_weather)

        cwg = fetch_cwg_forecast()
        prompt = self._resolve_prompt(prompt_override)
        llm_context = format_for_llm(weather_data, yesterday, cwg_forecast=cwg)

        # --force-refresh-llm overrides --no-refresh-llm
        effective_no_refresh = no_refresh_llm and not force_refresh_llm
        llm_response = self.llm_client.generate(
            llm_context,
            prompt,
            model_override=model_override,
            no_refresh=effective_no_refresh,
            force_refresh=force_refresh_llm,
        )

        if log_interaction and self.logger:
            self.logger.ensure_schema()
            payload = {k: v for k, v in llm_response.items() if k != "_raw_llm_response"}
            self.logger.log(
                weather_input=weather_data,
                llm_context=llm_context,
                system_prompt=prompt,
                model_used=llm_response.get("_model_used", model_override or self.settings.llm_model),
                llm_output={
                    "raw_llm_response": llm_response.get("_raw_llm_response", ""),
                    "parsed_result": payload,
                },
                description=llm_response.get("description", ""),
                source=source,
                location_name=weather_data.get("timezone") if isinstance(weather_data, dict) else None,
            )

        display_data = extract_display_data(weather_data)
        self.last_llm_context = llm_context
        self.last_system_prompt = prompt
        return self._assemble_report(weather_data, llm_response, display_data)

    def _fetch_weather_data(self, latitude: Optional[float], longitude: Optional[float], no_refresh: bool = False) -> Dict[str, Any]:
        lat_value = latitude if latitude is not None else self.settings.default_lat
        lon_value = longitude if longitude is not None else self.settings.default_lon
        return self.weather_client.fetch_current(lat_value, lon_value, no_refresh=no_refresh)

    def _fetch_yesterday_data_cached(self, lat: float, lon: float, no_refresh: bool = False) -> Optional[Dict[str, Any]]:
        try:
            return self.weather_client.fetch_yesterday_summary(lat, lon, no_refresh=no_refresh)
        except ValueError as e:
            if no_refresh and "yesterday" in str(e):
                pattern = re.compile(rf"weather_yesterday_{lat}_{lon}_\d+")
                for key in self.weather_client.cache.iterkeys():
                    if pattern.match(key):
                        cached_data = self.weather_client.cache.get(key)
                        if cached_data is not None:
                            return cached_data
            raise

    def _resolve_prompt(self, prompt_override: Optional[str]) -> str:
        if not prompt_override:
            return (self.settings.prompt_dir / "default.txt").read_text()
        path = Path(prompt_override)
        if path.exists() and path.is_file():
            return path.read_text()
        return prompt_override

    @staticmethod
    def _assemble_report(
        weather_data: Dict[str, Any],
        llm_response: Dict[str, Any],
        display_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        icon = display_data["current"].get("icon")
        timestamp = weather_data.get("current", {}).get("dt")
        last_updated = "Unknown"
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            last_updated = dt.strftime("%A, %B %d at %I:%M %p").lstrip("0").replace(" 0", " ")

        return {
            "description": llm_response.get("description", ""),
            "temperature": display_data["current"].get("temp"),
            "feels_like": display_data["current"].get("feels_like"),
            "conditions": display_data["current"].get("conditions"),
            "high_temp": display_data["forecast"].get("high_temp"),
            "low_temp": display_data["forecast"].get("low_temp"),
            "icon_url": f"http://openweathermap.org/img/wn/{icon}@4x.png" if icon else None,
            "alerts": [
                f"{a['event']} ({a['start']} to {a['end']})"
                for a in display_data.get("alerts", [])
            ],
            "last_updated": last_updated,
            "_raw_llm_response": llm_response.get("_raw_llm_response"),
            "model_used": llm_response.get("_model_used"),
        }


def build_default_service() -> WeatherReportService:
    """Convenience constructor used by CLI and web app entrypoints."""

    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    shared_cache = diskcache.Cache(settings.cache_dir)
    weather_client = WeatherClient(settings, cache=shared_cache)
    llm_client = LLMClient(
        settings,
        cache=shared_cache,
        cache_ttl_seconds=settings.weather_cache_ttl_seconds,
    )
    logger = LLMInteractionLogger(settings.llm_log_db)
    return WeatherReportService(settings, weather_client, llm_client, logger=logger)
