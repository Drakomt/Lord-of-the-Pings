import socket
import threading
from datetime import datetime
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, RoundedRectangle

OTHER_COLOR = (239 / 255, 246 / 255, 173 / 255, 1)
OWN_COLOR = (242 / 255, 235 / 255, 50 / 255, 1)

KV = """
ScreenManager:
    LoginScreen:
    ChatScreen:

<LoginScreen>:
    name: "login"
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.1, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # This RelativeLayout ensures the inner BoxLayout is always centered
    RelativeLayout:
        BoxLayout:
            orientation: "vertical"
            size_hint: None, None
            size: 400, self.minimum_height
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            spacing: 50  # Very large space between sections
            padding: [0, 20, 0, 20]

            Image:
                source: "LordOfThePingsImage.jpg"
                size_hint: (None, None)
                size: (300, 300)
                pos_hint: {"center_x": 0.5}
                allow_stretch: True

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: 30 # Space between the label and the text input

                Label:
                    text: "One chat to rule them all"
                    font_size: "22sp"
                    bold: True
                    color: 1, 1, 1, 1
                    size_hint_y: None
                    height: self.texture_size[1]

                TextInput:
                    id: username_input
                    hint_text: "Enter Username"
                    multiline: False
                    size_hint: (None, None)
                    size: (320, 55)
                    pos_hint: {"center_x": 0.5}
                    foreground_color: 0, 0, 0, 1
                    hint_text_color: 0.5, 0.5, 0.5, 1
                    background_color: 1, 1, 1, 1 
                    background_normal: "" 
                    padding: [15, (self.height - self.line_height) / 2]

            Button:
                text: "ENTER"
                size_hint: (None, None)
                size: (320, 60)
                pos_hint: {"center_x": 0.5}
                background_normal: ""
                background_color: 242/255, 235/255, 50/255, 1
                color: 0, 0, 0, 1
                bold: True
                font_size: "20sp"
                on_press: root.login(username_input.text)

<ChatScreen>:
    name: "chat"
    BoxLayout:
        orientation: "vertical"

        # Header with Red container behind Exit button
        BoxLayout:
            size_hint_y: None
            height: 70
            padding: [15, 10]
            spacing: 10
            canvas.before:
                Color:
                    rgba: 0.15, 0.15, 0.15, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                text: "SERVER STATUS: ONLINE"
                color: 0.4, 1, 0.4, 1
                bold: True
                halign: "left"
                text_size: self.size

            BoxLayout:
                size_hint: (None, None)
                size: (85, 45)
                pos_hint: {"center_y": 0.5}
                canvas.before:
                    Color:
                        rgba: 0.8, 0.1, 0.1, 1 
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [10]

                Button:
                    text: "EXIT"
                    background_normal: ""
                    background_color: 0, 0, 0, 0 
                    color: 1, 1, 1, 1
                    bold: True
                    on_press: app.stop()

        ScrollView:
            id: chat_scroll
            do_scroll_x: False
            canvas.before:
                Color:
                    rgba: 0.08, 0.08, 0.08, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            BoxLayout:
                id: chat_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: [10, 15]
                spacing: 15
                pos_hint: {'top': 1}

        BoxLayout:
            size_hint_y: None
            height: 90
            padding: 15
            spacing: 15
            canvas.before:
                Color:
                    rgba: 0.2, 0.2, 0.2, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            TextInput:
                id: message_input
                hint_text: "Type your message..."
                multiline: False
                foreground_color: 0, 0, 0, 1
                background_color: 0.9, 0.9, 0.9, 1
                padding: [15, (self.height - self.line_height) / 2]

            Button:
                text: "SEND"
                size_hint_x: None
                width: 110
                background_normal: ""
                background_color: 242/255, 235/255, 50/255, 1
                color: 0, 0, 0, 1
                bold: True
                on_press: root.send_message(message_input.text)
"""


