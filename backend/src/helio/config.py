"""Helio's own runtime settings.

Deliberately narrow: nothing here ever names an OKX credential. OKX auth is
owned entirely by the OKX Agent Trade Kit's local credential store, which
Helio never reads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class HelioSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HELIO_", env_file=".env", extra="forbid")

    mode: Literal["simulation", "live"] = "simulation"
    log_level: str = "info"
    risk_config_path: Path = Path("backend/config/risk_config.yaml")
    guard_config_path: Path = Path("backend/config/guard_config.yaml")
    db_path: Path = Path("backend/helio.sqlite3")
    service_port: int = 8787

    # Not configurable on purpose: the service must never bind beyond localhost.
    @property
    def service_host(self) -> str:
        return "127.0.0.1"


def get_settings() -> HelioSettings:
    return HelioSettings()
