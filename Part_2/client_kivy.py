from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp
import socket
import threading
import os
import time
from dotenv import load_dotenv
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
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Line, RoundedRectangle

# ============================================
# AETHER THEME - Blue / Purple Palette (RGBA accurate)
# ============================================
# BASE_BG:      #0E1020 - background
# DARK_BG:      #1A1F3A - cards, navbar, buttons
# OWN_COLOR:    #4E8AFF - your messages / primary accent
# OTHER_COLOR:  #8463FF - other messages / secondary accent
# TEXT_PRIMARY: #F2F5FF - primary text
# TEXT_HINT:    #8C9ABC - secondary text
# SYSTEM_COLOR: #2C3456 - system messages
# INPUT_BG:     #121426 - text input backgrounds
# ALERT_COLOR:  #FF58A0 - alerts/errors

BASE_BG = (14/255, 16/255, 32/255, 1)
DARK_BG = (26/255, 31/255, 58/255, 1)
OWN_COLOR = (78/255, 138/255, 255/255, 1)
OTHER_COLOR = (132/255, 99/255, 255/255, 1)
TEXT_PRIMARY = (242/255, 245/255, 255/255, 1)
TEXT_HINT = (140/255, 154/255, 188/255, 1)
SYSTEM_COLOR = (44/255, 52/255, 86/255, 1)
INPUT_BG = (18/255, 20/255, 38/255, 1)
ALERT_COLOR = (255/255, 88/255, 160/255, 1)

load_dotenv()

# ====== DISCOVERY CONFIG ======
DISCOVERY_PORT = 9001
DISCOVERY_TIMEOUT = 10  # seconds - longer initial timeout
DISCOVERY_PREFIX = "LOTP_SERVER|"
DISCOVERY_RETRY_INTERVAL = 3  # seconds - retry every 3 seconds if not found
user_avatars = {}   # username -> avatar filename

# ====== SERVER CONFIG ======
# Check if env vars are set - if yes, use them as manual override
# If not, use broadcast discovery
ENV_HOST = os.environ.get("HOST")
ENV_PORT = os.environ.get("SERVER_PORT")
USE_ENV_OVERRIDE = ENV_HOST is not None and ENV_PORT is not None

if USE_ENV_OVERRIDE:
    HOST = ENV_HOST
    SERVER_PORT = int(ENV_PORT)
else:
    HOST = "127.0.0.1"  # Placeholder, will be set by discovery
    SERVER_PORT = 9000  # Placeholder, will be set by discovery

DISCOVERED = False  # Flag to track if server was discovered

# ====== Screen Design kivy ======

