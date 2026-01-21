"""Lord of the Pings - Chat Server with Tic-Tac-Toe Game."""

import json
import socket
import threading
import time
import sys
from pathlib import Path

# Ensure package imports work even when run as `python server.py` from the server folder.
if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parent.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    __package__ = "server"

import customtkinter as ctk

from server.avatars import get_random_avatar, list_available_avatars
from server.config import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    DISCOVERY_INTERVAL,
    HOVER_COLOR,
    OTHER_COLOR,
    PREFERRED_DISCOVERY_PORT,
    PREFERRED_PORT,
    SERVER_HOST,
    TEXT_COLOR,
    DISCOVERY_PORT_AUTO_FALLBACK,
    SERVER_PORT_AUTO_FALLBACK,
)
from server.ports import find_available_discovery_port, find_available_port
from server.protocol import broadcast_json, parse_json_message, send_json_message
from server import state


def update_user_list():
    """Update the displayed user list in the GUI."""
    for widget in users_list.winfo_children():
        widget.destroy()

    with state.clients_lock:
        for sock, username in state.clients.items():
            btn = ctk.CTkButton(
                users_list,
                text=username,
                fg_color=ACCENT_COLOR,
                hover_color=HOVER_COLOR,
                text_color=TEXT_COLOR,
                command=lambda s=sock: disconnect_client(s),
            )
            btn.pack(fill="x", padx=5, pady=4)


def update_server_info_label():
    """Update the server info labels with host, server port, and discovery port."""
    server_host_label.configure(text=f"Host: {SERVER_HOST}")
    server_port_label.configure(text=f"Server Port: {state.SERVER_PORT}")
    discovery_port_label.configure(
        text=f"Discovery Port: {state.DISCOVERY_PORT}")


def log(text):
    """Log text to the server log textbox."""
    log_box.configure(state="normal")
    log_box.insert("end", text + "\n")
    log_box.configure(state="disabled")
    log_box.see("end")


def broadcast_user_list():
    """Broadcast the current user list to all connected clients."""
    with state.clients_lock:
        usernames = list(state.clients.values())
    broadcast_json("USERLIST", {"users": usernames})


def broadcast_avatars():
    """Broadcast all avatars to all clients."""
    for username, avatar in state.user_avatars.items():
        if avatar:
            broadcast_json("AVATAR", {"username": username, "avatar": avatar})


def broadcast_avatars_to_client(client_socket):
    """Send all current avatars to a specific new client."""
    for username, avatar in state.user_avatars.items():
        if avatar:
            try:
                send_json_message(client_socket, "AVATAR", {
                                  "username": username, "avatar": avatar})
            except Exception:
                pass


def broadcast_new_user_avatar(username):
    """Broadcast only the new user's avatar to existing clients."""
    avatar = state.user_avatars.get(username)
    if avatar:
        broadcast_json("AVATAR", {"username": username, "avatar": avatar})


def handle_avatar_change(username, avatar_name, client_socket):
    """Handle avatar change request from a client."""
    available = list_available_avatars()
    if avatar_name not in available:
        try:
            send_json_message(client_socket, "AVATAR_ERROR", {})
        except Exception:
            disconnect_client(client_socket)
        return

    with state.clients_lock:
        state.user_avatars[username] = avatar_name
    broadcast_json("AVATAR", {"username": username, "avatar": avatar_name})


def send_private(sender_socket, target_username, message):
    """Send a private message to a specific user."""
    with state.clients_lock:
        sender_name = state.clients.get(sender_socket, "unknown")
        target_socket = next(
            (sock for sock, user in state.clients.items() if user == target_username),
            None,
        )

    if not target_socket:
        try:
            send_json_message(sender_socket, "SYSTEM", {
                              "text": f"User {target_username} not found", "chat_id": "general"})
        except Exception:
            disconnect_client(sender_socket)
        return

    try:
        send_json_message(
            target_socket,
            "CHAT",
            {"sender": sender_name, "recipient": target_username, "text": message},
        )
    except Exception:
        disconnect_client(target_socket)


def disconnect_client(client_socket):
    """Disconnect a client and clean up."""
    with state.clients_lock:
        username = state.clients.pop(client_socket, None)
    try:
        client_socket.close()
    except Exception:
        pass
    if username:
        state.user_avatars.pop(username, None)
        log(f"[-] {username} disconnected")
        broadcast_json(
            "SYSTEM", {"text": f"{username} left the chat", "chat_id": "general"})
        update_user_list()
        broadcast_user_list()


