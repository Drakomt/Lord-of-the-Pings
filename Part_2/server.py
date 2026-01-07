# server.py
# TCP Chat Server with CustomTkinter GUI
# - Shows online users
# - Allows disconnecting users by click
# - Clean, readable, modern UI

import socket
import threading
import os
import time
import customtkinter as ctk
from dotenv import load_dotenv

load_dotenv()

# ====== SERVER CONFIG ======
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 9000))
# ===========================

BACKGROUND_COLOR = "#0F1218"
ACCENT_COLOR = "#2E4A62"
OTHER_COLOR = "#2B2B2B"
TEXT_COLOR = "#F2F2F2"

# ====== DISCOVERY CONFIG ======
DISCOVERY_PORT = 9001
DISCOVERY_INTERVAL = 2  # seconds
DISCOVERY_MESSAGE = f"LOTP_SERVER|{SERVER_PORT}"
# =============================

clients = {}        # socket -> username
clients_lock = threading.Lock()


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

        log(f"[+] {username} joined from {address}")
        broadcast(f"*** {username} joined the chat ***")
        update_user_list()
        broadcast_user_list()

        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode().strip()
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
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen()

    log(f"[*] Server listening on {SERVER_HOST}:{SERVER_PORT}")

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
# app.iconbitmap("Lotp_Icon_O.ico") # Old way
icon_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "Lotp_Icon_O.ico")
app.iconbitmap(icon_path)

# ----- Layout -----
frame_left = ctk.CTkFrame(app, width=200, corner_radius=15,
                          fg_color="#111821", border_color=ACCENT_COLOR, border_width=1)
frame_left.pack(side="left", fill="y", padx=10, pady=10)

frame_right = ctk.CTkFrame(
    app, corner_radius=15, fg_color="#111821", border_color=ACCENT_COLOR, border_width=1)
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
                hover_color="#3B5D7B",
                text_color=TEXT_COLOR,
                command=lambda s=sock: disconnect_client(s)
            )
            btn.pack(fill="x", padx=5, pady=4)

# ================= START =================


threading.Thread(target=server_thread, daemon=True).start()
threading.Thread(target=discovery_broadcast_thread, daemon=True).start()
app.mainloop()
