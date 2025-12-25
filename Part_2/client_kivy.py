import socket
import threading

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

OTHER_COLOR = (239/255, 246/255, 173/255, 1)
OWN_COLOR   = (242/255, 235/255,  50/255, 1)

KV = """
ScreenManager:
    LoginScreen:
    ChatScreen:

<LoginScreen>:
    name: "login"
    BoxLayout:
        orientation: "vertical"
        size_hint: None, None
        size: self.minimum_size
        spacing: 10
        pos_hint: {"center_x": 0.5, "center_y": 0.5}

        Image:
            source: "LordOfThePingsImage.jpg"
            size_hint: None, None
            size: 400, 400
            allow_stretch: True

        Label:
            text: "One chat to rule them all"
            font_size: "16sp"
            color: 1, 1, 1, 1
            size_hint_y: None
            height: self.texture_size[1]

        TextInput:
            id: username_input
            hint_text: "username"
            multiline: False
            size_hint: None, None
            size: 300, 45

        Button:
            text: "ENTER"
            size_hint: None, None
            size: 300, 45
            background_normal: ""
            background_down: ""
            background_color: 242/255, 235/255, 50/255, 1
            color: 0, 0, 0, 1
            on_press: root.login(username_input.text)

<ChatScreen>:
    name: "chat"
    BoxLayout:
        orientation: "vertical"

        BoxLayout:
            size_hint_y: None
            height: 40
            padding: 10

            Label:
                text: "server status: ONLINE"
                color: 0.4, 1, 0.4, 1

            Button:
                text: "X"
                size_hint_x: None
                width: 40
                background_color: 1, 0, 0, 1
                on_press: app.stop()

        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: chat_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: 10
                spacing: 10

        BoxLayout:
            size_hint_y: None
            height: 80
            padding: 10
            spacing: 10

            TextInput:
                id: message_input
                hint_text: "type your message..."
                multiline: False

            Button:
                text: "SEND"
                size_hint_x: None
                width: 100
                background_normal: ""
                background_down: ""
                background_color: 242/255, 235/255, 50/255, 1
                color: 0, 0, 0, 1
                on_press: root.send_message(message_input.text)
"""


class LoginScreen(Screen):
    def login(self, username):
        if not username:
            return

        app = App.get_running_app()
        app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        app.sock.connect(("127.0.0.1", 9000))
        app.sock.sendall(username.encode())

        chat = self.manager.get_screen("chat")
        chat.username = username
        chat.sock = app.sock

        threading.Thread(
            target=chat.listen_to_server,
            daemon=True
        ).start()

        self.manager.current = "chat"


class ChatScreen(Screen):
    username = StringProperty("")
    sock = None

    # ================= NETWORK =================

    def listen_to_server(self):
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    raise ConnectionResetError()

                message = data.decode().strip()
                Clock.schedule_once(
                    lambda dt, msg=message: self.add_message(msg, is_own=False)
                )

        except:
            self.on_disconnected()

    def send_message(self, text):
        if not text:
            return

        self.ids.message_input.text = ""
        self.add_message(text, is_own=True)

        try:
            self.sock.sendall(text.encode())
        except:
            self.on_disconnected()

    # ================= DISCONNECT =================

    def on_disconnected(self):
        Clock.schedule_once(lambda dt: self.show_disconnect_popup())

    def show_disconnect_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)

        msg = Label(
            text="You were disconnected by the server",
            font_size=18
        )

        btn = Button(
            text="OK",
            size_hint=(1, None),
            height=45
        )

        content.add_widget(msg)
        content.add_widget(btn)

        popup = Popup(
            title="Disconnected",
            content=content,
            size_hint=(0.7, 0.35),
            auto_dismiss=False
        )

        btn.bind(on_release=lambda x: self.return_to_login(popup))
        popup.open()

    def return_to_login(self, popup):
        popup.dismiss()

        try:
            self.sock.close()
        except:
            pass

        self.manager.current = "login"

    # ================= UI =================

    def add_message(self, text, is_own=False):
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout
        from kivy.graphics import Color, RoundedRectangle

        bubble_color = OWN_COLOR if is_own else OTHER_COLOR

        bubble = Label(
            text=text,
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            padding=(12, 8),
            text_size=(self.width * 0.6, None)
        )

        bubble.bind(
            texture_size=lambda inst, val:
            setattr(inst, "size", (val[0] + 24, val[1] + 16))
        )

        container = BoxLayout(
            size_hint_y=None,
            height=bubble.height,
            padding=(10, 5)
        )

        if is_own:
            container.add_widget(BoxLayout())
            container.add_widget(bubble)
        else:
            container.add_widget(bubble)
            container.add_widget(BoxLayout())

        with bubble.canvas.before:
            Color(*bubble_color)
            bubble.bg = RoundedRectangle(radius=[20], pos=bubble.pos, size=bubble.size)

        bubble.bind(
            pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
            size=lambda inst, v: setattr(inst.bg, "size", inst.size)
        )

        self.ids.chat_box.add_widget(container)


class ChatApp(App):
    sock = None

    def build(self):
        return Builder.load_string(KV)


if __name__ == "__main__":
    ChatApp().run()