def handle_json_message(client_socket, username, msg_obj):
    """Handle incoming JSON messages from client."""
    try:
        msg_type = msg_obj.get("type", "")
        data = msg_obj.get("data", {})

        if msg_type == "CHAT":
            sender = data.get("sender", username)
            recipient = data.get("recipient", "general")
            text = data.get("text", "")

            if recipient == "general":
                broadcast_json("CHAT", {
                               "sender": sender, "recipient": "general", "text": text}, sender_socket=client_socket)
            else:
                send_private(client_socket, recipient, text)

        elif msg_type == "SET_AVATAR":
            avatar_name = data.get("avatar", "")
            if avatar_name:
                handle_avatar_change(username, avatar_name, client_socket)

        elif msg_type == "GAME_INVITE":
            opponent = data.get("opponent", "")
            if opponent:
                with state.clients_lock:
                    target_socket = next(
                        (sock for sock, user in state.clients.items()
                         if user == opponent),
                        None,
                    )
                if target_socket:
                    send_json_message(target_socket, "GAME_INVITE", {
                                      "opponent": username})

        elif msg_type == "GAME_ACCEPTED":
            player = data.get("player", username)
            symbol = data.get("symbol", "X")
            opponent = data.get("opponent", "")
            if opponent:
                with state.clients_lock:
                    target_socket = next(
                        (sock for sock, user in state.clients.items()
                         if user == opponent),
                        None,
                    )
                if target_socket:
                    send_json_message(target_socket, "GAME_ACCEPTED", {
                                      "player": player, "symbol": symbol})

        elif msg_type == "GAME_MOVE":
            board = data.get("board", [])
            current_player = data.get("current_player", "X")
            opponent = data.get("opponent", "")
            if opponent:
                with state.clients_lock:
                    target_socket = next(
                        (sock for sock, user in state.clients.items()
                         if user == opponent),
                        None,
                    )
                if target_socket:
                    send_json_message(target_socket, "GAME_MOVE", {
                                      "board": board, "current_player": current_player})

        elif msg_type == "GAME_END":
            result = data.get("result", "DRAW")
            opponent = data.get("opponent", "")
            if opponent:
                with state.clients_lock:
                    target_socket = next(
                        (sock for sock, user in state.clients.items()
                         if user == opponent),
                        None,
                    )
                if target_socket:
                    send_json_message(target_socket, "GAME_END", {
                                      "result": result})

        elif msg_type == "GAME_RESET":
            player = data.get("player", username)
            symbol = data.get("symbol", "X")
            opponent = data.get("opponent", "")
            if opponent:
                with state.clients_lock:
                    target_socket = next(
                        (sock for sock, user in state.clients.items()
                         if user == opponent),
                        None,
                    )
                if target_socket:
                    send_json_message(target_socket, "GAME_RESET", {
                                      "player": player, "symbol": symbol})

        elif msg_type == "GAME_LEFT":
            player = data.get("player", username)
            opponent = data.get("opponent", "")
            if opponent:
                with state.clients_lock:
                    target_socket = next(
                        (sock for sock, user in state.clients.items()
                         if user == opponent),
                        None,
                    )
                if target_socket:
                    send_json_message(target_socket, "GAME_LEFT", {
                                      "player": player})

    except Exception as exc:
        log(f"Error handling JSON message from {username}: {exc}")


def handle_client(client_socket, address):
    """Handle a new client connection."""
    username = None
    try:
        username = client_socket.recv(1024).decode().strip()
        if not username:
            client_socket.close()
            return

        with state.clients_lock:
            if username in state.clients.values():
                client_socket.sendall("Username already taken".encode())
                client_socket.close()
                return
            state.clients[client_socket] = username
            avatar = get_random_avatar()
            state.user_avatars[username] = avatar

        log(f"[+] {username} joined from {address}")
        broadcast_json(
            "SYSTEM", {"text": f"{username} joined the chat", "chat_id": "general"})
        update_user_list()
        broadcast_user_list()
        broadcast_avatars_to_client(client_socket)
        broadcast_new_user_avatar(username)

        broadcast_avatars_to_client(client_socket)
        broadcast_new_user_avatar(username)

        buffer = ""
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            buffer += data.decode()

            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                message = message.strip()
                if not message:
                    continue

                parsed = parse_json_message(message)
                if parsed:
                    handle_json_message(client_socket, username, parsed)
                else:
                    log(
                        f"[WARN] Dropping non-JSON message from {username}: {message[:80]}")

    except Exception:
        pass
    finally:
        disconnect_client(client_socket)