class LoginScreen(Screen):
    def on_kv_post(self, base_widget):
        ti = self.ids.username_input
        with ti.canvas.after:
            Color(242 / 255, 235 / 255, 50 / 255, 1)
            self.border_line = Line(rectangle=(ti.x, ti.y, ti.width, ti.height), width=1.5)

        def update_border(instance, value):
            self.border_line.rectangle = (ti.x, ti.y, ti.width, ti.height)

        ti.bind(pos=update_border, size=update_border)

    def login(self, username):
        if not username.strip(): return
        app = App.get_running_app()
        try:
            app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            app.sock.connect(("127.0.0.1", 9000))
            app.sock.sendall(username.encode())
        except Exception as e:
            print("Connection error:", e)
            return
        chat = self.manager.get_screen("chat")
        chat.username = username
        chat.sock = app.sock
        threading.Thread(target=chat.listen_to_server, daemon=True).start()
        self.manager.current = "chat"


class ChatScreen(Screen):
    username = StringProperty("")
    sock = None

    def listen_to_server(self):
        try:
            while True:
                data = self.sock.recv(1024)
                if not data: break
                message = data.decode().strip()
                Clock.schedule_once(lambda dt, msg=message: self.add_message(msg, is_own=False))
        except:
            self.on_disconnected()

    def send_message(self, text):
        if not text.strip(): return
        self.ids.message_input.text = ""
        self.add_message(text, is_own=True)
        try:
            self.sock.sendall(text.encode())
        except:
            self.on_disconnected()

    def add_message(self, text, is_own=False):
        bubble_color = OWN_COLOR if is_own else OTHER_COLOR
        time_str = datetime.now().strftime("%H:%M")

        bubble_layout = BoxLayout(orientation='vertical', size_hint=(None, None), padding=(12, 8))

        msg_label = Label(
            text=text,
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            halign='left'
        )
        msg_label.text_size = (self.width * 0.65, None)

        def update_msg_size(inst, val):
            inst.size = inst.texture_size

        msg_label.bind(texture_size=update_msg_size)

        time_label = Label(
            text=time_str,
            color=(0, 0, 0, 0.4),
            font_size='10sp',
            size_hint=(1, None),
            height=15,
            halign='right'
        )
        time_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (inst.width, None)))

        bubble_layout.add_widget(msg_label)
        bubble_layout.add_widget(time_label)

        def update_bubble_size(inst, val):
            inst.width = max(msg_label.width, 65) + 24
            inst.height = msg_label.height + time_label.height + 15

        bubble_layout.bind(minimum_size=update_bubble_size)

        container = BoxLayout(size_hint_y=None)
        bubble_layout.bind(height=lambda inst, val: setattr(container, 'height', val))

        if is_own:
            container.add_widget(Widget())
            container.add_widget(bubble_layout)
        else:
            container.add_widget(bubble_layout)
            container.add_widget(Widget())

        with bubble_layout.canvas.before:
            Color(*bubble_color)
            bubble_layout.bg = RoundedRectangle(radius=[12], pos=bubble_layout.pos, size=bubble_layout.size)

        bubble_layout.bind(pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
                           size=lambda inst, v: setattr(inst.bg, "size", inst.size))

        self.ids.chat_box.add_widget(container)
        Clock.schedule_once(self.scroll_to_bottom, 0.05)

    def scroll_to_bottom(self, dt):
        if self.ids.chat_box.height > self.ids.chat_scroll.height:
            self.ids.chat_scroll.scroll_y = 0

    def on_disconnected(self):
        Clock.schedule_once(lambda dt: self.show_disconnect_popup())

    def show_disconnect_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(Label(text="Disconnected from server", font_size=16))
        btn = Button(text="OK", size_hint_y=None, height=45)
        content.add_widget(btn)
        popup = Popup(title="Error", content=content, size_hint=(0.7, 0.3), auto_dismiss=False)
        btn.bind(on_release=lambda x: self.return_to_login(popup))
        popup.open()

    def return_to_login(self, popup):
        popup.dismiss()
        self.manager.current = "login"


class ChatApp(App):
    def build(self):
        return Builder.load_string(KV)


if __name__ == "__main__":
    ChatApp().run()