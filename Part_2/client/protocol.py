import json


def send_json_message(sock, msg_type, data):
    """Send a JSON-encoded message through socket."""
    try:
        payload = {"type": msg_type, "data": data}
        sock.sendall((json.dumps(payload) + "\n").encode())
    except Exception as exc:  # noqa: BLE001
        print(f"Error sending JSON message: {exc}")


def parse_json_message(raw_string):
    """Try to parse string as JSON, return dict or None."""
    try:
        return json.loads(raw_string)
    except Exception:  # noqa: BLE001
        return None