def discovery_broadcast_thread():
    """Periodically broadcast server presence on the local network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        try:
            sock.sendto(state.DISCOVERY_MESSAGE.encode(),
                        ("<broadcast>", state.DISCOVERY_PORT))
        except Exception:
            pass
        time.sleep(DISCOVERY_INTERVAL)


def server_thread():
    """Main server thread."""
    # Resolve server and discovery ports (with fallback if allowed)
    state.SERVER_PORT = find_available_port(
        PREFERRED_PORT, allow_fallback=SERVER_PORT_AUTO_FALLBACK)
    if state.SERVER_PORT is None:
        log(
            f"[ERROR] Could not find available port starting from {PREFERRED_PORT}")
        return

    state.DISCOVERY_PORT = find_available_discovery_port(
        PREFERRED_DISCOVERY_PORT,
        allow_fallback=DISCOVERY_PORT_AUTO_FALLBACK,
    )
    if state.DISCOVERY_PORT is None:
        log(
            f"[ERROR] Could not find available discovery port starting from {PREFERRED_DISCOVERY_PORT}")
        return

    state.DISCOVERY_MESSAGE = json.dumps(
        {"type": "DISCOVERY", "data": {"port": state.SERVER_PORT}})

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, state.SERVER_PORT))

    def server_thread():
        """Main server thread."""
        # Initialize port configurations
        state.SERVER_PORT = find_available_port(
            PREFERRED_PORT, allow_fallback=SERVER_PORT_AUTO_FALLBACK)
        if state.SERVER_PORT is None:
            log(
                f"[ERROR] Could not find available port starting from {PREFERRED_PORT}")
            return

        state.DISCOVERY_PORT = find_available_discovery_port(
            PREFERRED_DISCOVERY_PORT,
            allow_fallback=DISCOVERY_PORT_AUTO_FALLBACK,
        )
        if state.DISCOVERY_PORT is None:
            log(
                f"[ERROR] Could not find available discovery port starting from {PREFERRED_DISCOVERY_PORT}")
            return

        state.DISCOVERY_MESSAGE = json.dumps(
            {"type": "DISCOVERY", "data": {"port": state.SERVER_PORT}})

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, state.SERVER_PORT))
    server_socket.listen()

    update_server_info_label()
    log(f"[*] Server listening on {SERVER_HOST}:{state.SERVER_PORT}")

    while True:
        client_socket, address = server_socket.accept()
        threading.Thread(
            target=handle_client,
            args=(client_socket, address),
            daemon=True,
        ).start()


# ================= GUI =================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Lotp Server")
app.geometry("600x420")
app.configure(fg_color=BACKGROUND_COLOR)

# Set window icon
icon_path = Path(__file__).parent / "assets" / "icons" / "Lotp_Icon_BP.ico"
try:
    if icon_path.exists():
        app.iconbitmap(str(icon_path))
except Exception:
    pass

# Server Info Labels
frame_top = ctk.CTkFrame(app, corner_radius=15,
                         fg_color=BACKGROUND_COLOR, border_width=0)
frame_top.pack(fill="x", padx=10, pady=(10, 5))

server_host_frame = ctk.CTkFrame(
    frame_top, fg_color=OTHER_COLOR, corner_radius=8, border_color=ACCENT_COLOR, border_width=1
)
server_host_frame.pack(side="left", padx=5, pady=10, fill="x", expand=True)
server_host_label = ctk.CTkLabel(
    server_host_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
server_host_label.pack(padx=10, pady=10)

server_port_frame = ctk.CTkFrame(
    frame_top, fg_color=OTHER_COLOR, corner_radius=8, border_color=ACCENT_COLOR, border_width=1
)
server_port_frame.pack(side="left", padx=5, pady=10, fill="x", expand=True)
server_port_label = ctk.CTkLabel(
    server_port_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
server_port_label.pack(padx=10, pady=10)

discovery_port_frame = ctk.CTkFrame(
    frame_top, fg_color=OTHER_COLOR, corner_radius=8, border_color=ACCENT_COLOR, border_width=1
)
discovery_port_frame.pack(side="left", padx=5, pady=10, fill="x", expand=True)
discovery_port_label = ctk.CTkLabel(
    discovery_port_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
discovery_port_label.pack(padx=10, pady=10)

# Layout
frame_left = ctk.CTkFrame(app, width=200, corner_radius=15,
                          fg_color=OTHER_COLOR, border_color=ACCENT_COLOR, border_width=1)
frame_left.pack(side="left", fill="y", padx=10, pady=10)

frame_right = ctk.CTkFrame(
    app, corner_radius=15, fg_color=OTHER_COLOR, border_color=ACCENT_COLOR, border_width=1)
frame_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

# Online Users
label_users = ctk.CTkLabel(frame_left, text="Online Users", font=(
    "Arial", 16, "bold"), text_color=TEXT_COLOR)
label_users.pack(pady=(10, 5))

users_list = ctk.CTkScrollableFrame(
    frame_left, height=300, fg_color=BACKGROUND_COLOR)
users_list.pack(fill="both", expand=True, padx=5, pady=5)

# Log
label_log = ctk.CTkLabel(frame_right, text="Server Log", font=(
    "Arial", 16, "bold"), text_color=TEXT_COLOR)
label_log.pack(pady=(10, 5))

log_box = ctk.CTkTextbox(
    frame_right,
    state="disabled",
    corner_radius=10,
    fg_color=BACKGROUND_COLOR,
    text_color=TEXT_COLOR,
    border_color=ACCENT_COLOR,
    border_width=1,
)
log_box.pack(fill="both", expand=True, padx=10, pady=10)

# ================= START =================

threading.Thread(target=server_thread, daemon=True).start()
threading.Thread(target=discovery_broadcast_thread, daemon=True).start()
app.mainloop()
