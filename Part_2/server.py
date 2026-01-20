# server.py
# TCP Chat Server with CustomTkinter GUI
# - Shows online users
# - Allows disconnecting users by click
# - Clean, readable, modern UI

import socket
import threading
import random
import os
import time
import customtkinter as ctk
from dotenv import load_dotenv

load_dotenv()

# ====== SERVER CONFIG ======
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
PREFERRED_PORT = int(os.environ.get("SERVER_PORT", 9000))
SERVER_PORT = None
SERVER_PORT_AUTO_FALLBACK = os.environ.get(
    "SERVER_PORT_AUTO_FALLBACK", "true").lower() == "true"

# ====== DISCOVERY CONFIG ======
PREFERRED_DISCOVERY_PORT = int(os.environ.get("DISCOVERY_PORT", 9001))
DISCOVERY_PORT_AUTO_FALLBACK = os.environ.get(
    "DISCOVERY_PORT_AUTO_FALLBACK", "true").lower() == "true"

DISCOVERY_PORT = None
DISCOVERY_INTERVAL = 2  # seconds
DISCOVERY_MESSAGE = None
# =============================

BACKGROUND_COLOR = "#0E1020"
ACCENT_COLOR = "#4E8AFF"
HOVER_COLOR = "#3357A0"
OTHER_COLOR = "#1A1F3A"
TEXT_COLOR = "#F2F2F2"


def find_available_port(start_port, max_attempts=50, allow_fallback=True):
    """
    Find an available port starting from start_port.
    Tries up to max_attempts different ports.
    Returns the available port number, or None if none found.
    """
    if allow_fallback:
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Use for port reuse
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


def find_available_discovery_port(start_port=9001, max_attempts=50, allow_fallback=True):
    """
    Find an available UDP port for discovery broadcasts.
    If allow_fallback is False, only tries the exact start_port (no increment).
    """
    if allow_fallback:
        # Try incrementing ports if needed
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.bind(("", port))
                test_socket.close()
                return port
            except OSError:
                continue
    else:
        # Only try the exact port (manual override from env)
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.bind(("", start_port))
            test_socket.close()
            return start_port
        except OSError:
            return None

    return None


clients = {}        # socket -> username
clients_lock = threading.Lock()
user_avatars = {}   # username -> avatar filename


def discovery_broadcast_thread():
    """
    Periodically broadcast server presence on the local network
    so clients can auto-discover the server IP and port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        try:
            sock.sendto(
                DISCOVERY_MESSAGE.encode(),
                ("<broadcast>", DISCOVERY_PORT)
            )
        except:
            pass
        time.sleep(DISCOVERY_INTERVAL)


def get_random_avatar():
    avatars_dir = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "assets", "avatars")
    try:
        avatars = [f for f in os.listdir(avatars_dir) if f.endswith(".png")]
        return random.choice(avatars) if avatars else None
    except:
        return None


def list_available_avatars():
    avatars_dir = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "assets", "avatars")
    try:
        return [f for f in os.listdir(avatars_dir) if f.endswith(".png")]
    except:
        return []

# ================= SERVER LOGIC =================


def broadcast(message, sender_socket=None):
    with clients_lock:
        for client in list(clients.keys()):
            if client != sender_socket:
                try:
                    client.sendall((message + "\n").encode())
                except:
                    disconnect_client(client)


def broadcast_user_list():
    with clients_lock:
        usernames = list(clients.values())
    broadcast("USERLIST|" + ",".join(usernames))


def broadcast_avatars():
    for username, avatar in user_avatars.items():
        if avatar:
            broadcast(f"AVATAR|{username}|{avatar}")


def broadcast_avatars_to_client(client_socket):
    """Send all current avatars to a specific new client"""
    for username, avatar in user_avatars.items():
        if avatar:
            try:
                client_socket.sendall(f"AVATAR|{username}|{avatar}\n".encode())
            except:
                pass


def broadcast_new_user_avatar(username):
    """Broadcast only the new user's avatar to existing clients (not to themselves)"""
    avatar = user_avatars.get(username)
    if avatar:
        broadcast(f"AVATAR|{username}|{avatar}")


def handle_avatar_change(username, avatar_name, client_socket):
    available = list_available_avatars()
    if avatar_name not in available:
        try:
            client_socket.sendall(b"AVATAR_ERROR|invalid\n")
        except:
            disconnect_client(client_socket)
        return

    with clients_lock:
        user_avatars[username] = avatar_name
    broadcast(f"AVATAR|{username}|{avatar_name}")


def send_private(sender_socket, target_username, message):
    with clients_lock:
        sender_name = clients.get(sender_socket, "unknown")
        target_socket = next(
            (sock for sock, user in clients.items() if user == target_username),
            None,
        )

    if not target_socket:
        try:
            sender_socket.sendall(
                (f"*** User {target_username} not found ***\n").encode())
        except:
            disconnect_client(sender_socket)
        return

    payload = f"[PM {sender_name} -> {target_username}]: {message}"
    for sock in (target_socket, sender_socket):  # echo to sender for context
        try:
            sock.sendall((payload + "\n").encode())
        except:
            disconnect_client(sock)


def disconnect_client(client_socket):
    with clients_lock:
        username = clients.pop(client_socket, None)
    try:
        client_socket.close()
    except:
        pass
    if username:
        user_avatars.pop(username, None)
        log(f"[-] {username} disconnected")
        broadcast(f"*** {username} left the chat ***")
        update_user_list()
        broadcast_user_list()


