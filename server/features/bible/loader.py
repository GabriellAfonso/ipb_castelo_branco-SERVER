import json
from pathlib import Path
from typing import Any

BIBLES: dict[str, Any] = {}

_DATA_DIR = Path(__file__).parent / "data"


def load_bibles() -> None:
    for path in _DATA_DIR.glob("*.json"):
        with path.open(encoding="utf-8") as f:
            BIBLES[path.stem] = json.load(f)
