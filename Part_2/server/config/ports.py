"""Port discovery utilities for Lord of the Pings server.

Provides functions to find available TCP and UDP ports for the server
and discovery broadcast, with optional fallback behavior.
"""

import socket

from .config import (
    PREFERRED_DISCOVERY_PORT,
    PREFERRED_PORT,
    SERVER_HOST,
    SERVER_PORT_AUTO_FALLBACK,
    DISCOVERY_PORT_AUTO_FALLBACK,
)


def find_available_port(start_port, max_attempts=50, allow_fallback=True):
    """Find an available TCP port for the chat server.

    Attempts to bind a socket starting from start_port and incrementing
    until an available port is found or max_attempts is reached.

    Args:
        start_port: Port number to start search from
        max_attempts: Maximum number of ports to try
        allow_fallback: If True, search multiple ports; if False, try only start_port

    Returns:
        Available port number, or None if no port found
    """
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
    """Find an available UDP port for discovery broadcasts.

    Attempts to bind a UDP socket starting from start_port and incrementing
    until an available port is found or max_attempts is reached.

    Args:
        start_port: Port number to start search from
        max_attempts: Maximum number of ports to try
        allow_fallback: If True, search multiple ports; if False, try only start_port

    Returns:
        Available port number, or None if no port found
    """
    if allow_fallback:
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Use SO_REUSEADDR/SO_REUSEPORT to allow sharing with client's listener
                test_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, 'SO_REUSEPORT'):
                    test_socket.setsockopt(
                        socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                test_socket.bind(("", port))
                test_socket.close()
                return port
            except OSError:
                continue
    else:
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Use SO_REUSEADDR/SO_REUSEPORT to allow sharing with client's listener
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                test_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            test_socket.bind(("", start_port))
            test_socket.close()
            return start_port
        except OSError:
            return None
    return None
