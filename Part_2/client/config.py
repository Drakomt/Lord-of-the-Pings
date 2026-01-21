import os
from dotenv import load_dotenv

load_dotenv()

# Discovery configuration
DISCOVERY_PORT = 9001
DISCOVERY_TIMEOUT = 10
DISCOVERY_PREFIX = "LOTP_SERVER|"
DISCOVERY_RETRY_INTERVAL = int(os.environ.get("DISCOVERY_RETRY_INTERVAL", "3"))
DISCOVERY_FORCE_TIMEOUT = int(os.environ.get("DISCOVERY_FORCE_TIMEOUT", "20"))

# Server configuration and overrides
ENV_HOST = os.environ.get("HOST")
ENV_PORT = os.environ.get("SERVER_PORT")
USE_ENV_OVERRIDE = ENV_HOST is not None and ENV_PORT is not None
LOCALHOST_FALLBACK = os.environ.get(
    "LOCALHOST_FALLBACK", "true").lower() == "true"

# Tic-Tac-Toe defaults
DEFAULT_SERVER_PORT = int(os.environ.get("SERVER_PORT", "9000"))