KV = """
ScreenManager:
    LoginScreen:
    MainScreen:
    ChatScreen:

<LoginScreen>:
    name: "login"
    canvas.before:
        Color:
            rgba: 14/255., 16/255., 32/255., 1  # BASE_BG
        Rectangle:
            pos: self.pos
            size: self.size

    # This RelativeLayout ensures the inner BoxLayout is always centered
    RelativeLayout:
        BoxLayout:
            orientation: "vertical"
            size_hint: 0.9, None
            width: min(400, root.width * 0.9)
            height: self.minimum_height
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            spacing: dp(30)  # Responsive spacing
            padding: [dp(10), dp(20), dp(10), dp(20)]

            Image:
                source: "Lotp_Image_BP.png"
                size_hint: (None, None)
                size: (min(300, root.width * 0.7), min(300, root.width * 0.7))
                pos_hint: {"center_x": 0.5}
                allow_stretch: True

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: 30 # Space between the label and the text input
                Label:
                    id: server_status_lbl
                    text : "Checking status..."
                    color: 1, 1, 1, 1
                    bold: True
                    halign: "center"
                    text_size: self.size
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
                    size_hint: (0.9, None)
                    height: dp(55)
                    pos_hint: {"center_x": 0.5}
                    foreground_color: 242/255., 245/255., 255/255., 1  # TEXT_PRIMARY
                    hint_text_color: 140/255., 154/255., 188/255., 1  # TEXT_HINT
                    background_color: 18/255., 20/255., 38/255., 1  # INPUT_BG
                    background_normal: "" 
                    padding: [dp(15), (self.height - self.line_height) / 2]
                    on_text_validate: root.login(username_input.text)

            Button:
                text: "ENTER"
                size_hint: (0.9, None)
                height: dp(60)
                pos_hint: {"center_x": 0.5}
                background_normal: ""
                background_color: 26/255, 31/255, 58/255, 1  # DARK_BG
                color: 242/255., 245/255., 255/255., 1  # TEXT_PRIMARY
                bold: True
                font_size: "20sp"
                on_press: root.login(username_input.text)
                canvas.after:
                    Color:
                        rgba: 78/255, 138/255, 255/255, 1  # OWN_COLOR (blue border)
                    Line:
                        rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
                        width: 1.5

<MainScreen>:
    name: "main"
    BoxLayout:
        orientation: "horizontal"

        # Main content - chat cards
        BoxLayout:
            orientation: "vertical"
            padding: 0
            spacing: 0

            # Header with Exit button
            BoxLayout:
                size_hint_y: None
                height: dp(70)
                padding: [dp(15), dp(10)]
                spacing: dp(10)
                canvas.before:
                    Color:
                        rgba: 26/255., 31/255., 58/255., 1  # DARK_BG (navbar)
                    Rectangle:
                        pos: self.pos
                        size: self.size

                Button:
                    text: "EXIT"
                    size_hint: (None, None)
                    size: (dp(85), dp(45))
                    pos_hint: {"center_y": 0.5}
                    background_normal: ""
                    background_color: 26/255., 31/255., 58/255., 1  # DARK_BG
                    color: 1, 1, 1, 1
                    bold: True
                    canvas.after:
                        Color:
                            rgba: 132/255., 99/255., 255/255., 1  # OTHER_COLOR (purple border)
                        Line:
                            rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
                            width: 1.5
                    bold: True
                    on_press: root.Exit_to_login()
                BoxLayout:
                    orientation: "horizontal"
                    spacing: dp(8)
                    size_hint_x: 1
                    height: dp(28)
                
                    Label:
                        id: current_user_lbl
                        text: f"User: {root.username}"
                        color: 1, 1, 1, 1
                        bold: True
                        font_size: "18sp"
                        halign: "right"
                        valign: "middle"
                        text_size: self.size
                        size_hint_x: 1
                        shorten: True
                        shorten_from: "right"
                
                    AnchorLayout:
                        size_hint_x: None
                        width: dp(28)
                        anchor_x: "center"
                        anchor_y: "center"
                
                        Image:
                            id: current_user_avatar
                            size_hint: None, None
                            size: dp(28), dp(28)
                            keep_ratio: True
                            allow_stretch: False
                            opacity: 1



            Label:
                text: "Chats"
                size_hint_y: None
                height: dp(50)
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "left"
                valign: "middle"
                padding: dp(15), 0
                text_size: self.size
                canvas.before:
                    Color:
                        rgba: 132/255., 99/255., 255/255., 1  # OTHER_COLOR background
                    Rectangle:
                        pos: self.pos
                        size: self.size

            ScrollView:
                id: chats_scroll
                do_scroll_x: False
                bar_width: 6
                canvas.before:
                    Color:
                        rgba: 14/255., 16/255., 32/255., 1  # BASE_BG
                    Rectangle:
                        pos: self.pos
                        size: self.size

                BoxLayout:
                    id: chats_container
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: [dp(15), dp(10)]
                    spacing: dp(12)

        # Sidebar user list
        BoxLayout:
            orientation: "vertical"
            size_hint_x: None
            width: max(dp(150), root.width * 0.28)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 14/255., 16/255., 32/255., 1  # BASE_BG
                Rectangle:
                    pos: self.pos
                    size: self.size
            canvas.after:
                Color:
                    rgba: 26/255., 31/255., 58/255., 1  # DARK_BG background
                Line:
                    rectangle: (self.x, self.y, self.width, self.height)
                    width: 1.5

            Label:
                text: "Users Online"
                size_hint_y: None
                height: dp(30)
                color: 1, 1, 1, 1
                bold: True
                canvas.before:
                    Color:
                        rgba: 132/255., 99/255., 255/255., 1  # OTHER_COLOR background
                    Rectangle:
                        pos: self.pos
                        size: self.size

            ScrollView:
                id: users_scroll
                do_scroll_x: False

                BoxLayout:
                    id: user_list
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(10)
                    padding: [dp(5), dp(8)]

<ChatScreen>:
    name: "chat"
    BoxLayout:
        orientation: "vertical"

        # Header with back button
        BoxLayout:
            size_hint_y: None
            height: dp(70)
            padding: [dp(15), dp(10)]
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 26/255., 31/255., 58/255., 1  # CARD_BG (navbar)
                Rectangle:
                    pos: self.pos
                    size: self.size

            Button:
                text: "<--"
                size_hint: (None, None)
                size: (dp(80), dp(45))
                background_normal: ""
                background_color: 26/255, 31/255, 58/255, 1  # DARK_BG
                color: 242/255., 245/255., 255/255., 1  # TEXT_PRIMARY
                bold: True
                font_size: "24sp"
                on_press: root.go_back()
                canvas.after:
                    Color:
                        rgba: 132/255., 99/255., 255/255., 1  # OTHER_COLOR (purple border)
                    Line:
                        rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
                        width: 1.5

            Label:
                id: chat_title
                text: "General Chat"
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "left"
                valign: "middle"
                text_size: self.size

            Label:
                id: current_user_lbl
                text: "User:"
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "right"
                valign: "middle"
                text_size: self.size

        ScrollView:
            id: chat_scroll
            do_scroll_x: False
            bar_width: 6
            canvas.before:
                Color:
                    rgba: 14/255., 16/255., 32/255., 1  # BASE_BG
                Rectangle:
                    pos: self.pos
                    size: self.size

            BoxLayout:
                id: chat_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(10), dp(15)]
                spacing: dp(15)
                pos_hint: {'top': 1}

        BoxLayout:
            size_hint_y: None
            height: dp(90)
            padding: dp(15)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 26/255., 31/255., 58/255., 1  # CARD_BG
                Rectangle:
                    pos: self.pos
                    size: self.size

            TextInput:
                id: message_input
                hint_text: "Type your message..."
                multiline: False
                foreground_color: 242/255., 245/255., 255/255., 1  # TEXT_PRIMARY
                hint_text_color: 140/255., 154/255., 188/255., 1  # TEXT_HINT
                background_color: 18/255., 20/255., 38/255., 1  # INPUT_BG
                padding: [dp(15), (self.height - self.line_height) / 2]
                on_text_validate: root.send_message(message_input.text)

            Button:
                text: "SEND"
                size_hint_x: None
                width: dp(110)
                background_normal: ""
                background_color: 26/255, 31/255, 58/255, 1  # DARK_BG  
                color: 242/255., 245/255., 255/255., 1  # TEXT_PRIMARY
                bold: True
                on_press: root.send_message(message_input.text)
                canvas.after:
                    Color:
                        rgba: 132/255., 99/255., 255/255., 1  # OTHER_COLOR (purple border)
                    Line:
                        rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
                        width: 1.5
"""

