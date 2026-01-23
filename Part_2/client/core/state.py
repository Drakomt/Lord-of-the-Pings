"""Shared runtime state for the Lord of the Pings client.

Maintains global state about server discovery, connection details, and user
avatars that need to be accessible across multiple modules and screens.
"""

# Cached avatar assignments for all users (maps username -> avatar filename)
user_avatars = {}

# Server connection information discovered via broadcast or environment
HOST = None
SERVER_PORT = None

# Manual override state (takes precedence over discovery and env)
manual_override_mode = False
manual_override_ip = None
manual_override_port = None

# Discovery state tracking
DISCOVERED = False
DISCOVERY_START_TIME = None
discovery_thread_stop = False