def handle_client(client_socket, address):
    try:
        username = client_socket.recv(1024).decode().strip()
        if not username:
            client_socket.close()
            return

        with clients_lock:
            if username in clients.values():
                client_socket.sendall("Username already taken".encode())
                client_socket.close()
                return
            clients[client_socket] = username
            avatar = get_random_avatar()
            user_avatars[username] = avatar

        log(f"[+] {username} joined from {address}")
        broadcast(f"*** {username} joined the chat ***")
        update_user_list()
        broadcast_user_list()

        # Send ALL avatars to the new client first (including their own)
        broadcast_avatars_to_client(client_socket)

        # Then send only the new user's avatar to existing clients
        broadcast_new_user_avatar(username)

        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode().strip()
            if message.startswith("SET_AVATAR|"):
                _, avatar_name = message.split("|", 1)
                handle_avatar_change(username, avatar_name, client_socket)
                continue
            if message.startswith("@"):  # format: @target message
                parts = message.split(" ", 1)
                if len(parts) == 2 and parts[0][1:]:
                    send_private(client_socket, parts[0][1:], parts[1])
                else:
                    try:
                        client_socket.sendall(
                            b"*** Invalid private message format. Use @username message ***\n")
                    except:
                        disconnect_client(client_socket)
                continue

            broadcast(f"{username}: {message}", client_socket)

    except:
        pass
    finally:
        disconnect_client(client_socket)


def server_thread():
    global SERVER_PORT, DISCOVERY_PORT, DISCOVERY_MESSAGE

    # Find available port for main server (respect env strictness)
    SERVER_PORT = find_available_port(
        PREFERRED_PORT, allow_fallback=SERVER_PORT_AUTO_FALLBACK)
    if SERVER_PORT is None:
        log(
            f"[ERROR] Could not find available port starting from {PREFERRED_PORT}")
        return

    # Find available port for discovery (respects env variable override)
    DISCOVERY_PORT = find_available_discovery_port(
        PREFERRED_DISCOVERY_PORT,
        allow_fallback=DISCOVERY_PORT_AUTO_FALLBACK
    )
    if DISCOVERY_PORT is None:
        if not DISCOVERY_PORT_AUTO_FALLBACK:
            log(
                f"[ERROR] Discovery port {PREFERRED_DISCOVERY_PORT} (from env) is in use and no fallback allowed")
        else:
            log(
                f"[ERROR] Could not find available discovery port starting from {PREFERRED_DISCOVERY_PORT}")
        return

    # Set the discovery message now that we know the ports
    DISCOVERY_MESSAGE = f"LOTP_SERVER|{SERVER_PORT}"

    # Log requested (preferred) vs actual (bound) ports for clarity
    log(f"Requested server port: {PREFERRED_PORT} (strict={not SERVER_PORT_AUTO_FALLBACK})")
    log(f"Bound server port: {SERVER_PORT}")
    log(f"Requested discovery port: {PREFERRED_DISCOVERY_PORT} (strict={not DISCOVERY_PORT_AUTO_FALLBACK})")
    log(f"Bound discovery port: {DISCOVERY_PORT}")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen()

    log(f"[*] Server listening on {SERVER_HOST}:{SERVER_PORT}")
    log(f"[*] Discovery broadcasting on port {DISCOVERY_PORT}")

    while True:
        client_socket, address = server_socket.accept()
        threading.Thread(
            target=handle_client,
            args=(client_socket, address),
            daemon=True
        ).start()

# ================= GUI =================


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Lotp Server")
app.geometry("600x420")
app.configure(fg_color=BACKGROUND_COLOR)
icon_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "assets/icons/Lotp_Icon_BP.ico")
app.iconbitmap(icon_path)

# ----- Layout -----
frame_left = ctk.CTkFrame(app, width=200, corner_radius=15,
                          fg_color=OTHER_COLOR, border_color=ACCENT_COLOR, border_width=1)
frame_left.pack(side="left", fill="y", padx=10, pady=10)

frame_right = ctk.CTkFrame(
    app, corner_radius=15, fg_color=OTHER_COLOR, border_color=ACCENT_COLOR, border_width=1)
frame_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

# ----- Online Users -----
label_users = ctk.CTkLabel(
    frame_left, text="Online Users", font=("Arial", 16, "bold"), text_color=TEXT_COLOR)
label_users.pack(pady=(10, 5))

users_list = ctk.CTkScrollableFrame(
    frame_left, height=300, fg_color=BACKGROUND_COLOR)
users_list.pack(fill="both", expand=True, padx=5, pady=5)

# ----- Log -----
label_log = ctk.CTkLabel(frame_right, text="Server Log",
                         font=("Arial", 16, "bold"), text_color=TEXT_COLOR)
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

# ================= GUI HELPERS =================


def log(text):
    log_box.configure(state="normal")
    log_box.insert("end", text + "\n")
    log_box.configure(state="disabled")
    log_box.see("end")


def update_user_list():
    for widget in users_list.winfo_children():
        widget.destroy()

    with clients_lock:
        for sock, username in clients.items():
            btn = ctk.CTkButton(
                users_list,
                text=username,
                fg_color=ACCENT_COLOR,
                hover_color=HOVER_COLOR,
                text_color=TEXT_COLOR,
                command=lambda s=sock: disconnect_client(s)
            )
            btn.pack(fill="x", padx=5, pady=4)

# ================= START =================


threading.Thread(target=server_thread, daemon=True).start()
threading.Thread(target=discovery_broadcast_thread, daemon=True).start()
app.mainloop()
