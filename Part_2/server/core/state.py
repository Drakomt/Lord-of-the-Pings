"""Global server state management for Lord of the Pings.

Maintains shared state for connected clients, their usernames, avatars,
and server port information. Uses threading locks for thread-safe access.
"""

import threading

# Global server state - maps socket to username for all connected clients
clients = {}
clients_lock = threading.Lock()

# Maps username to selected avatar filename
user_avatars = {}

# Server port tracking (will be set by server_thread at startup)
SERVER_PORT = None
DISCOVERY_PORT = None
DISCOVERY_MESSAGE = None
