"""Reads .env once and exposes typed settings. Fails loudly on a bad config.

Nothing else in the app reads os.environ. Import `settings` from here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised at startup when a required variable is missing or unusable."""


def _get(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ConfigError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def _get_bool(name: str, default: str) -> bool:
    return _get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: str) -> int:
    raw = _get(name, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}.") from exc


@dataclass(frozen=True)
class Settings:
    use_mock: bool
    n8n_base_url: str
    process_path: str
    documents_path: str
    review_path: str
    analyze_path: str
    secret: str
    request_timeout_ms: int
    max_file_mb: int

    @property
    def request_timeout_s(self) -> float:
        return self.request_timeout_ms / 1000

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    def url_for(self, path: str) -> str:
        return f"{self.n8n_base_url.rstrip('/')}/{path.lstrip('/')}"


def _load() -> Settings:
    use_mock = _get_bool("USE_MOCK", "true")

    # These only have to be real when we actually call n8n.
    base_url = os.environ.get("N8N_BASE_URL", "")
    secret = os.environ.get("N8N_SECRET", "")
    if not use_mock:
        if not base_url:
            raise ConfigError("USE_MOCK=false but N8N_BASE_URL is not set.")
        if not secret or secret == "replace-me":
            raise ConfigError("USE_MOCK=false but N8N_SECRET is still a placeholder.")

    return Settings(
        use_mock=use_mock,
        n8n_base_url=base_url,
        process_path=_get("N8N_PROCESS_PATH", "/process-document"),
        documents_path=_get("N8N_DOCUMENTS_PATH", "/documents"),
        review_path=_get("N8N_REVIEW_PATH", "/review"),
        analyze_path=_get("N8N_ANALYZE_PATH", "/analyze"),
        secret=secret,
        request_timeout_ms=_get_int("REQUEST_TIMEOUT_MS", "90000"),
        max_file_mb=_get_int("MAX_FILE_MB", "10"),
    )


settings = _load()
