"""Server-side network protocol utilities for Lord of the Pings.

Handles JSON message creation, transmission to single clients or broadcasts,
and parsing of incoming messages from connected clients.
"""

import json

from server.core import state


def send_json_message(sock, msg_type, data):
    """Send a JSON-encoded message to a specific client.

    Args:
        sock: Socket of the destination client
        msg_type: Message type/command identifier
        data: Dictionary of message data to be JSON-encoded
    """
    try:
        payload = {"type": msg_type, "data": data}
        sock.sendall((json.dumps(payload) + "\n").encode())
    except Exception:
        pass


def broadcast_json(msg_type, data, sender_socket=None):
    """Broadcast a JSON message to all clients except the sender.

    Args:
        msg_type: Message type/command identifier
        data: Dictionary of message data to be JSON-encoded
        sender_socket: Socket of originating client to exclude, or None
    """
    payload = {"type": msg_type, "data": data}
    message = json.dumps(payload) + "\n"
    with state.clients_lock:
        for client in list(state.clients.keys()):
            if client != sender_socket:
                try:
                    client.sendall(message.encode())
                except Exception:
                    pass


def parse_json_message(raw_string):
    """Parse incoming JSON message from client.

    Args:
        raw_string: Raw message string to parse

    Returns:
        Parsed dictionary if valid JSON, None otherwise
    """
    try:
        return json.loads(raw_string)
    except Exception:
        return None
