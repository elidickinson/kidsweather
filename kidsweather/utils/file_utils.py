"""Utility helpers for reading and writing test fixtures."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.settings import load_settings


def save_weather_data(data: dict, filename: Optional[str] = None,*, directory: Optional[Path] = None) -> Path:
    """Persist raw weather data to disk for later replay or testing."""

    settings = load_settings()
    target_dir = directory or settings.paths.test_data_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weather_{timestamp}.json"

    path = target_dir / filename
    path.write_text(json.dumps(data, indent=2))
    return path


def load_weather_data(filename: str,*, directory: Optional[Path] = None) -> dict:
    """Load weather data previously saved for deterministic runs."""

    settings = load_settings()
    target_dir = directory or settings.paths.test_data_dir
    path = target_dir / filename
    return json.loads(path.read_text())