# ============ SERVER DISCOVERY FUNCTIONS =============

discovery_thread_stop = False  # Flag to stop the discovery thread


def try_broadcast_discovery():
    """
    Tries to discover server via UDP broadcast.
    Returns (ip, port) or None if not found within timeout.
    """
    try:
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(1)

        start_time = time.time()

        while time.time() - start_time < DISCOVERY_TIMEOUT:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode()

                if message.startswith(DISCOVERY_PREFIX):
                    port = int(message.split("|")[1])
                    server_ip = addr[0]
                    sock.close()
                    return server_ip, port

            except socket.timeout:
                continue
            except:
                break

        sock.close()
    except:
        pass

    return None


def try_env_server():
    """
    Tries to connect to server from env vars.
    Returns (ip, port) if successful, None otherwise.
    """
    env_host = os.environ.get("HOST", "127.0.0.1")
    env_port = int(os.environ.get("SERVER_PORT", 9000))

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((env_host, env_port))
        sock.close()
        return env_host, env_port
    except:
        return None


def find_server():
    """
    Finds server via broadcast discovery.
    If env vars are set (manual override), uses those instead.
    Returns (ip, port) or None if not found.
    """
    # If env vars are manually set, use those instead of discovery
    if USE_ENV_OVERRIDE:
        return (ENV_HOST, int(ENV_PORT))

    # Otherwise, try broadcast discovery
    return try_broadcast_discovery()


def start_discovery():
    """
    Starts server discovery in a background thread.
    Tries broadcast and env vars, retries if not found.
    Stops when connection is established.
    """
    def worker():
        global discovery_thread_stop, HOST, SERVER_PORT, DISCOVERED

        # If env override is set, use it immediately without retrying
        if USE_ENV_OVERRIDE:
            HOST = ENV_HOST
            SERVER_PORT = int(ENV_PORT)
            DISCOVERED = True
            print(f"[Discovery] Using env override: {HOST}:{SERVER_PORT}")
            discovery_thread_stop = True  # Stop discovery thread
            return

        # Otherwise, search for broadcast
        while not discovery_thread_stop:
            result = find_server()

            if result:
                server_ip, server_port = result
                HOST = server_ip
                SERVER_PORT = server_port
                DISCOVERED = True
                print(
                    f"[Discovery] Found server via broadcast at {HOST}:{SERVER_PORT}")
                break  # Stop searching once found
            else:
                # Not found, wait before retrying
                if not discovery_thread_stop:
                    time.sleep(DISCOVERY_RETRY_INTERVAL)

    threading.Thread(target=worker, daemon=True).start()


def stop_discovery():
    """
    Stops the discovery thread.
    """
    global discovery_thread_stop
    discovery_thread_stop = True


def restart_discovery():
    """
    Restarts the discovery thread (used after disconnect).
    """
    global discovery_thread_stop
    discovery_thread_stop = False
    start_discovery()


# ============ if server online check function =============


def server_online():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.8)
        sock.connect((HOST, SERVER_PORT))
        sock.close()
        return True
    except:
        return False


# ============LoginsScreen==================================================


