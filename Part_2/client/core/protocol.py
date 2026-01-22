"""Client-side network protocol utilities for Lord of the Pings.

Provides functions to send and receive JSON-formatted messages over sockets,
enabling structured communication with the server.
"""

import json

from client.core import state


def send_json_message(sock, msg_type, data):
    """Send a JSON-encoded message through the socket.

    Args:
        sock: Socket to send through
        msg_type: Type/command of the message (e.g., "CHAT", "GAME_MOVE")
        data: Dictionary of message data to be JSON-encoded

    Raises:
        Exception: On socket errors (logged but not re-raised)
    """
    try:
        payload = {"type": msg_type, "data": data}
        sock.sendall((json.dumps(payload) + "\n").encode())
    except Exception as exc:
        print(f"Error sending JSON message: {exc}")


def parse_json_message(raw_string):
    """Parse a JSON message string.

    Args:
        raw_string: Raw string to parse

    Returns:
        Dictionary with parsed JSON, or None if parsing fails
    """
    try:
        return json.loads(raw_string)
    except Exception:
        return None
