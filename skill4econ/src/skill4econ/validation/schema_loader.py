from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "contracts" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Schema is not a JSON object: {path}")
    return data


def list_schemas() -> list[Path]:
    return sorted(SCHEMA_DIR.glob("*.schema.json"))
