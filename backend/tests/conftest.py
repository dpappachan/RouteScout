"""Shared pytest config. Nothing loaded here hits the network, graph file,
or Gemini — tests run in well under a second."""
import os
import sys
from pathlib import Path

# Make `backend.*` importable when running `pytest` from the repo root.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Prevent any accidental LLM call in a test from actually hitting the API.
os.environ.setdefault("GEMINI_API_KEY", "test-key-do-not-use")
