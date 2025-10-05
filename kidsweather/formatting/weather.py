"""Helpers for shaping weather data for display and LLM consumption."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def format_alert_time(timestamp: int, timezone_offset: int) -> str:
    """Return human friendly alert timing, including day if needed."""

    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc) + timedelta(seconds=timezone_offset)
    today = datetime.now(timezone(timedelta(seconds=timezone_offset))).date()
    if dt.date() == today:
        return dt.strftime("%-I%p")
    return dt.strftime("%-I%p %a")


def _format_clock(timestamp_utc: Optional[int], tz_offset: int) -> str:
    if timestamp_utc is None:
        return "N/A"
    dt = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc) + timedelta(seconds=tz_offset)
    return dt.strftime("%I:%M %p")


def _day_name(timestamp_utc: Optional[int], tz_offset: int) -> str:
    if timestamp_utc is None:
        return "N/A"
    dt = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc) + timedelta(seconds=tz_offset)
    return dt.strftime("%A")


def _describe_wind(speed: Optional[float], gust: Optional[float] = None) -> str:
    if speed is None:
        return "Wind data not available."
    if speed >= 25:
        description = f"Very windy, around {speed:.0f} mph."
    elif speed >= 15:
        description = f"Windy, around {speed:.0f} mph."
    elif speed >= 5:
        description = f"Light winds around {speed:.0f} mph."
    elif speed > 1:
        description = "Mostly calm."
    else:
        description = "No wind."
    if gust and gust > speed * 1.5 and gust > 5:
        description += f" Gusts up to {gust:.0f} mph."
    return description


def _describe_uvi(uvi: Optional[float]) -> str:
    if uvi is None:
        return "N/A"
    value = float(uvi)
    if value < 4:
        return f"{value:.1f} (low)"
    elif value < 6:
        return f"{value:.1f} (mild)"
    elif value < 8:
        return f"{value:.1f} - Mention sunscreen"
    else:
        return f"{value:.1f} - Sunscreen is a must!"


def _safe_round(value: Optional[float]) -> Optional[int]:
    if value is None:
        return None
    return int(round(value))


def _format_metric(value: Optional[float]) -> str:
    rounded = _safe_round(value)
    return f"{rounded}°F" if rounded is not None else "N/A"


def format_for_llm(weather_data: Dict[str, Any], yesterday_data: Optional[Dict[str, Any]] = None) -> str:
    """Convert weather data to an explanatory text block for the LLM."""

    tz_offset = weather_data.get("timezone_offset", 0)
    lines: List[str] = []

    current_time = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
    rounded_minute = (current_time.minute // 15) * 15
    rounded_time = current_time.replace(minute=rounded_minute, second=0, microsecond=0)
    lines.append(f"Current Date and Time: {rounded_time.strftime('%A, %B %d, %Y at %I:%M %p')}")

    if yesterday_data:
        lines.append(f"\nYESTERDAY'S WEATHER ({yesterday_data['date']}):")
        avg_temp = _format_metric(yesterday_data.get("avg_temp"))
        feels_like = _format_metric(yesterday_data.get("avg_feels_like"))
        high_temp = _format_metric(yesterday_data.get("high_temp"))
        low_temp = _format_metric(yesterday_data.get("low_temp"))
        lines.append(f"  Average Temperature: {avg_temp} (felt like {feels_like})")
        lines.append(f"  High: {high_temp}, Low: {low_temp}")
        lines.append(f"  Main Condition: {yesterday_data.get('main_condition', 'Unknown')}")

    current = weather_data.get("current", {})
    lines.append("\nTODAY'S FORECAST:")
    desc = (current.get("weather") or [{}])[0].get("description", "Not available")
    temperature = _format_metric(current.get("temp"))
    line = f"  Right Now: {desc} at {temperature}"
    feels_like = current.get("feels_like")
    if feels_like is not None and current.get("temp") is not None:
        if abs(round(current["temp"]) - round(feels_like)) > 5:
            line += f" (feels like {round(feels_like)}°F)"
    lines.append(line)

    precip_line = "  Current Precipitation: none."
    rain = current.get("rain", {}).get("1h")
    snow = current.get("snow", {}).get("1h")
    if rain:
        precip_line = f"  Current Precipitation: raining ({rain} mm/hr)."
    elif snow:
        precip_line = f"  Current Precipitation: snowing ({snow} mm/hr)."
    lines.append(precip_line)

    lines.append(f"  Current Wind: {_describe_wind(current.get('wind_speed'), current.get('wind_gust'))}")
    lines.append(f"  Current UV Index: {_describe_uvi(current.get('uvi'))}")
    lines.append(
        "  Sunrise: "
        + _format_clock(current.get("sunrise"), tz_offset)
        + ", Sunset: "
        + _format_clock(current.get("sunset"), tz_offset)
        + "."
    )

    daily = weather_data.get("daily", [])
    if daily:
        today = daily[0]
        summary = today.get('summary', 'No summary available.')
        lines.append(
            f"\n  Overall for Today ({_day_name(today.get('dt'), tz_offset)}): {summary}"
        )
        high = _format_metric(today.get("temp", {}).get("max"))
        low = _format_metric(today.get("temp", {}).get("min"))
        lines.append(f"  High: {high}, Low for tonight: {low}.")
        lines.append(f"  Precipitation: {describe_precipitation(today)}")
        lines.append(f"  Day Wind: {_describe_wind(today.get('wind_speed'), today.get('wind_gust'))}")

    hourly = weather_data.get("hourly", [])
    if hourly:
        lines.append("\nNEXT 8 HOURS:")
        for hour in hourly[:8]:
            hour_line = f"  {_format_clock(hour.get('dt'), tz_offset)}: "
            hour_line += f"{(hour.get('weather') or [{}])[0].get('description', 'N/A')}"
            hour_line += f" at {_format_metric(hour.get('temp'))}"
            uvi = hour.get("uvi")
            if uvi and float(uvi) >= 6:
                hour_line += f" (UV {_describe_uvi(uvi)})"
            pop = hour.get("pop", 0)
            if pop:
                details: List[str] = [f"{int(pop * 100)}% chance precip"]
                rain_amt = hour.get("rain", {}).get("1h", 0)
                snow_amt = hour.get("snow", {}).get("1h", 0)
                if rain_amt:
                    details.append(f"{rain_amt}mm rain")
                if snow_amt:
                    details.append(f"{snow_amt}mm snow")
                hour_line += f" ({', '.join(details)})"
            lines.append(hour_line)

    lines.append("\nNEXT FEW DAYS (for daily_forecasts - use these exact day names):")
    if len(daily) > 1:
        for day in daily[1:5]:
            lines.append(f"\n  {_day_name(day.get('dt'), tz_offset)}:")
            lines.append(f"    Summary: {day.get('summary', 'No summary available.')}")
            lines.append(
                f"    High: {_format_metric(day.get('temp', {}).get('max'))}, "
                f"Low: {_format_metric(day.get('temp', {}).get('min'))}."
            )
            lines.append(f"    Precipitation: {describe_precipitation(day)}")
            lines.append(f"    Wind: {_describe_wind(day.get('wind_speed'), day.get('wind_gust'))}")
    else:
        lines.append("  No extended forecast available.")

    return "\n".join(lines)


def describe_precipitation(day: Dict[str, Any]) -> str:
    """Return a short precipitation summary for a daily forecast entry."""

    probability = day.get("pop", 0)
    if not probability or probability < 0.1:
        return "Low chance of precipitation."
    desc = f"{int(probability * 100)}% chance of precipitation"
    rain_amount = day.get("rain")
    snow_amount = day.get("snow")
    extras: List[str] = []
    if rain_amount:
        extras.append(f"{rain_amount}mm rain")
    if snow_amount:
        extras.append(f"{snow_amount}mm snow")
    if extras:
        desc += f" ({', '.join(extras)})"
    return desc + "."


def extract_display_data(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return the subset needed for templates/CLI output."""

    current = weather_data.get("current", {})
    daily = weather_data.get("daily", [])

    alerts_payload = []
    tz_offset = weather_data.get("timezone_offset", 0)
    for alert in (weather_data.get("alerts") or []):
        start = alert.get("start")
        end = alert.get("end")
        alerts_payload.append(
            {
                "event": alert.get("event", "Weather Alert"),
                "start": format_alert_time(start, tz_offset) if start else "N/A",
                "end": format_alert_time(end, tz_offset) if end else "N/A",
            }
        )

    forecast_days = []
    for day in daily[:5]:
        timestamp = day.get("dt")
        day_name = datetime.fromtimestamp(timestamp).strftime("%A") if timestamp else "Unknown"
        forecast_days.append(
            {
                "day": day_name,
                "high": _safe_round(day.get("temp", {}).get("max")),
                "low": _safe_round(day.get("temp", {}).get("min")),
                "conditions": (day.get("weather") or [{}])[0].get("description"),
                "precip_prob": float(day.get("pop", 0) or 0) * 100,
                "icon": (day.get("weather") or [{}])[0].get("icon"),
            }
        )

    today = daily[0] if daily else None
    high = today.get("temp", {}).get("max") if today else current.get("temp")
    low = today.get("temp", {}).get("min") if today else current.get("temp")

    return {
        "current": {
            "temp": _safe_round(current.get("temp")),
            "feels_like": _safe_round(current.get("feels_like")),
            "conditions": (current.get("weather") or [{}])[0].get("description", "") if current else "",
            "icon": (current.get("weather") or [{}])[0].get("icon", "") if current else "",
        },
        "forecast": {
            "high_temp": _safe_round(high),
            "low_temp": _safe_round(low),
        },
        "alerts": alerts_payload,
        "daily_forecast_raw": forecast_days,
        "location": "",
    }
