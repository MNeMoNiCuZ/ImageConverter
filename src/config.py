"""Config persistence for Image Converter. Saves/loads JSON next to the executable or script."""

import json
import os
import sys

DEFAULTS = {
    "overwrite": False,
    "auto_process": True,
    "output_formats": ["JPG"],
    "clear_on_drop": True,
    "save_log": False,
}


def _config_path():
    """Return the path to the config JSON file, next to the exe or script."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
    return os.path.join(base, "imageconverter_config.json")


def load():
    """Load config from disk, returning defaults for missing keys."""
    cfg = dict(DEFAULTS)
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update({k: saved[k] for k in DEFAULTS if k in saved})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save(cfg):
    """Save config dict to disk."""
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass
