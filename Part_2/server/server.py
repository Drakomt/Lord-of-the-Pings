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
    find_available_discovery_port,
    find_available_port,
)
from server.core.avatars import get_random_avatar, list_available_avatars
from server.core.protocol import broadcast_json, parse_json_message, send_json_message
from server.core import state


def get_local_ip():
    """Resolve a best-effort local IP used for outbound traffic."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


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
    broadcast_ip_label.configure(text=f"Discovery IP: {state.BROADCAST_IP}")


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
    """Process and validate avatar change request from a client.

    Verifies avatar exists in available avatars, updates server state,
    and broadcasts the change to all connected clients.

    Args:
        username: Username of the client changing avatar
        avatar_name: Name of the avatar file to switch to
        client_socket: Socket of the requesting client
    """
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
    """Send a private message to a specific user.

    Routes a message from one client to another by finding the target socket
    and sending the message. Notifies sender if target is not found.

    Args:
        sender_socket: Socket of the sending client
        target_username: Username of the recipient
        message: Message text to send
    """
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
    """Disconnect a client and clean up all related resources.

    Removes client from active connections, closes socket, cleans up avatar
    data, and broadcasts disconnect notification to remaining clients.

    Args:
        client_socket: Socket of the client to disconnect
    """
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
    """Process incoming JSON messages from a connected client.

    Routes different message types (CHAT, GAME_INVITE, GAME_MOVE, etc.) to
    appropriate handlers. Manages peer-to-peer communication and game state.

    Args:
        client_socket: Socket of the sending client
        username: Username of the client
        msg_obj: Parsed JSON message object with 'type' and 'data' fields
    """
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
    """Handle a new client connection and manage client lifecycle.

    Accepts client login, maintains connection, receives and routes messages,
    and handles graceful disconnection with cleanup.

    Args:
        client_socket: Socket of the new client connection
        address: Tuple (host, port) of the connecting client
    """
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

        # Receive messages from client in a loop
        buffer = ""
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            buffer += data.decode()

            # Process complete messages (delimited by newline)
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
    """Continuously broadcast server presence on local network via UDP.

    Sends JSON discovery messages at regular intervals to allow clients
    to automatically detect and connect to the server.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Allow sharing port with client's listening socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, 'SO_REUSEPORT'):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    while True:
        try:
            sock.sendto(state.DISCOVERY_MESSAGE.encode(),
                        ("<broadcast>", state.DISCOVERY_PORT))
        except Exception:
            pass
        time.sleep(DISCOVERY_INTERVAL)


def server_thread():
    """Main server thread - initialize and run TCP chat server.

    Finds available ports for the server and discovery, creates a listening
    socket, accepts client connections in a loop, and spawns handler threads.
    """
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

    state.BROADCAST_IP = get_local_ip()
    state.DISCOVERY_MESSAGE = json.dumps(
        {"type": "DISCOVERY", "data": {"port": state.SERVER_PORT, "ip": state.BROADCAST_IP}})

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, state.SERVER_PORT))
    server_socket.listen()

    update_server_info_label()
    log(f"[*] Server listening on {SERVER_HOST}:{state.SERVER_PORT}")

    # Accept client connections indefinitely
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
app.geometry("700x420")
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
server_host_label = ctk.CTkLabel(
    server_host_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
server_host_label.pack(padx=10, pady=10)

server_port_frame = ctk.CTkFrame(
    frame_top, fg_color=OTHER_COLOR, corner_radius=8, border_color=ACCENT_COLOR, border_width=1
)
server_port_label = ctk.CTkLabel(
    server_port_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
server_port_label.pack(padx=10, pady=10)

discovery_port_frame = ctk.CTkFrame(
    frame_top, fg_color=OTHER_COLOR, corner_radius=8, border_color=ACCENT_COLOR, border_width=1
)
discovery_port_label = ctk.CTkLabel(
    discovery_port_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
discovery_port_label.pack(padx=10, pady=10)

broadcast_ip_frame = ctk.CTkFrame(
    frame_top, fg_color=OTHER_COLOR, corner_radius=8, border_color=ACCENT_COLOR, border_width=1
)
broadcast_ip_label = ctk.CTkLabel(
    broadcast_ip_frame, text="", font=("Arial", 11, "bold"), text_color=TEXT_COLOR, fg_color=OTHER_COLOR
)
broadcast_ip_label.pack(padx=10, pady=10)

# Arrange the four bubbles in two rows: host | discovery IP on top, server port | discovery port below.
info_frames = [
    server_host_frame,
    broadcast_ip_frame,
    server_port_frame,
    discovery_port_frame,
]


def layout_info_bubbles(event=None):
    width = frame_top.winfo_width() or app.winfo_width()
    cols = 2 if width >= 420 else 1  # keep 2x2 normally; stack if extremely narrow
    for child in frame_top.grid_slaves():
        child.grid_forget()
    frame_top.grid_columnconfigure(
        tuple(range(cols)), weight=1, uniform="cols")
    frame_top.grid_rowconfigure((0, 1, 2, 3), weight=1)
    for idx, frame in enumerate(info_frames):
        row = idx // cols
        col = idx % cols
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")


frame_top.bind("<Configure>", layout_info_bubbles)
layout_info_bubbles()

# Layout
body_frame = ctk.CTkFrame(app, fg_color=BACKGROUND_COLOR, border_width=0)
body_frame.pack(fill="both", expand=True, padx=10, pady=10)
body_frame.grid_columnconfigure(0, weight=1, minsize=180)
body_frame.grid_columnconfigure(1, weight=2)
body_frame.grid_rowconfigure(0, weight=1)

frame_left = ctk.CTkFrame(body_frame, corner_radius=15,
                          fg_color=OTHER_COLOR, border_color=ACCENT_COLOR, border_width=1)
frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

frame_right = ctk.CTkFrame(
    body_frame, corner_radius=15, fg_color=OTHER_COLOR, border_color=ACCENT_COLOR, border_width=1)
frame_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

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
