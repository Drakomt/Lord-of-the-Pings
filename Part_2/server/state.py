import threading

# Global server state
clients = {}
clients_lock = threading.Lock()
user_avatars = {}

# Server port tracking (will be set by server_thread)
SERVER_PORT = None
DISCOVERY_PORT = None
DISCOVERY_MESSAGE = None
