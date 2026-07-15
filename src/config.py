from pathlib import Path
import json
from constants import CONFIG_FILE

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def config_path() -> Path:
    return project_root() / CONFIG_FILE

DEFAULT_CONFIG = {
    "version": "1.0",
    "turismo_root": "",
    "last_country": "ARGENTINA",
    "last_province": "BUENOS AIRES",
    "last_city": "LA PLATA",
    "window_width": 1100,
    "window_height": 700
}

def load_config() -> dict:
    path = config_path()
    if not path.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = DEFAULT_CONFIG.copy()

    for key, value in DEFAULT_CONFIG.items():
        data.setdefault(key, value)

    return data

def save_config(data: dict) -> None:
    config_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )
