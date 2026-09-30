import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
os.environ.setdefault("SERVICEABILITY_MCP_URL", "http://serviceability.test:8102/mcp/")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
