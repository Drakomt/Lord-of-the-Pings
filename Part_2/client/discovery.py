import os
import socket
import threading
import time

from client import config, state
from client.protocol import parse_json_message


def try_broadcast_discovery():
    """Discover server via UDP broadcast (JSON format)."""
    try:
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", config.DISCOVERY_PORT))
        sock.settimeout(1)

        start_time = time.time()
        while time.time() - start_time < config.DISCOVERY_TIMEOUT:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode()
                parsed = parse_json_message(message)
                if parsed and parsed.get("type") == "DISCOVERY":
                    port = parsed.get("data", {}).get("port")
                    if port:
                        sock.close()
                        return addr[0], port
            except socket.timeout:
                continue
            except Exception:
                break
        sock.close()
    except Exception:
        pass
    return None


def try_env_server():
    """Try to connect to server from environment variables."""
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
    """Find server via broadcast discovery or env override."""
    if config.USE_ENV_OVERRIDE:
        return config.ENV_HOST, int(config.ENV_PORT)
    return try_broadcast_discovery()


def start_discovery():
    """Start server discovery in a background thread."""
    def worker():
        state.DISCOVERY_START_TIME = time.time()
        timeout_action_taken = False

        if config.USE_ENV_OVERRIDE:
            state.HOST = config.ENV_HOST
            state.SERVER_PORT = int(config.ENV_PORT)
            state.DISCOVERED = True
            # Keep monitoring for fallback
        else:
            while not state.discovery_thread_stop:
                if (not timeout_action_taken) and (time.time() - state.DISCOVERY_START_TIME > config.DISCOVERY_FORCE_TIMEOUT):
                    timeout_action_taken = True
                    if config.LOCALHOST_FALLBACK:
                        fallback_port = config.DEFAULT_SERVER_PORT
                        state.HOST = "127.0.0.1"
                        state.SERVER_PORT = fallback_port
                        state.DISCOVERED = True
                        break
                result = find_server()
                if result:
                    server_ip, server_port = result
                    state.HOST = server_ip
                    state.SERVER_PORT = server_port
                    state.DISCOVERED = True
                    break
                if not state.discovery_thread_stop:
                    time.sleep(config.DISCOVERY_RETRY_INTERVAL)
            return

        while not state.discovery_thread_stop:
            if (not timeout_action_taken) and (time.time() - state.DISCOVERY_START_TIME > config.DISCOVERY_FORCE_TIMEOUT):
                timeout_action_taken = True
                if not server_online():
                    if config.LOCALHOST_FALLBACK:
                        fallback_port = config.DEFAULT_SERVER_PORT
                        state.HOST = "127.0.0.1"
                        state.SERVER_PORT = fallback_port
            if not state.discovery_thread_stop:
                time.sleep(config.DISCOVERY_RETRY_INTERVAL)

    threading.Thread(target=worker, daemon=True).start()


def stop_discovery():
    """Stop the discovery thread."""
    state.discovery_thread_stop = True


def restart_discovery():
    """Restart discovery after disconnect."""
    state.discovery_thread_stop = False
    start_discovery()


def server_online():
    """Check if server is online."""
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
