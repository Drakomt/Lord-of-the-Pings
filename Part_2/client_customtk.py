# =============================
# client_customtk.py – TCP Chat Client (Desktop GUI with CustomTkinter)
# =============================
import socket
import threading
import customtkinter as ctk
from customtkinter import CTk, CTkFrame, CTkLabel, CTkEntry, CTkButton
import tkinter as tk

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
        # Canvas + scrollbar for messages
        self.canvas = tk.Canvas(self.chat_frame, bg="#e5ddd5", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.chat_frame, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame = CTkFrame(self.canvas, fg_color="#e5ddd5")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Entry box
        self.entry = CTkEntry(root, placeholder_text="Type a message...")
        self.entry.pack(fill="x", padx=5, pady=(5, 0))
        self.entry.bind("<Return>", self.send_message)

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
                self.after(0,self.add_message(USERNAME,msg,sent_by_user=True))
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

    def add_message(self, username, message, sent_by_user=True):
        # Shadow frame (slightly bigger, darker color)
        shadow = CTkFrame(self.scrollable_frame, corner_radius=15, fg_color="#c0c0c0")
        shadow.pack(anchor="e" if sent_by_user else "w", pady=5, padx=5)

        # Actual message bubble on top of shadow
        msg_container = CTkFrame(shadow, corner_radius=15, fg_color="#DCF8C6" if sent_by_user else "#FFFFFF")
        msg_container.pack(padx=2, pady=2)  # small offset for shadow effect

        # Username label
        CTkLabel(msg_container, text=username, font=("Arial", 8, "bold"), fg_color=msg_container._fg_color).pack(
            anchor="w", padx=8, pady=(3, 0))

        # Message bubble text
        CTkLabel(msg_container, text=message, font=("Arial", 12), wraplength=250, justify="left",
                 fg_color=msg_container._fg_color).pack(anchor="w", padx=8, pady=(0, 5))

        # Scroll to bottom
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
        #self.chat_box.configure(state="normal")
        #self.chat_box.insert("end", msg + "")
        #self.chat_box.configure(state="disabled")
        #self.chat_box.see("end")


if __name__ == '__main__':
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ChatClient()
    app.mainloop()
