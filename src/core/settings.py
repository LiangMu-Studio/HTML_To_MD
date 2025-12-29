import json
import sys
from pathlib import Path
from typing import Dict, Any

# 配置文件放在 EXE 所在目录
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent.parent.parent
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": "LIGHT",
    "output_dir": None,
    "recent_files": [],
    "last_browse_dir": "",
}


def load_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        merged = DEFAULT_SETTINGS.copy()
        merged.update({k: data.get(k) for k in DEFAULT_SETTINGS.keys()})
        return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(data: Dict[str, Any]) -> None:
    to_save = DEFAULT_SETTINGS.copy()
    to_save.update(data)
    SETTINGS_PATH.write_text(json.dumps(to_save, ensure_ascii=False, indent=2), encoding="utf-8")
