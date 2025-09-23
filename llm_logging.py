"""SQLite-based persistence for LLM interactions."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    location_name TEXT,
    weather_input TEXT,
    llm_context TEXT,
    system_prompt TEXT,
    model_used TEXT,
    llm_output TEXT,
    description TEXT,
    source TEXT
)
"""


@dataclass(slots=True)
class LLMInteractionLogger:
    """Utility for writing structured interaction logs."""

    database_path: Path

    def ensure_schema(self) -> None:
        """Create the backing table if it does not already exist."""

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(SCHEMA)
            # Legacy databases might be missing llm_context; add it idempotently.
            cursor = conn.execute("PRAGMA table_info(llm_interactions)")
            columns = {row[1] for row in cursor.fetchall()}
            if "llm_context" not in columns:
                conn.execute("ALTER TABLE llm_interactions ADD COLUMN llm_context TEXT")

    def log(
        self,
        *,
        weather_input: Dict[str, Any],
        llm_context: str,
        system_prompt: str,
        model_used: str,
        llm_output: Dict[str, Any],
        description: str,
        source: str,
        location_name: Optional[str] = None,
    ) -> None:
        """Persist a single LLM interaction."""

        payload = (
            location_name or "N/A",
            json.dumps(weather_input),
            llm_context,
            system_prompt,
            model_used,
            json.dumps(llm_output),
            description,
            source,
        )
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO llm_interactions (
                    location_name, weather_input, llm_context,
                    system_prompt, model_used, llm_output,
                    description, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
