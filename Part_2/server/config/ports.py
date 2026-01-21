import socket

from .config import (
    PREFERRED_DISCOVERY_PORT,
    PREFERRED_PORT,
    SERVER_HOST,
    SERVER_PORT_AUTO_FALLBACK,
    DISCOVERY_PORT_AUTO_FALLBACK,
)


def find_available_port(start_port, max_attempts=50, allow_fallback=True):
    """Find an available TCP port."""
    if allow_fallback:
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.bind((SERVER_HOST, port))
                test_socket.close()
                return port
            except OSError:
                continue
        return None
    else:
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.bind((SERVER_HOST, start_port))
            test_socket.close()
            return start_port
        except OSError:
            return None


def find_available_discovery_port(start_port=PREFERRED_DISCOVERY_PORT, max_attempts=50, allow_fallback=True):
    """Find an available UDP port for discovery broadcasts."""
    if allow_fallback:
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.bind(("", port))
                test_socket.close()
                return port
            except OSError:
                continue
    else:
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.bind(("", start_port))
            test_socket.close()
            return start_port
        except OSError:
            return None
    return None
