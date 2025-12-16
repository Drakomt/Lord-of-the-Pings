# =============================
# client_kivy.py – TCP Chat Client (with username)
# =============================
import socket
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

# ====== CHANGE HERE ======
SERVER_IP = '192.168.1.100'   # IP of the server machine (same Wi-Fi)
SERVER_PORT = 5000
USERNAME = 'Natan'            # change per device / user
# ==========================


class ChatLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.chat_label = Label(size_hint_y=None, text_size=(None, None))
        self.chat_label.bind(texture_size=self.chat_label.setter('size'))

        scroll = ScrollView()
        scroll.add_widget(self.chat_label)
        self.add_widget(scroll)

        bottom = BoxLayout(size_hint_y=0.2)
        self.input = TextInput(multiline=False, hint_text='Type a message...')
        send_btn = Button(text='Send')
        send_btn.bind(on_press=self.send_message)

        bottom.add_widget(self.input)
        bottom.add_widget(send_btn)
        self.add_widget(bottom)

        # TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((SERVER_IP, SERVER_PORT))

        # Send username as first message
        self.sock.sendall(USERNAME.encode())

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_message(self, instance):
        msg = self.input.text.strip()
        if msg:
            self.sock.sendall(msg.encode())
            self.input.text = ''

    def receive_messages(self):
        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                Clock.schedule_once(
                    lambda dt, msg=data.decode(): self.add_text(msg)
                )
            except:
                break

    def add_text(self, msg):
        self.chat_label.text += msg + '\n'


class ChatApp(App):
    def build(self):
        return ChatLayout()


if __name__ == '__main__':
    ChatApp().run()
