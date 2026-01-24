"""Server configuration for Lord of the Pings.

Loads environment variables for server host, ports, and discovery settings.
Includes GUI theme colors for the server admin interface.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Server connection configuration
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
PREFERRED_PORT = int(os.environ.get("SERVER_PORT", 9000))
SERVER_PORT_AUTO_FALLBACK = os.environ.get(
    "SERVER_PORT_AUTO_FALLBACK", "true").lower() == "true"

# UDP Discovery broadcast configuration
PREFERRED_DISCOVERY_PORT = int(os.environ.get("DISCOVERY_PORT", 9001))
DISCOVERY_INTERVAL = 2  # seconds between broadcasts

# Server admin GUI theme colors
BACKGROUND_COLOR = "#0E1020"
ACCENT_COLOR = "#4E8AFF"
HOVER_COLOR = "#3357A0"
OTHER_COLOR = "#1A1F3A"
TEXT_COLOR = "#F2F2F2"
