"""Radar PhD — monitor di posizioni di dottorato."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DB_PATH = ROOT / "data" / "radar.sqlite"
