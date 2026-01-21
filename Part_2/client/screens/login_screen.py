import socket
import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from client import state
from client.constants import ALERT_COLOR, BASE_BG, DARK_BG2, OWN_COLOR, TEXT_PRIMARY
from client.discovery import server_online, stop_discovery
from client.protocol import parse_json_message


class LoginScreen(Screen):
    """Initial screen that handles discovery, ping, and login."""

    can_login = BooleanProperty(False)

    def on_enter(self):
        threading.Thread(target=self.perform_ping, daemon=True).start()
        Clock.schedule_interval(self.check_status, 1)
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, "focus", True), 0.2)

    def on_leave(self):
        Clock.unschedule(self.check_status)

    def check_status(self, _dt):
        threading.Thread(target=self.perform_ping, daemon=True).start()

    def perform_ping(self):
        online = server_online()
        Clock.schedule_once(lambda dt: self.update_label(online))

    def update_label(self, online):
        if online:
            self.ids.server_status_lbl.text = "ONLINE"
            self.ids.server_status_lbl.color = OWN_COLOR
            self.can_login = True
        else:
            self.ids.server_status_lbl.text = "OFFLINE"
            self.ids.server_status_lbl.color = ALERT_COLOR
            self.can_login = False

    def show_server_offline_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="server is down try again later", font_size=18))
        btn = Button(
            text="OK",
            size_hint_y=None,
            height=45,
            background_normal="",
            background_color=DARK_BG2,
            color=TEXT_PRIMARY,
            bold=True,
        )

        with btn.canvas.after:
            Color(*OWN_COLOR)
            btn.border_line = Line(
                rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, 8), width=1.5
            )
        btn.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
            size=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
        )

        content.add_widget(btn)
        popup = Popup(title="Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda _x: self.return_to_login(popup))
        popup.open()
        Clock.schedule_once(lambda dt: btn.dispatch("on_press"), 0.2)

    def show_username_taken_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Username already taken. Please choose another.", font_size=18))
        btn = Button(
            text="OK",
            size_hint_y=None,
            height=45,
            background_normal="",
            background_color=DARK_BG2,
            color=TEXT_PRIMARY,
            bold=True,
        )

        with btn.canvas.after:
            Color(*OWN_COLOR)
            btn.border_line = Line(
                rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, 8), width=1.5
            )
        btn.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
            size=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
        )

        content.add_widget(btn)
        popup = Popup(
            title="Username Error",
            content=content,
            size_hint=(0.7, 0.3),
            auto_dismiss=False,
        )
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda _x: self._on_popup_close_login(popup))
        popup.open()
        Clock.schedule_once(lambda dt: btn.dispatch("on_press"), 0.2)

    def return_to_login(self, popup):
        popup.dismiss()
        self.manager.current = "login"
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, "focus", True), 0.1)

    def _on_popup_close_login(self, popup):
        popup.dismiss()
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, "focus", True), 0.1)

    def on_kv_post(self, base_widget):
        ti = self.ids.username_input
        with ti.canvas.after:
            Color(*OWN_COLOR)
            self.border_line = Line(rectangle=(
                ti.x, ti.y, ti.width, ti.height), width=1.5)

        def update_border(_instance, _value):
            self.border_line.rectangle = (ti.x, ti.y, ti.width, ti.height)

        def clear_error_on_focus(_instance, value):
            if value:
                self.ids.error_label.text = ""

        ti.bind(pos=update_border, size=update_border,
                focus=clear_error_on_focus)

    def login(self, username):
        if not username.strip():
            self.ids.error_label.text = "Please enter a username"
            return

        self.ids.error_label.text = ""

        if not server_online():
            self.show_server_offline_popup()
            return

        app = App.get_running_app()
        prebuffer = b""
        try:
            app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            app.sock.connect((state.HOST, state.SERVER_PORT))
            app.sock.sendall(username.encode())
            app.sock.settimeout(0.4)
            chunks = []
            while True:
                try:
                    chunk = app.sock.recv(1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except socket.timeout:
                    break
            prebuffer = b"".join(chunks)
            app.sock.settimeout(None)
        except Exception as exc:  # noqa: BLE001
            self.show_server_offline_popup()
            print("Connection error:", exc)
            return

        if prebuffer:
            premsg = prebuffer.decode(errors="ignore").strip()
            if "Username already taken" in premsg:
                try:
                    app.sock.close()
                except Exception:
                    pass
                app.sock = None
                self.show_username_taken_popup()
                return

        main = self.manager.get_screen("main")
        main.reset_chat_data()
        main.username = username
        main.sock = app.sock

        userlist_names = []
        if prebuffer:
            buffer_str = premsg
            while "\n" in buffer_str:
                line, buffer_str = buffer_str.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                parsed = parse_json_message(line)
                if parsed:
                    msg_type = parsed.get("type", "")
                    data = parsed.get("data", {})
                    if msg_type == "USERLIST":
                        userlist_names = data.get("users", [])
                    elif msg_type == "AVATAR":
                        uname = data.get("username", "")
                        avatar = data.get("avatar", "")
                        if uname and avatar:
                            state.user_avatars[uname] = avatar
                    elif msg_type == "SYSTEM":
                        pass

            if userlist_names:
                Clock.schedule_once(
                    lambda dt: main.update_user_buttons(userlist_names), 0.1)

        if not userlist_names:
            Clock.schedule_once(lambda dt: main.update_user_buttons([]), 0.1)

        stop_discovery()
        threading.Thread(target=main.listen_to_server, daemon=True).start()
        self.manager.current = "main"