class LoginScreen(Screen):
    def on_enter(self):
        # Check server status immediately (don't wait for first interval)
        threading.Thread(target=self.perform_ping, daemon=True).start()
        # Then schedule periodic checks every 1 second
        Clock.schedule_interval(self.check_status, 1)
        # Auto-focus the username input
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, 'focus', True), 0.2)

    def on_leave(self):
        # Stop checking when the user leaves the login screen to save battery/CPU
        Clock.unschedule(self.check_status)

    def check_status(self, dt):
        # We run the actual network logic in a Thread so the UI doesn't "hiccup"
        threading.Thread(target=self.perform_ping, daemon=True).start()

    def perform_ping(self):
        # 1. Check the network
        online = server_online()

        # 2. Update the UI safely on the main thread
        Clock.schedule_once(lambda dt: self.update_label(online))

    def update_label(self, online):
        if online:
            self.ids.server_status_lbl.text = "ONLINE"
            self.ids.server_status_lbl.color = OWN_COLOR
        else:
            self.ids.server_status_lbl.text = "OFFLINE"
            self.ids.server_status_lbl.color = ALERT_COLOR

    def show_server_offline_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="server is down try again later", font_size=18))
        btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                     background_color=DARK_BG, color=TEXT_PRIMARY, bold=True)

        # Add rounded border
        with btn.canvas.after:
            Color(*OWN_COLOR)
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                 size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

        content.add_widget(btn)
        popup = Popup(title="Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda x: self.return_to_login(popup))
        popup.open()
        # Give focus to the button by simulating a keyboard event
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def show_username_taken_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Username already taken. Please choose another.", font_size=18))
        btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                     background_color=DARK_BG, color=TEXT_PRIMARY, bold=True)

        # Add rounded border
        with btn.canvas.after:
            Color(*OWN_COLOR)
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                 size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

        content.add_widget(btn)
        popup = Popup(title="Username Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda x: self._on_popup_close_login(popup))
        popup.open()
        # Give focus to the button by simulating a keyboard event
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def return_to_login(self, popup):
        popup.dismiss()
        self.manager.current = "login"
        # Focus on username input after popup closes
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, 'focus', True), 0.1)

    def _on_popup_close_login(self, popup):
        """Helper method to handle popup close and restore focus to username input"""
        popup.dismiss()
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, 'focus', True), 0.1)

    def on_kv_post(self, base_widget):
        ti = self.ids.username_input
        with ti.canvas.after:
            Color(*OWN_COLOR)
            self.border_line = Line(rectangle=(
                ti.x, ti.y, ti.width, ti.height), width=1.5)

        def update_border(instance, value):
            self.border_line.rectangle = (ti.x, ti.y, ti.width, ti.height)

        ti.bind(pos=update_border, size=update_border)

    def login(self, username):
        if not username.strip():
            return

        # If not using env override, make sure discovery has found the server first
        if not USE_ENV_OVERRIDE and not DISCOVERED:
            self.show_server_offline_popup()
            return

        app = App.get_running_app()
        prebuffer = b""
        try:
            app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            app.sock.connect((HOST, SERVER_PORT))
            app.sock.sendall(username.encode())

            # Drain the initial burst (user list + avatar assignments) before the listener spins up
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
        except Exception as e:
            self.show_server_offline_popup()
            print("Connection error:", e)
            return

        # Handle immediate username-taken response
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

        # Success path: transition to main and preserve any pre-received messages
        main = self.manager.get_screen("main")
        main.reset_chat_data()
        main.username = username
        main.sock = app.sock

        # If we received non-error data (like USERLIST| or join messages), feed it in
        if prebuffer:
            for line in premsg.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("USERLIST|"):
                    try:
                        names = [n for n in line.split(
                            "|", 1)[1].split(",") if n]
                    except Exception:
                        names = []
                    Clock.schedule_once(
                        lambda dt, names=names: main.update_user_buttons(names))
                elif line.startswith("AVATAR|"):
                    try:
                        _, uname, avatar = line.split("|", 2)
                        user_avatars[uname] = avatar
                        if uname == username:
                            Clock.schedule_once(
                                lambda dt: main.update_current_user_avatar())
                        Clock.schedule_once(
                            lambda dt: main.update_user_buttons(main.online_users))
                        Clock.schedule_once(
                            lambda dt: main.update_chat_cards())
                    except Exception:
                        pass
                else:
                    Clock.schedule_once(
                        lambda dt, m=line: main.route_message(m))

        # Stop discovery now that we're connected
        stop_discovery()

        threading.Thread(target=main.listen_to_server, daemon=True).start()
        self.manager.current = "main"


# ============ Main Screen ===============================


class UserButton(ButtonBehavior, BoxLayout):
    def __init__(self, username, callback, **kwargs):
        # קריאה נפרדת לכל אב כדי למנוע TypeError
        BoxLayout.__init__(self, size_hint_y=None, height=dp(
            40), padding=(dp(10), 0), **kwargs)
        ButtonBehavior.__init__(self)

        with self.canvas.before:
            Color(*DARK_BG)
            self.bg = RoundedRectangle(
                radius=[dp(8)], pos=self.pos, size=self.size)
            Color(*OTHER_COLOR)
            self.border = Line(rounded_rectangle=(
                self.x, self.y, self.width, self.height, dp(8)), width=1.2)

        self.bind(pos=self._update_graphics, size=self._update_graphics)

        # תוכן ממורכז אנכית
        content = BoxLayout(orientation="horizontal",
                            spacing=dp(8), pos_hint={'center_y': 0.5})

        avatar_file = user_avatars.get(username)
        if avatar_file:
            avatar_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "assets", "avatars", avatar_file)
            if os.path.exists(avatar_path):
                content.add_widget(Image(source=avatar_path, size_hint=(
                    None, None), size=(dp(24), dp(24)), pos_hint={'center_y': 0.5}))

        label = Label(text=username, color=TEXT_PRIMARY, bold=True, font_size="14sp",
                      halign="left", valign="middle", shorten=True)
        label.bind(size=lambda inst, val: setattr(
            inst, "text_size", inst.size))

        content.add_widget(label)
        self.add_widget(content)
        self.bind(on_release=callback)

    def _update_graphics(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(8))


