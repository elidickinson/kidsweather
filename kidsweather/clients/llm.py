"""LLM invocation utilities with optional fallback and caching."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ..infrastructure.cache import make_cache_key
from ..core.settings import LLMProviderSettings


@dataclass(slots=True)
class LLMClient:
    """High-level client that wraps a primary (and optional fallback) provider."""

    primary: LLMProviderSettings
    fallback: Optional[LLMProviderSettings] = None
    cache: Optional[Any] = None  # diskcache.Cache, but typed loosely for testing ease
    cache_ttl_seconds: int = 600

    def generate(
        self,
        context: Any,
        system_prompt: str,
        *,
        model_override: Optional[str] = None,
        api_key_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a response from the primary LLM (with fallback if configured)."""

        self.primary.require_complete("primary")
        cache_keys = []
        if self.cache:
            model = model_override or self.primary.model or "unknown"
            primary_key = make_cache_key("llm", [context, system_prompt, model])
            cache_keys.append(primary_key)
            if not model_override and self.fallback and self.fallback.is_configured():
                fallback_model = self.fallback.model or "unknown"
                cache_keys.append(
                    make_cache_key("llm", [context, system_prompt, fallback_model])
                )
            for key in cache_keys:
                cached = self.cache.get(key)
                if cached is not None:
                    return cached

        try:
            result = self._invoke_provider(
                provider=self.primary,
                context=context,
                system_prompt=system_prompt,
                model_override=model_override,
                api_key_override=api_key_override,
                provider_label="primary",
            )
        except Exception as exc:
            if not self.fallback:
                raise

            try:
                self.fallback.require_complete("fallback")
                result = self._invoke_provider(
                    provider=self.fallback,
                    context=context,
                    system_prompt=system_prompt,
                    model_override=None,  # Fallback uses its own configured model
                    api_key_override=None,
                    provider_label="fallback",
                )
            except Exception as fallback_exc:  # noqa: F841 - keep for error message clarity
                raise RuntimeError(
                    f"Primary LLM failed ({exc!r}) and fallback also failed ({fallback_exc!r})."
                ) from exc

        if self.cache:
            model_used = result.get("_model_used") or "unknown"
            cache_key = make_cache_key("llm", [context, system_prompt, model_used])
            self.cache.set(cache_key, result, expire=self.cache_ttl_seconds)
        return result

    def _invoke_provider(
        self,
        provider: LLMProviderSettings,
        *,
        context: Any,
        system_prompt: str,
        model_override: Optional[str],
        api_key_override: Optional[str],
        provider_label: str,
    ) -> Dict[str, Any]:
        """Call the configured provider and return parsed JSON output."""

        model = model_override or provider.model
        api_key = api_key_override or provider.api_key
        if not api_key:
            raise ValueError(f"Missing API key for {provider_label} LLM provider")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": context if isinstance(context, str) else json.dumps(context),
                },
            ],
            "stream": False,
        }
        if provider.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}

        if not provider.api_url:
            raise ValueError(f"API URL is required for {provider_label} LLM provider")

        response = requests.post(
            provider.api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=200,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LLM response did not include choices")

        raw_content = choices[0]["message"]["content"]
        content = self._normalise_content(raw_content)
        parsed = json.loads(content)
        parsed["_raw_llm_response"] = raw_content
        parsed["_model_used"] = model
        parsed["_provider_label"] = provider_label
        return parsed

    @staticmethod
    def _normalise_content(raw_content: str) -> str:
        """Strip provider-specific wrappers around JSON output."""

        content = raw_content.strip()
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        if content.startswith("temperature:"):
            content = content.split("temperature:", 1)[1].strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
