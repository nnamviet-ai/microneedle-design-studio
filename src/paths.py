"""Resolve assets relative to this deployment, independent of working directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