class ChatCard(ButtonBehavior, BoxLayout):
    def __init__(self, title, chat_id, parent_with_open_chat, unread=0, **kwargs):
        # גובה רזה 55dp וקריאה מופרדת ל-init
        BoxLayout.__init__(self, orientation="horizontal", size_hint_y=None,
                           height=dp(55), padding=(dp(15), dp(5)), spacing=dp(12), **kwargs)
        ButtonBehavior.__init__(self)

        self.chat_id = chat_id

        with self.canvas.before:
            Color(*DARK_BG)
            self.bg = RoundedRectangle(
                radius=[dp(10)], pos=self.pos, size=self.size)

        self.bind(pos=lambda inst, val: setattr(self.bg, "pos", inst.pos),
                  size=lambda inst, val: setattr(self.bg, "size", inst.size))

        # מיכל טקסט ממורכז אנכית עם center_y
        info_box = BoxLayout(orientation="vertical",
                             size_hint_y=1, pos_hint={'center_y': 0.5})

        title_label = Label(text=title, color=(1, 1, 1, 1), bold=True, font_size="16sp",
                            halign="left", valign="middle")
        title_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", inst.size))
        info_box.add_widget(title_label)

        if unread > 0:
            unread_label = Label(text=f"{unread} new messages", color=OWN_COLOR,
                                 font_size="11sp", halign="left", valign="middle")
            unread_label.bind(size=lambda inst, val: setattr(
                inst, "text_size", inst.size))
            info_box.add_widget(unread_label)

        # אווטאר קטן ממורכז
        if chat_id != "general":
            avatar_file = user_avatars.get(chat_id)
            if avatar_file:
                avatar_path = os.path.join(os.path.dirname(
                    os.path.abspath(__file__)), "assets", "avatars", avatar_file)
                if os.path.exists(avatar_path):
                    self.add_widget(Image(source=avatar_path, size_hint=(None, None),
                                          size=(dp(30), dp(30)), pos_hint={'center_y': 0.5}))

        self.add_widget(info_box)
        self.bind(on_release=lambda inst: parent_with_open_chat.open_chat(chat_id))


