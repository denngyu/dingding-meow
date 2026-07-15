"""Small atomic JSON settings store shared by independent features."""

import json
import threading
from pathlib import Path


_SETTINGS_LOCK = threading.RLock()


def _read_unlocked(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_settings(path):
    path = Path(path)
    with _SETTINGS_LOCK:
        return _read_unlocked(path)


def update_settings(path, **values):
    path = Path(path)
    with _SETTINGS_LOCK:
        data = _read_unlocked(path)
        data.update(values)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
        return data
