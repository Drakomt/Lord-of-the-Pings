# =============================
# server.py – TCP Chat Server (with usernames & join/leave)
# =============================
import socket
import threading

# ====== CHANGE HERE ======
HOST = '0.0.0.0'   # keep 0.0.0.0 to allow connections from other devices
PORT = 9000        # make sure this port is open / free
# =========================

clients = {}       # socket -> username
clients_lock = threading.Lock()


def broadcast(message, sender_socket=None):
    """Send message to all connected clients except sender"""
    with clients_lock:
        for client in list(clients.keys()):
            if client != sender_socket:
                try:
                    client.sendall(message.encode())
                except:
                    clients.pop(client, None)


def handle_client(client_socket, address):
    try:
        # First message = username
        username = client_socket.recv(1024).decode().strip()
        if not username:
            client_socket.close()
            return

        with clients_lock:
            clients[client_socket] = username

        print(f"[+] {username} joined from {address}")
        broadcast(f"*** {username} joined the chat ***")

        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            message = data.decode().strip()
            formatted = f"[{username}]: {message}"
            print(formatted)
            broadcast(formatted, client_socket)

    except:
        pass
    finally:
        with clients_lock:
            username = clients.pop(client_socket, 'Unknown')
        print(f"[-] {username} left the chat")
        broadcast(f"*** {username} left the chat ***")
        client_socket.close()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"[*] Server listening on {HOST}:{PORT}")

    while True:
        client_socket, address = server_socket.accept()
        thread = threading.Thread(
            target=handle_client,
            args=(client_socket, address),
            daemon=True
        )
        thread.start()


if __name__ == '__main__':
    main()
