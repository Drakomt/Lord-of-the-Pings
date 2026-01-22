"""Server discovery mechanism for Lord of the Pings client.

Implements UDP-based broadcast discovery to automatically locate the server
on the local network, with fallback to environment variables or localhost.
"""

import os
import select
import socket
import threading
import time

from client.config import config
from client.core import state
from client.core.protocol import parse_json_message


def try_broadcast_discovery():
    """Discover server via UDP broadcast with JSON protocol.

    Listens for DISCOVERY messages on multiple ports in parallel to handle
    cases where the preferred port is occupied by another application.

    Returns:
        Tuple of (server_ip, server_port) if found, None otherwise
    """
    # Try listening on multiple ports (configurable via DISCOVERY_PORT_COUNT)
    ports_to_try = [
        config.DISCOVERY_PORT + i for i in range(config.DISCOVERY_PORT_COUNT)
    ]

    sockets = []

    # Create listening sockets on all available ports
    for port in ports_to_try:
        try:
            sock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            # Allow multiple sockets to bind same port for broadcasts
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(("", port))
            sock.setblocking(False)  # Non-blocking for select()
            sockets.append(sock)
        except OSError:
            # Port truly occupied by another app without SO_REUSEPORT, skip it
            pass

    if not sockets:
        return None

    # Listen on all sockets in parallel (short timeout for responsive checking)
    start_time = time.time()

    while time.time() - start_time < config.DISCOVERY_TIMEOUT:
        # Wait for data on any socket (0.5 second timeout per iteration)
        readable, _, _ = select.select(sockets, [], [], 0.5)

        for sock in readable:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode()
                parsed = parse_json_message(message)
                if parsed and parsed.get("type") == "DISCOVERY":
                    port = parsed.get("data", {}).get("port")
                    if port:
                        # Clean up all sockets
                        for s in sockets:
                            try:
                                s.close()
                            except Exception:
                                pass
                        return addr[0], port
            except Exception:
                pass

    # Clean up all sockets
    for sock in sockets:
        try:
            sock.close()
        except Exception:
            pass

    return None


def try_env_server():
    """Try to connect to server from environment variables.

    Returns:
        Tuple of (server_ip, server_port) from env, None if unavailable
    """
    env_host = os.environ.get("HOST", "127.0.0.1")
    env_port = int(os.environ.get("SERVER_PORT", 9000))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((env_host, env_port))
        sock.close()
        return env_host, env_port
    except Exception:
        return None


def find_server():
    """Find server using configured discovery method.

    Returns:
        Tuple of (server_ip, server_port) if found, None otherwise
    """
    if config.USE_ENV_OVERRIDE:
        return config.ENV_HOST, int(config.ENV_PORT)
    return try_broadcast_discovery()


def start_discovery():
    """Start server discovery in a background thread.

    Tries to find the server via UDP broadcast or environment override.
    If using ENV override, sets that immediately. Otherwise, searches network.
    """

    def worker():
        """Background worker thread for server discovery."""
        while not state.discovery_thread_stop:
            # Try to discover (env override wins, otherwise broadcast)
            if config.USE_ENV_OVERRIDE:
                state.HOST = config.ENV_HOST
                state.SERVER_PORT = int(config.ENV_PORT)
                state.DISCOVERED = True
            else:
                result = find_server()
                if result:
                    server_ip, server_port = result
                    state.HOST = server_ip
                    state.SERVER_PORT = server_port
                    state.DISCOVERED = True

            # If we have a target, stop this discovery thread
            if state.DISCOVERED or state.discovery_thread_stop:
                break

            # Retry interval before next attempt
            time.sleep(config.DISCOVERY_RETRY_INTERVAL)

    threading.Thread(target=worker, daemon=True).start()


def stop_discovery():
    """Signal the discovery thread to stop."""
    state.discovery_thread_stop = True


def restart_discovery():
    """Restart discovery after disconnect."""
    state.discovery_thread_stop = False
    start_discovery()


def server_online():
    """Check if server is currently online and reachable.

    Returns:
        True if server responds to connection attempt, False otherwise
    """
    if state.HOST is None or state.SERVER_PORT is None:
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.8)
        sock.connect((state.HOST, state.SERVER_PORT))
        sock.close()
        return True
    except Exception:
        return False
