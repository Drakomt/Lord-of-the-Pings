# =============================
# client_customtk.py – TCP Chat Client (Desktop GUI with CustomTkinter)
# =============================
import socket
import threading
import customtkinter as ctk

# ====== CHANGE HERE ======
SERVER_IP = '127.0.0.1'   # IP of the server machine
SERVER_PORT = 9000
USERNAME = 'DesktopUser'     # change per client
# ==========================


class ChatClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TCP Chat Client")
        self.geometry("500x600")

        # Chat display
        self.chat_box = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.chat_box.pack(expand=True, fill="both", padx=10, pady=10)

        # Bottom input area
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=10, pady=10)

        self.message_entry = ctk.CTkEntry(
            bottom, placeholder_text="Type a message...")
        self.message_entry.pack(
            side="left", expand=True, fill="x", padx=(0, 10))
        self.message_entry.bind("<Return>", lambda e: self.send_message())

        send_btn = ctk.CTkButton(
            bottom, text="Send", command=self.send_message)
        send_btn.pack(side="right")

        # TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((SERVER_IP, SERVER_PORT))

        # Send username
        self.sock.sendall(USERNAME.encode())

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_message(self):
        msg = self.message_entry.get().strip()
        if msg:
            try:
                print(f"Sending: {msg}")
                self_msg = msg + "\n"
                self.after(0, self.add_message, self_msg)
                self.sock.sendall(msg.encode())
            except:
                pass
            self.message_entry.delete(0, "end")

    def receive_messages(self):
        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                self.after(0, self.add_message, data.decode())
            except:
                break

    def add_message(self, msg):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", msg + "")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")


if __name__ == '__main__':
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ChatClient()
    app.mainloop()
