#!/usr/bin/env python3
"""
Data models for the Kids Weather application.

This module defines the core data structures used throughout the application
using Python type hints for improved code clarity and reliability.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

@dataclass
class CurrentWeather:
    """Current weather conditions."""
    temp: int
    feels_like: int
    conditions: str
    humidity: int
    uvi: float = 0.0
    icon: str = ""
    clouds: Union[int, str] = ""
    visibility: Union[int, str] = ""
    wind_speed: Union[float, str] = ""

@dataclass
class HourlyForecast:
    """Hourly weather forecast data."""
    time: str
    temp: int
    feels_like: int
    conditions: str
    precip_prob: int
    rain_inches: Optional[float] = None

@dataclass
class ForecastMetrics:
    """Combined forecast metrics."""
    high_temp: int
    low_temp: int
    hourly: List[HourlyForecast] = field(default_factory=list)
    humidity: Optional[int] = None
    wind_gust: Optional[float] = None
    uvi: Optional[float] = None

@dataclass
class DailyForecast:
    """Daily weather forecast."""
    day: str
    high: int
    low: int
    conditions: str
    precip_prob: float
    icon: Optional[str] = None

@dataclass
class WeatherAlert:
    """Weather alert information."""
    event: str
    description: str = ""
    start: str = ""
    end: str = ""

@dataclass
class WeatherContext:
    """Complete weather context for LLM processing."""
    current_time: str
    current: CurrentWeather
    forecast: ForecastMetrics
    daily_forecast_raw: List[DailyForecast]  # Raw data from weather API
    alerts: List[WeatherAlert] = field(default_factory=list)

@dataclass
class WeatherReport:
    """Processed weather report for display."""
    description: str
    daily_forecasts_llm: Dict[str, str]  # LLM-generated text descriptions
    temperature: int
    feels_like: int
    conditions: str
    high_temp: int
    low_temp: int
    icon_url: str
    alerts: List[str] = field(default_factory=list)
    last_updated: str = ""
    daily_forecast_raw: List[DailyForecast] = field(default_factory=list)  # Raw API data for icons/temps

@dataclass
class LLMInteraction:
    """Record of an LLM interaction for logging and replay."""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    weather_input: Dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    model_used: str = ""
    llm_output: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    source: str = ""