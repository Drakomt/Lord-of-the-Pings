import json

from server.core import state


def send_json_message(sock, msg_type, data):
    """Send a JSON-encoded message to a specific client."""
    try:
        payload = {"type": msg_type, "data": data}
        sock.sendall((json.dumps(payload) + "\n").encode())
    except Exception:
        pass


def broadcast_json(msg_type, data, sender_socket=None):
    """Broadcast a JSON message to all clients except the sender."""
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
    """Parse incoming JSON message, return dict or None."""
    try:
        return json.loads(raw_string)
    except Exception:
        return None
