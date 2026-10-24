"""Vercel serverless entrypoint for FunnelBot."""
import os
import sys

# Ensure project root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app  # noqa: E402
