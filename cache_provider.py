"""Factory helpers and utilities for shared cache instances."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional
import json
import hashlib

import diskcache


def create_cache(cache_dir: Path, *, size_limit_bytes: Optional[int] = None) -> diskcache.Cache:
    """Return a configured diskcache instance.

    Parameters
    ----------
    cache_dir:
        Directory where cache data should be stored. The directory is
        created if it does not already exist.
    size_limit_bytes:
        Optional hard limit for cache size. ``None`` keeps the library default.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = diskcache.Cache(cache_dir)
    if size_limit_bytes is not None:
        cache.cull_limit = 10  # Cull aggressively when exceeding limit.
        cache.size_limit = size_limit_bytes
    return cache


def make_cache_key(prefix: str, *components: Iterable[Any]) -> str:
    """Build a stable cache key from heterogeneous inputs."""

    parts = [prefix]
    for component in components:
        if isinstance(component, dict):
            encoded = json.dumps(component, sort_keys=True, separators=(",", ":")).encode()
            digest = hashlib.sha256(encoded).hexdigest()[:16]
            parts.append(digest)
        elif isinstance(component, (list, tuple, set)):
            encoded = json.dumps(list(component)).encode()
            digest = hashlib.sha256(encoded).hexdigest()[:16]
            parts.append(digest)
        elif isinstance(component, str) and len(component) > 48:
            digest = hashlib.sha256(component.encode()).hexdigest()[:16]
            parts.append(digest)
        else:
            parts.append(str(component))
    return "_".join(parts)
