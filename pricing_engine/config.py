from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel


class Settings(BaseModel):
    vat: Dict[str, float]
    margin_pct: Dict[str, float]
    risk_pct: Dict[str, float]
    sanity: Dict[str, Any]
    file_paths: Dict[str, Any]


def load_settings(config_path: str | Path) -> Settings:
    config_path = Path(config_path)
    with config_path.open("r") as f:
        raw = yaml.safe_load(f)
    return Settings(**raw)
