"""Client configuration for Lord of the Pings.

Loads environment variables and sets discovery/connection parameters for
locating the server on the local network or via explicit configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# UDP Discovery configuration
DISCOVERY_PORT = int(os.environ.get("DISCOVERY_PORT", "9001"))
DISCOVERY_TIMEOUT = 10
DISCOVERY_PREFIX = "LOTP_SERVER|"
DISCOVERY_RETRY_INTERVAL = int(os.environ.get("DISCOVERY_RETRY_INTERVAL", "2"))

# Server connection configuration with environment variable overrides
ENV_HOST = os.environ.get("HOST")
# Default to 9000 if not specified
ENV_PORT = os.environ.get("SERVER_PORT", "9000")
USE_ENV_OVERRIDE = ENV_HOST is not None  # Use env override if HOST is set

# Tic-Tac-Toe default server port
DEFAULT_SERVER_PORT = int(os.environ.get("SERVER_PORT", "9000"))
