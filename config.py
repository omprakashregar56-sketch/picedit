"""Config loading/saving. Edit config.json (next to the exe) to change settings."""
import json
import os
import sys

DEFAULTS = {
    "app_name": "OM Picture Manager",
    "theme": "sunset",               # "sunset", "dark" or "light"
    "window_size": "1150x720",
    "last_dir": "",
    "jpeg_quality": 92,              # quality for normal Save As (JPG)
    "target_kb": 100,                # default value for "Save under KB"
    "autocrop_tolerance": 25,        # 0-100
    "preview_max_side": 1400,        # px, for fast slider preview
    "undo_limit": 15,
    "default_ratio": "Free",
    # custom crop ratios: name -> [w, h] or null for free
    "ratios": {
        "Free": None,
        "1:1": [1, 1],
        "4:3": [4, 3],
        "3:4": [3, 4],
        "3:2": [3, 2],
        "2:3": [2, 3],
        "16:9": [16, 9],
        "Passport 3.5x4.5": [35, 45],
    },
}


def project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_dir():
    """Folder where config.json lives (next to the exe when frozen)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return project_root()


def resource_path(rel):
    """Path to a bundled resource (works in source and in PyInstaller exe)."""
    base = getattr(sys, "_MEIPASS", project_root())
    return os.path.join(base, rel)


CONFIG_PATH = os.path.join(app_dir(), "config.json")


def load():
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            user = json.load(fh)
        if isinstance(user, dict):
            cfg.update(user)
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except OSError:
        pass