class MainScreen(Screen):
    username = StringProperty("")
    sock = None
    user_initiated_disconnect = False

    def disconnect_socket(self):
        """Properly disconnect the socket from the server"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def reset_chat_data(self):
        """Clear all chat history and user list for new login"""
        self.chats = {}
        self.online_users = []
        self.ids.chats_container.clear_widgets()
        self.ids.user_list.clear_widgets()
        user_avatars.clear()

    def Exit_to_login(self):
        self.user_initiated_disconnect = True
        self.disconnect_socket()
        self.reset_chat_data()
        self.manager.current = "login"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chats = {}  # chat_id -> {messages: [], unread: 0}
        self.online_users = []

    def listen_to_server(self):
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break
                message = data.decode().strip()
                if message.startswith("USERLIST|"):
                    names = [n for n in message.split(
                        "|", 1)[1].split(",") if n]
                    Clock.schedule_once(
                        lambda dt, names=names: self.update_user_buttons(names))
                elif message.startswith("AVATAR|"):
                    _, username, avatar = message.split("|", 2)
                    user_avatars[username] = avatar

                    # אם זה האווטר שלי – טען אותו עכשיו (זה הזמן הנכון)
                    if username == self.username:
                        Clock.schedule_once(
                            lambda dt: self.update_current_user_avatar())

                    # ריענון UI
                    Clock.schedule_once(
                        lambda dt: self.update_user_buttons(self.online_users))
                    Clock.schedule_once(lambda dt: self.update_chat_cards())

                else:
                    Clock.schedule_once(
                        lambda dt, msg=message: self.route_message(msg))

        except:
            self.on_disconnected()

    def route_message(self, message):
        chat_id = None
        is_self_sender = False
        username = ""
        body = message

        if message.startswith("[PM ") and "->" in message:
            parsed = self.parse_pm(message)
            if parsed:
                sender, target, body = parsed
                username = sender.strip()
                is_self_sender = (username == self.username.strip())
                chat_id = sender if target == self.username else target
        else:
            chat_id = "general"
            # Parse "username: body" format
            if ":" in message:
                try:
                    username, body = message.split(":", 1)
                    username = username.strip()
                    body = body.strip()
                    is_self_sender = (username == self.username)
                except Exception:
                    username = "Unknown"
                    is_self_sender = False
            else:
                username = "Unknown"

        if chat_id not in self.chats:
            self.chats[chat_id] = {"messages": [], "unread": 0}

        # If this is my own message echoed by the server, skip to avoid duplicate
        if is_self_sender:
            # Still refresh cards to keep UI consistent
            self.update_chat_cards()
            return

        # Append the incoming message with separated username and body
        self.chats[chat_id]["messages"].append(
            {"username": username, "text": body, "is_own": False})

        # If the chat is currently open, push the bubble live and avoid counting as unread
        try:
            chat_screen = self.manager.get_screen("chat")
            if self.manager.current == "chat" and chat_screen.chat_id == chat_id:
                # Ensure unread stays 0 for the open chat
                self.chats[chat_id]["unread"] = 0
                chat_screen.add_message_bubble(username, body, is_own=False)
                Clock.schedule_once(
                    lambda dt: chat_screen.scroll_to_bottom(), 0.05)
            else:
                # Not currently viewing this chat -> mark as unread
                self.chats[chat_id]["unread"] += 1
        except Exception:
            # Fallback: if screen not ready, count as unread
            self.chats[chat_id]["unread"] += 1

        # Refresh cards to reflect unread changes
        self.update_chat_cards()

    def parse_pm(self, message):
        try:
            prefix, body = message.split("]:", 1)
            body = body.strip()
            prefix = prefix.strip("[]")
            _, rest = prefix.split("PM ", 1)
            sender, target = rest.split("->")
            return sender.strip(), target.strip(), body
        except Exception:
            return None

    def update_user_buttons(self, names):
        # Store previous online users to detect disconnections
        previous_users = set(self.online_users)
        self.online_users = [n for n in names if n and n != self.username]
        current_users = set(self.online_users)

        # Detect users who disconnected
        disconnected_users = previous_users - current_users

        # Handle disconnections for users with active private chats
        for user in disconnected_users:
            if user in self.chats:
                # Show popup notification
                self.show_user_disconnected_popup(user)

                # Check if user is currently viewing this chat
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == user:
                        # Navigate back to main screen
                        Clock.schedule_once(lambda dt: setattr(
                            self.manager, 'current', 'main'), 0.5)
                except Exception:
                    pass

                # Remove the chat
                self.remove_chat(user)

        holder = self.ids.user_list
        holder.clear_widgets()
        self.ids.current_user_lbl.text = f"User: {self.username}"
        for name in self.online_users:
            user_btn = UserButton(
                name,
                callback=lambda inst, n=name: self.open_chat(n)
            )
            holder.add_widget(user_btn)
        self.update_chat_cards()

    def update_chat_cards(self):
        container = self.ids.chats_container
        container.clear_widgets()

        # General chat card
        general_card = self.create_chat_card("General Chat", "general")
        container.add_widget(general_card)

        # Add divider between general and private chats if there are private chats
        private_chats = [
            user for user in self.online_users if user in self.chats]
        if private_chats:
            divider = self.create_divider()
            container.add_widget(divider)

        # Private chat cards
        for user in private_chats:
            private_card = self.create_chat_card(f"{user}", user)
            container.add_widget(private_card)

    def create_chat_card(self, title, chat_id):
        unread = self.chats.get(chat_id, {}).get("unread", 0)
        return ChatCard(title, chat_id, parent_with_open_chat=self, unread=unread)

    def create_divider(self):
        """Create a divider bar between general and private chats"""
        divider_container = BoxLayout(
            size_hint_y=None,
            height=30,
            padding=(15, 8)
        )

        divider_line = Widget(size_hint_y=None, height=1)
        with divider_line.canvas:
            Color(*OTHER_COLOR)
            divider_line.rect = RoundedRectangle(
                pos=divider_line.pos,
                size=divider_line.size,
                radius=[0]
            )

        divider_line.bind(
            pos=lambda inst, val: setattr(inst.rect, 'pos', inst.pos),
            size=lambda inst, val: setattr(inst.rect, 'size', inst.size)
        )

        divider_container.add_widget(divider_line)
        return divider_container

    def open_chat(self, chat_id):
        if chat_id not in self.chats:
            self.chats[chat_id] = {"messages": [], "unread": 0}

        # Reset unread counter
        self.chats[chat_id]["unread"] = 0
        self.update_chat_cards()

        # Navigate to ChatScreen
        chat_screen = self.manager.get_screen("chat")
        chat_screen.load_chat(chat_id, self)
        self.manager.current = "chat"

    def on_disconnected(self):
        # Restart discovery to find the server again
        restart_discovery()

        # Only show disconnect popup if it wasn't a user-initiated disconnect
        if not self.user_initiated_disconnect:
            Clock.schedule_once(lambda dt: self.show_disconnect_popup())
        else:
            # Reset the flag for next session
            self.user_initiated_disconnect = False

    def show_disconnect_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Disconnected from server", font_size=18))
        btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                     background_color=DARK_BG, color=TEXT_PRIMARY, bold=True)

        # Add rounded border
        with btn.canvas.after:
            Color(*OWN_COLOR)
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                 size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

        content.add_widget(btn)
        popup = Popup(title="Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda x: self.return_to_login(popup))
        popup.open()
        # Give focus to the button by pressing it after a short delay
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def show_user_disconnected_popup(self, username):
        """Show popup when a user in a private chat disconnects"""
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text=f"{username} has disconnected", font_size=18))
        btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                     background_color=DARK_BG, color=TEXT_PRIMARY, bold=True)

        # Add rounded border
        with btn.canvas.after:
            Color(*OWN_COLOR)
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                 size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

        content.add_widget(btn)
        popup = Popup(title="User Disconnected", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda x: popup.dismiss())
        popup.open()
        # Give focus to the button by simulating a keyboard event
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def remove_chat(self, chat_id):
        """Remove a chat from the chats dictionary and update UI"""
        if chat_id in self.chats:
            del self.chats[chat_id]
        self.update_chat_cards()

    def return_to_login(self, popup):
        popup.dismiss()
        self.manager.current = "login"

    def update_current_user_avatar(self):
        if not self.username:
            return

        avatar_file = user_avatars.get(self.username)
        if not avatar_file:
            self.ids.current_user_avatar.source = ""
            return

        avatar_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "assets", "avatars", avatar_file)
        if os.path.exists(avatar_path):
            self.ids.current_user_avatar.source = avatar_path
            self.ids.current_user_avatar.opacity = 1
            self.ids.current_user_avatar.reload()
        else:
            self.ids.current_user_avatar.source = ""


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_id = None
        self.main_screen = None

    def load_chat(self, chat_id, main_screen):
        self.chat_id = chat_id
        self.main_screen = main_screen

        # Set title
        if chat_id == "general":
            self.ids.chat_title.text = "General Chat"
        else:
            self.ids.chat_title.text = f"{chat_id}"
        self.ids.current_user_lbl.text = f"User: {main_screen.username}"
        # Load messages
        self.refresh_messages()
        # Auto-focus the message input
        Clock.schedule_once(lambda dt: setattr(
            self.ids.message_input, 'focus', True), 0.1)

    def refresh_messages(self):
        box = self.ids.chat_box
        box.clear_widgets()

        if self.chat_id and self.chat_id in self.main_screen.chats:
            messages = self.main_screen.chats[self.chat_id]["messages"]
            for msg in messages:
                username = msg.get("username", "Unknown")
                text = msg.get("text", "")
                is_own = msg.get("is_own", False)
                self.add_message_bubble(username, text, is_own)

        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)

    def add_message_bubble(self, username, text, is_own):
        # Check if this is a system message (user joined/left)
        is_system_message = (
            "joined the chat" in text or
            "left the chat" in text or
            text.startswith("***")
        )

        if is_system_message:
            # Create centered system message
            self.add_system_message(text)
            return

        bubble_color = OWN_COLOR if is_own else OTHER_COLOR
        time_str = datetime.now().strftime("%H:%M")
        avatar_file = user_avatars.get(username)
        avatar_widget = None

        if avatar_file:
            avatar_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "assets", "avatars", avatar_file)
            if os.path.exists(avatar_path):
                avatar_widget = Image(
                    source=avatar_path,
                    size_hint=(None, None),
                    size=(dp(32), dp(32))
                )

        bubble_layout = BoxLayout(
            orientation='vertical', size_hint=(None, None), padding=(dp(12), dp(8)), spacing=dp(5))

        # Username label
        username_label = Label(
            text=username,
            color=TEXT_PRIMARY,
            size_hint=(None, None),
            halign='left',
            font_size='11sp',
            bold=True
        )

        def update_username_size(inst, val):
            inst.size = inst.texture_size

        username_label.bind(texture_size=update_username_size)
        username_label.text_size = (None, None)

        # Message label
        msg_label = Label(
            text=text,
            color=TEXT_PRIMARY,
            size_hint=(None, None),
            halign='left'
        )

        def update_msg_size(inst, val):
            inst.size = inst.texture_size

        msg_label.bind(texture_size=update_msg_size)

        # Defer text_size until layout is ready to avoid 0-width wrap
        def set_text_size(_dt=None, width=None):
            # Use min to ensure it doesn't exceed screen width, with better mobile sizing
            max_width = width if width is not None else self.ids.chat_box.width * 0.7
            msg_label.text_size = (max(dp(100), min(max_width, dp(300))), None)

        # Initial scheduling and live binding to container width
        Clock.schedule_once(set_text_size, 0)
        self.ids.chat_box.bind(
            width=lambda inst, val: set_text_size(width=val * 0.7))

        # Time label
        time_label = Label(
            text=time_str,
            color=(1, 1, 1, 1),
            font_size='10sp',
            size_hint=(1, None),
            height=15,
            halign='right'
        )
        time_label.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (inst.width, None)))

        bubble_layout.add_widget(username_label)
        bubble_layout.add_widget(msg_label)
        bubble_layout.add_widget(time_label)

        def update_bubble_size(inst, val):
            inst.width = max(msg_label.width, username_label.width, 65) + 24
            inst.height = username_label.height + msg_label.height + time_label.height + 20

        bubble_layout.bind(minimum_size=update_bubble_size)

        container = BoxLayout(size_hint_y=None)
        bubble_layout.bind(height=lambda inst,
                           val: setattr(container, 'height', val))

        if is_own:
            container.add_widget(Widget())
            container.add_widget(bubble_layout)
        else:
            if avatar_widget:
                container.add_widget(avatar_widget)
            container.add_widget(bubble_layout)
            container.add_widget(Widget())

        with bubble_layout.canvas.before:
            Color(*bubble_color)
            bubble_layout.bg = RoundedRectangle(
                radius=[dp(12)], pos=bubble_layout.pos, size=bubble_layout.size)

        bubble_layout.bind(pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
                           size=lambda inst, v: setattr(inst.bg, "size", inst.size))

        self.ids.chat_box.add_widget(container)

    def add_system_message(self, text):
        """Add a centered system message with different styling"""
        time_str = datetime.now().strftime("%H:%M")

        # Create centered container
        container = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            padding=(dp(10), dp(5))
        )

        # Create system message bubble
        bubble_layout = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            padding=(dp(15), dp(8)),
            pos_hint={'center_x': 0.5}
        )

        msg_label = Label(
            text=text,
            color=TEXT_PRIMARY,
            size_hint=(None, None),
            halign='center',
            italic=True,
            font_size='12sp'
        )

        def update_msg_size(inst, val):
            inst.size = inst.texture_size

        msg_label.bind(texture_size=update_msg_size)

        # Defer text_size until layout is ready to avoid 0-width wrap
        def set_text_size(_dt=None, width=None):
            # Use min to ensure it doesn't exceed screen width
            max_width = width if width is not None else self.ids.chat_box.width * 0.55
            msg_label.text_size = (max(dp(100), min(max_width, dp(250))), None)

        # Initial scheduling and live binding to container width
        Clock.schedule_once(set_text_size, 0)
        self.ids.chat_box.bind(
            width=lambda inst, val: set_text_size(width=val * 0.55))

        time_label = Label(
            text=time_str,
            color=(1, 1, 1, 1),
            font_size='9sp',
            size_hint=(1, None),
            height=12,
            halign='center'
        )
        time_label.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (inst.width, None)))

        bubble_layout.add_widget(msg_label)
        bubble_layout.add_widget(time_label)

        def update_bubble_size(inst, val):
            inst.width = msg_label.width + 30
            inst.height = msg_label.height + time_label.height + 15

        bubble_layout.bind(minimum_size=update_bubble_size)

        # Add spacers to center the bubble
        container.add_widget(Widget())
        container.add_widget(bubble_layout)
        container.add_widget(Widget())

        # Set background color for system message
        with bubble_layout.canvas.before:
            Color(*SYSTEM_COLOR)
            bubble_layout.bg = RoundedRectangle(
                radius=[dp(12)],
                pos=bubble_layout.pos,
                size=bubble_layout.size
            )

        bubble_layout.bind(
            pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
            size=lambda inst, v: setattr(inst.bg, "size", inst.size)
        )

        self.ids.chat_box.add_widget(container)

    def send_message(self, text):
        if not text.strip():
            return
        self.ids.message_input.text = ""

        outbound = text.strip()
        if self.chat_id != "general":
            outbound = f"@{self.chat_id} {outbound}"

        # Add to local chat
        if self.chat_id not in self.main_screen.chats:
            self.main_screen.chats[self.chat_id] = {
                "messages": [], "unread": 0}

        self.main_screen.chats[self.chat_id]["messages"].append(
            {"username": self.main_screen.username, "text": text.strip(), "is_own": True})
        self.add_message_bubble(self.main_screen.username,
                                text.strip(), is_own=True)

        # Send to server
        try:
            self.main_screen.sock.sendall(outbound.encode())
        except:
            self.main_screen.on_disconnected()

        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)
        # Refocus the message input so user can send multiple messages quickly
        Clock.schedule_once(lambda dt: setattr(
            self.ids.message_input, 'focus', True), 0.1)

    def scroll_to_bottom(self):
        if self.ids.chat_box.height > self.ids.chat_scroll.height:
            self.ids.chat_scroll.scroll_y = 0

    def go_back(self):
        self.manager.current = "main"


class ChatApp(App):
    def build(self):
        # Set window title and icon
        self.title = "Lord of the Pings"
        self.icon = "Lotp_Icon_BP.ico"  # Change to your .ico file path if needed

        # Start server discovery when app starts
        start_discovery()
        return Builder.load_string(KV)


if __name__ == "__main__":
    ChatApp().run()
