import os
import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
os.environ.setdefault("CATALOG_MCP_URL", "http://catalog.test:8101/mcp/")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
