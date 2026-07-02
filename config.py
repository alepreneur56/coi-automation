"""
config.py
---------
Central configuration for the local COI automation runtime.
All secrets live in .env (gitignored) — never hardcode them here.

Copy .env.example to .env and fill in the values.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv(path):
    """Minimal .env loader — no external dependency needed."""
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(os.path.join(BASE_DIR, ".env"))


def _require(name):
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(
            f"Missing required setting: {name}\n"
            f"Fill it in at: {os.path.join(BASE_DIR, '.env')} "
            f"(copy .env.example if .env doesn't exist yet)"
        )
    return value


def _bool(name, default):
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Microsoft Graph (Azure app registration — client credentials flow)
# ---------------------------------------------------------------------------
AZURE_TENANT_ID = _require("AZURE_TENANT_ID")
AZURE_CLIENT_ID = _require("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = _require("AZURE_CLIENT_SECRET")

# The mailbox the automation reads from and sends as
COI_MAILBOX = os.environ.get("COI_MAILBOX", "admin@clientpolicyhelp.com")

# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

# ---------------------------------------------------------------------------
# Email routing
# ---------------------------------------------------------------------------
# TEST MODE GUARD — flip to false in .env ONLY when ready to send to real
# clients. When true, every outbound client email is redirected to
# TEST_REDIRECT_TO and CC lists are stripped.
TEST_MODE = _bool("TEST_MODE", True)
TEST_REDIRECT_TO = os.environ.get("TEST_REDIRECT_TO", "alepreneur56@gmail.com")

# Always CC the producer (Alejandro) on every outbound email (when not in test mode)
PRODUCER_CC_EMAIL = os.environ.get("PRODUCER_CC_EMAIL", "alepreneur56@gmail.com")
# Where complex-review draft COIs go for manual review (never test-redirected)
REVIEW_RECIPIENT_EMAIL = os.environ.get("REVIEW_RECIPIENT_EMAIL", "alepreneur56@gmail.com")

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
TEMPLATES_DIR = os.environ.get("TEMPLATES_DIR", os.path.join(BASE_DIR, "templates"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "output"))
STATE_DIR = os.path.join(BASE_DIR, "state")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

for _d in (OUTPUT_DIR, STATE_DIR, LOGS_DIR):
    os.makedirs(_d, exist_ok=True)
