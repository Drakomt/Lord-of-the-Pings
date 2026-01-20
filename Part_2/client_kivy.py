from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp
import socket
import threading
import os
import time
import random
import kivy.properties
from dotenv import load_dotenv
from datetime import datetime
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout

# ============================================
# AETHER THEME - Blue / Purple Palette (RGBA accurate)
# ============================================
# BASE_BG:      #0E1020 - background
# DARK_BG:      #1A1F3A - cards, navbar
# DARK_BG2:     #121426 - buttons
# OWN_COLOR:    #4E8AFF - your messages / primary accent
# OTHER_COLOR:  #8463FF - other messages / secondary accent
# TEXT_PRIMARY: #F2F5FF - primary text
# TEXT_HINT:    #8C9ABC - secondary text
# SYSTEM_COLOR: #2C3456 - system messages
# INPUT_BG:     #121426 - text input backgrounds
# ALERT_COLOR:  #FF58A0 - alerts/errors

BASE_BG = (14/255, 16/255, 32/255, 1)
DARK_BG = (26/255, 31/255, 58/255, 1)
DARK_BG2 = (18/255, 20/255, 38/255, 1)
OWN_COLOR = (78/255, 138/255, 255/255, 1)
OTHER_COLOR = (132/255, 99/255, 255/255, 1)
TEXT_PRIMARY = (242/255, 245/255, 255/255, 1)
TEXT_HINT = (140/255, 154/255, 188/255, 1)
SYSTEM_COLOR = (44/255, 52/255, 86/255, 1)
INPUT_BG = (18/255, 20/255, 38/255, 1)
ALERT_COLOR = (255/255, 88/255, 160/255, 1)

load_dotenv()

# ====== JSON MESSAGE PROTOCOL HELPERS ======


def send_json_message(sock, msg_type, data):
    """Send a JSON-encoded message through socket"""
    try:
        payload = {"type": msg_type, "data": data}
        sock.sendall(json.dumps(payload).encode())
    except Exception as e:
        print(f"Error sending JSON message: {e}")


def parse_json_message(raw_string):
    """Try to parse string as JSON, return dict or None"""
    try:
        return json.loads(raw_string)
    except:
        return None


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

# ====== Custom Styled Button Widget ======


class StyledButton(ButtonBehavior, FloatLayout):
    """Custom button widget with rounded corners, border, and dark background"""
    text = StringProperty("")
    image_source = StringProperty("")
    display_mode = StringProperty("text")  # "text", "icon", or "icon_text"
    # "vertical" or "horizontal" (for icon_text mode)
    text_orientation = StringProperty("vertical")
    border_color = kivy.properties.ListProperty(OTHER_COLOR)
    background_color = kivy.properties.ListProperty(DARK_BG2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_widget = None

        # Draw background and border
        with self.canvas.before:
            self.bg_color = Color(*self.background_color)
            self.bg = RoundedRectangle(
                radius=[dp(8)], pos=self.pos, size=self.size)
            self.border_color_obj = Color(*self.border_color)
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, dp(8)),
                width=1.5
            )

        # Bind for responsive updates
        self.bind(pos=self._update_graphics, size=self._update_graphics)
        self.bind(text=self._update_content, image_source=self._update_content,
                  display_mode=self._update_content, text_orientation=self._update_content)
        self.bind(background_color=self._update_bg_color,
                  border_color=self._update_border_color)

        # Initial content update
        self._update_content()

    def _update_content(self, *args):
        """Update the content based on display_mode"""
        # Remove old content
        if self.content_widget:
            self.remove_widget(self.content_widget)
            self.content_widget = None

        if self.display_mode == "text" and self.text:
            # Text only
            self.content_widget = Label(
                text=self.text,
                color=TEXT_PRIMARY,
                bold=True,
                font_size="12sp",
                size_hint=(1, 1),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                halign="center",
                valign="middle"
            )
            self.content_widget.bind(
                size=lambda inst, val: setattr(inst, 'text_size', inst.size))
            self.add_widget(self.content_widget)
        elif self.display_mode == "icon" and self.image_source:
            # Icon only
            self.content_widget = Image(
                source=self.image_source,
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            )
            self.add_widget(self.content_widget)
        elif self.display_mode == "icon_text":
            # Both icon and text
            is_vertical = self.text_orientation == "vertical"
            container = BoxLayout(
                orientation="vertical" if is_vertical else "horizontal",
                size_hint=(None, None),
                spacing=dp(4),
                padding=(dp(4), dp(4)),
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            )
            container.size = self.size
            self.bind(size=lambda inst, val: setattr(container, "size", val))
            # Icon first
            if self.image_source:
                img = Image(
                    source=self.image_source,
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                    size_hint=(None, None),
                    size=(dp(26), dp(26))
                )
                container.add_widget(img)

            # Text second
            if self.text:
                lbl = Label(
                    text=self.text,
                    color=TEXT_PRIMARY,
                    font_size="14sp",
                    halign="left" if not is_vertical else "center",
                    valign="middle",
                    size_hint=(1, 1),
                    text_size=(None, None)
                )

                if not is_vertical:
                    def update_label_width(*args):
                        icon_width = dp(24) + container.spacing + \
                            container.padding[0] * 2
                        lbl.width = max(container.width - icon_width, dp(10))
                        lbl.text_size = (lbl.width, None)

                    container.bind(size=update_label_width)
                else:
                    lbl.bind(size=lambda inst, val: setattr(
                        lbl, "text_size", lbl.size))
                container.add_widget(lbl)

            self.content_widget = container
            self.add_widget(self.content_widget)
        else:
            # Default: text if available, else icon
            if self.text:
                self.content_widget = Label(
                    text=self.text,
                    color=TEXT_PRIMARY,
                    bold=True,
                    font_size="16sp",
                    size_hint=(1, 1),
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                    halign="center",
                    valign="middle"
                )
                self.content_widget.bind(
                    size=lambda inst, val: setattr(inst, 'text_size', inst.size))
                self.add_widget(self.content_widget)
            elif self.image_source:
                self.content_widget = Image(
                    source=self.image_source,
                    size_hint=(None, None),
                    size=(dp(24), dp(24)),
                    pos_hint={"center_x": 0.5, "center_y": 0.5}
                )
                self.add_widget(self.content_widget)

    def _update_graphics(self, *args):
        """Update background and border when size/pos changes"""
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(8))

    def _update_bg_color(self, *args):
        """Update background color"""
        self.bg_color.rgba = self.background_color

    def _update_border_color(self, *args):
        """Update border color"""
        self.border_color_obj.rgba = self.border_color


# ====== Screen Design kivy ======

KV = """
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
                source: "assets/icons/Lotp_Image_BP.png"
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

                Label:
                    id: error_label
                    text: ""
                    color: 255/255., 88/255., 160/255., 1  # ALERT_COLOR
                    bold: True
                    font_size: "14sp"
                    halign: "center"
                    size_hint_y: None
                    height: self.texture_size[1] if self.text else 0
                    text_size: self.size

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

            StyledButton:
                text: "ENTER"
                size_hint: (0.9, None)
                height: dp(60)
                pos_hint: {"center_x": 0.5}
                border_color: 78/255, 138/255, 255/255, 1
                background_color: 18/255, 20/255, 38/255, 1
                on_press: root.login(username_input.text)

<MainScreen>:
    name: "main"
    BoxLayout:
        orientation: "horizontal"

        # Main content - chat cards
        BoxLayout:
            orientation: "vertical"
            padding: 0
            spacing: 0

            # Header with Exit button and User Bubble
            BoxLayout:
                orientation: "horizontal"
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

                StyledButton:
                    text: "EXIT"
                    size_hint: (None, None)
                    size: (dp(85), dp(45))
                    pos_hint: {"center_y": 0.5}
                    on_press: root.Exit_to_login()
                
                Widget:  # spacer

                UserBubbleWidget:
                    id: user_bubble_widget
                    size_hint_x: None

                # Menu button - only visible on mobile
                StyledButton:
                    image_source: "assets/icons/group.png"
                    size_hint: (None, None)
                    size: (dp(45) if root.width < dp(700) else 0, dp(45))
                    pos_hint: {"center_y": 0.5}
                    opacity: 1 if root.width < dp(700) else 0
                    disabled: root.width >= dp(700)
                    on_press: root.toggle_drawer()




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

        # Sidebar user list (responsive: drawer on mobile, sidebar on desktop)
        BoxLayout:
            id: sidebar_container
            orientation: "vertical"
            size_hint_x: None if root.width >= dp(700) else 0
            width: (max(dp(150), root.width * 0.28) if root.width >= dp(700) else max(dp(220), root.width * 0.7))
            pos_hint: {'right': 1, 'top': 1} if root.width < dp(700) else {}
            pos: (root.width - self.width if root.drawer_open else root.width, 0) if root.width < dp(700) else self.pos
            spacing: 0
            canvas.before:
                Color:
                    rgba: 26/255., 31/255., 58/255., 1  # DARK_BG
                Rectangle:
                    pos: self.pos
                    size: self.size
            canvas.after:
                Color:
                    rgba: 132/255, 99/255, 255/255, 1  # OTHER_COLOR border
                Line:
                    rectangle: (self.x, self.y, self.width, self.height)
                    width: 2

            # Header with close button (on mobile, close button on left side)
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(40)
                spacing: 0
                canvas.before:
                    Color:
                        rgba: 132/255., 99/255., 255/255., 1  # OTHER_COLOR background
                    Rectangle:
                        pos: self.pos
                        size: self.size
                
                StyledButton:
                    image_source: "assets/icons/X.png"
                    size_hint: (None, 1)
                    width: dp(40) if root.width < dp(700) else 0
                    opacity: 1 if root.width < dp(700) else 0
                    disabled: root.width >= dp(700)
                    on_press: root.close_drawer()
                
                Label:
                    text: "Users Online"
                    color: 1, 1, 1, 1
                    bold: True
                    font_size: "16sp"
                    halign: "center"
                    valign: "middle"

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

            StyledButton:
                size_hint: (None, None)
                size: (dp(45), dp(45))
                image_source: "assets/icons/back_arrow.png"
                on_press: root.go_back()

            Label:
                id: chat_title
                text: "General Chat"
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "left"
                valign: "middle"
                size_hint_x: None
                on_texture_size:
                    self.width = self.texture_size[0] + dp(20)

            Widget: # spacer

            StyledButton:
                id: invite_container
                text: root.invite_stats_text
                display_mode: "icon_text"
                text_orientation: "vertical"
                image_source: "assets/icons/tic_tac_toe.png"
                size_hint: (None, None)
                size: (dp(50), dp(50))
                opacity: 0  # Hidden by default (not private chat)
                disabled: True
                on_press: root.send_game_invite()

            UserBubbleWidget:
                id: user_bubble_widget
                size_hint_x: None

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

            StyledButton:
                text: "SEND"
                size_hint_x: None
                width: dp(110)
                on_press: root.send_message(message_input.text)

<GameScreen>:
    name: "game"
    BoxLayout:
        orientation: "vertical"

        # Header
        BoxLayout:
            size_hint_y: None
            height: dp(70)
            padding: [dp(15), dp(10)]
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 26/255., 31/255., 58/255., 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            StyledButton:
                size_hint: (None, None)
                size: (dp(45), dp(45))
                image_source: "assets/icons/back_arrow.png"
                on_press: root.exit_game()

            Label:
                text: "Tic-Tac-Toe"
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "left"
                size_hint_x: 1


        # ================= GAME BODY =================
        RelativeLayout:
            canvas.before:
                Color:
                    rgba: 14/255., 16/255., 32/255., 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            # -------- Vertical content stack --------
            BoxLayout:
                orientation: "vertical"
                size_hint: None, None
                width: min(dp(320), root.width)
                height: self.minimum_height
                spacing: dp(18)
                pos_hint: {"center_x": 0.5, "top": 0.95}

                # -------- Status --------
                Label:
                    id: game_status_label
                    text: "Your Turn"
                    color: 78/255., 138/255., 1, 1
                    font_size: "22sp"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]
                    halign: "center"
                    valign: "middle"
                    text_size: self.width, None

                # -------- Score --------
                Label:
                    id: score_label
                    text: "You: 0 | Opponent: 0"
                    color: 242/255., 245/255., 1, 1
                    font_size: "16sp"
                    size_hint_y: None
                    height: self.texture_size[1]
                    halign: "center"
                    valign: "middle"
                    text_size: self.width, None

                # -------- Separator --------
                Widget:
                    size_hint_y: None
                    height: dp(12)
                    canvas.before:
                        Color:
                            rgba: 132/255., 99/255., 1, 1
                        Rectangle:
                            size: self.width * 0.8, dp(1)
                            pos: self.center_x - self.width * 0.4, self.center_y

                # -------- Game board --------
                AnchorLayout:
                    size_hint_y: None
                    height: root.grid_size
                    anchor_x: "center"
                    anchor_y: "center"

                    GridLayout:
                        id: game_board
                        cols: 3
                        rows: 3
                        spacing: dp(6)
                        padding: dp(3), dp(3)
                        size_hint: None, None
                        size: root.grid_size, root.grid_size

                # New game button (hidden initially)
                AnchorLayout:
                    size_hint_y: None
                    height: dp(50)
                    anchor_x: "center"
                    anchor_y: "center"
                    StyledButton:
                        id: new_game_btn
                        text: "NEW GAME"
                        size_hint: (None, None)
                        size: (dp(180), dp(50))
                        opacity: 0
                        disabled: True
                        on_press: root.reset_game()

ScreenManager:
    LoginScreen:
    MainScreen:
    ChatScreen:
    GameScreen:
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


class AvatarButton(ButtonBehavior, FloatLayout):
    """Avatar button with image and border for the picker"""

    def __init__(self, avatar_path, is_current=False, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = dp(50)
        self.height = dp(50)

        # Add image to the float layout
        self.img = Image(
            source=avatar_path,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.img)

        # Draw border
        highlight_color = OWN_COLOR if is_current else OTHER_COLOR
        with self.canvas.after:
            Color(*highlight_color)
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, dp(12)),
                width=2
            )

        self.bind(
            pos=self._update_border,
            size=self._update_border
        )

    def _update_border(self, *args):
        self.border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(12))


class UserBubbleWidget(BoxLayout):
    """Custom widget to display user info as a styled bubble"""

    def __init__(self, username="", avatar_source=None, **kwargs):
        # Set defaults but allow kwargs to override
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (None, 1)
        if 'height' not in kwargs:
            kwargs['height'] = dp(50)

        super().__init__(orientation='horizontal', spacing=dp(12), **kwargs)
        self.size_hint_x = None
        self.bind(minimum_width=lambda inst, val: setattr(inst, "width", val))
        self.username = username
        self.avatar_widget = None
        self.name_label = None
        self.bubble_bg = None
        self.on_press_callback = None

        self._build_widget(username, avatar_source)

    def _build_widget(self, username, avatar_source):
        """Build or rebuild the widget with new username and avatar"""
        self.clear_widgets()
        self.username = username

        # Create a single bubble container with background that includes everything
        bubble_container = BoxLayout(
            orientation='horizontal',
            # Equal left and right padding
            padding=[dp(10), dp(6), dp(10), dp(6)],
            spacing=dp(10),
            size_hint=(None, None),
            height=dp(50)
        )

        # Add bubble background (slightly darker than header)
        with bubble_container.canvas.before:
            Color(rgba=(18/255, 20/255, 38/255, 1))  # INPUT_BG - darker
            self.bubble_bg = RoundedRectangle(
                radius=[dp(10)],
                pos=bubble_container.pos,
                size=bubble_container.size
            )
            # Add border
            Color(rgba=OTHER_COLOR)  # Purple border
            self.bubble_border = Line(
                rounded_rectangle=(bubble_container.x, bubble_container.y,
                                   bubble_container.width, bubble_container.height, dp(10)),
                width=1.5
            )

        def update_bubble_graphics(inst, val):
            self.bubble_bg.pos = inst.pos
            self.bubble_bg.size = inst.size
            self.bubble_border.rounded_rectangle = (
                inst.x, inst.y, inst.width, inst.height, dp(10))

        bubble_container.bind(pos=update_bubble_graphics,
                              size=update_bubble_graphics)

        # Avatar inside bubble (if provided)
        if avatar_source:
            self.avatar_widget = Image(
                source=avatar_source,
                size_hint=(None, None),
                size=(dp(36), dp(36))
            )
            bubble_container.add_widget(self.avatar_widget)
        else:
            self.avatar_widget = None

        # Text container inside bubble
        text_layout = BoxLayout(
            orientation='vertical',
            padding=[0, dp(2)],
            spacing=dp(1),
            size_hint=(None, None),
            width=dp(90),
            height=dp(38)
        )

        # "User:" header in small font like timestamps
        header_label = Label(
            text='User:',
            color=TEXT_HINT,
            font_size='12sp',
            size_hint=(None, None),
            height=dp(12),
            halign='left',
            valign='bottom'
        )
        header_label.bind(texture_size=lambda inst,
                          val: setattr(inst, 'width', val[0]))
        header_label.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (inst.width, None)))

        # Username in larger font
        self.name_label = Label(
            text=username,
            color=TEXT_PRIMARY,
            font_size='18sp',
            bold=True,
            size_hint=(None, None),
            height=dp(20),
            halign='left',
            valign='top'
        )
        self.name_label.bind(texture_size=lambda inst,
                             val: setattr(inst, 'width', val[0]))
        self.name_label.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (inst.width, None)))

        text_layout.add_widget(header_label)
        text_layout.add_widget(self.name_label)

        bubble_container.add_widget(text_layout)

        # Calculate bubble width based on content
        def update_width(*args):
            # avatar + spacing
            avatar_width = (dp(36) + dp(10)) if avatar_source else 0
            header_width = header_label.texture_size[0] if header_label.texture_size[0] > 0 else dp(
                40)
            name_width = self.name_label.texture_size[0] if self.name_label.texture_size[0] > 0 else dp(
                60)
            text_width = max(header_width, name_width)
            # Total: left_padding + avatar + spacing + text + right_padding
            bubble_container.width = dp(
                10) + avatar_width + text_width + dp(10)
            text_layout.width = text_width

        # Bind to texture_size changes to update width dynamically
        header_label.bind(texture_size=update_width)
        self.name_label.bind(texture_size=update_width)

        # Initial width calculation
        update_width()

        self.add_widget(bubble_container)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if callable(self.on_press_callback):
                self.on_press_callback()
            return True
        return super().on_touch_down(touch)

    def set_user(self, username, avatar_source=None):
        """Update the widget with new user info"""
        self._build_widget(username, avatar_source)


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
                     background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

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
                     background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

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

        def clear_error_on_focus(instance, value):
            if value:  # When focus is True
                self.ids.error_label.text = ""

        ti.bind(pos=update_border, size=update_border,
                focus=clear_error_on_focus)

    def login(self, username):
        if not username.strip():
            # Show error message
            self.ids.error_label.text = "Please enter a username"
            return

        # Clear any previous error when attempting login
        self.ids.error_label.text = ""

        # If not using env override, verify server is actually reachable
        if not USE_ENV_OVERRIDE:
            if not server_online():
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

        # If we received non-error data, process it (JSON or legacy format)
        userlist_names = []
        if prebuffer:
            # Process ALL messages first to populate user_avatars before updating UI
            buffer_str = premsg
            for line in buffer_str.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Try to parse as JSON first
                parsed = parse_json_message(line)
                if parsed:
                    # Handle JSON messages during login
                    msg_type = parsed.get("type", "")
                    data = parsed.get("data", {})

                    if msg_type == "USERLIST":
                        userlist_names = data.get("users", [])

                    elif msg_type == "AVATAR":
                        uname = data.get("username", "")
                        avatar = data.get("avatar", "")
                        if uname and avatar:
                            user_avatars[uname] = avatar

                    elif msg_type == "SYSTEM":
                        # System messages during login can be ignored or stored
                        pass

                else:
                    # Legacy string format fallback
                    if line.startswith("USERLIST|"):
                        try:
                            userlist_names = [n for n in line.split(
                                "|", 1)[1].split(",") if n]
                        except Exception:
                            userlist_names = []
                    elif line.startswith("AVATAR|"):
                        try:
                            _, uname, avatar = line.split("|", 2)
                            user_avatars[uname] = avatar
                        except Exception:
                            pass
                    else:
                        # Unknown message format - let the listener thread handle it
                        Clock.schedule_once(
                            lambda dt, m=line: main.route_message(m))

            # Now schedule UI updates AFTER all data is processed
            if userlist_names:
                Clock.schedule_once(
                    lambda dt: main.update_user_buttons(userlist_names), 0.1)

        # If no prebuffer or no userlist, still initialize the display
        # This ensures username shows even if we're the only user
        if not userlist_names:
            Clock.schedule_once(lambda dt: main.update_user_buttons([]), 0.1)

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
    drawer_open = BooleanProperty(False)
    sock = None
    user_initiated_disconnect = False

    def toggle_drawer(self):
        """Toggle the drawer open/closed on mobile"""
        self.drawer_open = not self.drawer_open

    def close_drawer(self):
        """Close the drawer"""
        self.drawer_open = False

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
        self.game_records = {}
        self.ids.chats_container.clear_widgets()
        self.ids.user_list.clear_widgets()
        user_avatars.clear()

    def clear_invites_for_chat(self, chat_id):
        """Remove any stored game invites for a chat and refresh the UI"""
        if not chat_id or chat_id not in self.chats:
            return

        messages = self.chats[chat_id].get("messages", [])
        filtered = [m for m in messages if not m.get(
            "text", "").startswith("***GAME_INVITE***")]
        self.chats[chat_id]["messages"] = filtered

        try:
            chat_screen = self.manager.get_screen("chat")
            if chat_screen.chat_id == chat_id:
                chat_screen.has_pending_invite = False
                chat_screen.refresh_messages()
        except Exception:
            pass

    def Exit_to_login(self):
        self.user_initiated_disconnect = True
        self.disconnect_socket()
        self.reset_chat_data()
        self.manager.current = "login"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chats = {}  # chat_id -> {messages: [], unread: 0}
        self.online_users = []
        self.game_records = {}  # opponent -> {wins, losses}

    def on_kv_post(self, base_widget):
        self.ids.user_bubble_widget.on_press_callback = self.open_avatar_picker

    def open_avatar_picker(self):
        avatars_dir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "assets", "avatars")
        try:
            avatars = [f for f in os.listdir(
                avatars_dir) if f.endswith(".png")]
        except Exception:
            avatars = []

        if not avatars or not self.username:
            return

        current_avatar = user_avatars.get(self.username)

        grid = GridLayout(
            cols=4,
            spacing=dp(12),
            padding=dp(12),
            size_hint_x=None,
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))
        grid.bind(minimum_width=grid.setter("width"))

        # Ensure each child is measured at its fixed size
        grid.bind(children=lambda inst, val: setattr(
            inst, 'width', inst.minimum_width))

        def add_avatar_button(filename):
            avatar_path = os.path.join(avatars_dir, filename)
            is_current = (filename == current_avatar)

            btn = AvatarButton(avatar_path, is_current=is_current)
            btn.bind(on_release=lambda inst,
                     name=filename: self._select_avatar(name))
            grid.add_widget(btn)

        for avatar in sorted(avatars):
            add_avatar_button(avatar)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)

        # Create popup wrapper
        popup_container = BoxLayout(
            orientation='vertical', padding=0, spacing=0)
        popup_container.add_widget(scroll)

        popup = Popup(
            title="Choose Your Avatar",
            content=popup_container,
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            background="",
            background_color=(0, 0, 0, 0),
        )
        popup.title_size = "18sp"
        popup.separator_color = OTHER_COLOR

        with popup.canvas.before:
            Color(*OTHER_COLOR)
            popup.outer_border = RoundedRectangle(
                radius=[dp(12)],
                pos=popup.pos,
                size=popup.size
            )
            Color(*BASE_BG)
            popup.outer_bg = RoundedRectangle(
                radius=[dp(10)],
                pos=(popup.x + dp(2), popup.y + dp(2)),
                size=(popup.width - dp(4), popup.height - dp(4))
            )

        def update_popup_graphics(inst, val):
            popup.outer_border.pos = inst.pos
            popup.outer_border.size = inst.size
            popup.outer_bg.pos = (inst.x + dp(2), inst.y + dp(2))
            popup.outer_bg.size = (inst.width - dp(4), inst.height - dp(4))

        popup.bind(pos=update_popup_graphics, size=update_popup_graphics)

        # Calculate popup size based on grid content
        def set_popup_size(dt=None):
            # Grid height + padding + title height + spacing
            title_height = dp(40)
            total_height = grid.height + dp(24) + title_height
            total_width = grid.width + dp(24)

            popup.size = (min(total_width, self.width * 0.9),
                          min(total_height, self.height * 0.9))

        # Set initial size before opening
        Clock.schedule_once(set_popup_size, 0)

        def close_on_select(_dt=None):
            popup.dismiss()

        # Replace the on_select closer after creation to use inside _select_avatar
        self._avatar_popup_closer = close_on_select

        # Open after size is calculated
        def open_popup(dt):
            popup.open()
            # Disable background dimming overlay
            popup.overlay_color = [0, 0, 0, 0]

        Clock.schedule_once(open_popup, 0.1)

    def _select_avatar(self, avatar_name):
        user_avatars[self.username] = avatar_name
        self.update_current_user_avatar()

        try:
            if self.sock:
                send_json_message(self.sock, "SET_AVATAR",
                                  {"avatar": avatar_name})
        except Exception:
            self.on_disconnected()

        closer = getattr(self, "_avatar_popup_closer", None)
        if closer:
            Clock.schedule_once(closer, 0)

    def listen_to_server(self):
        buffer = ""
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break
                buffer += data.decode()

                # Process complete messages (separated by newlines)
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    message = message.strip()
                    if not message:
                        continue

                    # Try to parse as JSON first
                    parsed = parse_json_message(message)
                    if parsed:
                        Clock.schedule_once(
                            lambda dt, msg=parsed: self.route_json_message(msg))
                    else:
                        # Fallback to legacy string format for backward compatibility
                        print(
                            f"[LEGACY] Processing non-JSON message: {message[:100]}")
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

        # Ensure only one active invite per chat
        if body.startswith("***GAME_INVITE***"):
            self.clear_invites_for_chat(chat_id)

        # Check for game left messages
        if body.startswith("***GAME_LEFT***"):
            # Opponent left the game
            try:
                opponent_name = body.replace("***GAME_LEFT***", "")
                self.clear_invites_for_chat(opponent_name)
                if self.manager.current == "game":
                    # Show popup and redirect to chat
                    def show_left_popup(dt):
                        content = BoxLayout(
                            orientation="vertical", spacing=15, padding=20)
                        content.add_widget(
                            Label(text=f"{opponent_name} left the game", font_size=18))
                        btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                                     background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

                        # Add rounded border
                        with btn.canvas.after:
                            Color(*OWN_COLOR)
                            btn.border_line = Line(rounded_rectangle=(
                                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
                        btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                                 size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

                        content.add_widget(btn)

                        popup = Popup(title="Game Ended", content=content,
                                      size_hint=(0.7, 0.3), auto_dismiss=False)
                        popup.background = ""
                        popup.background_color = BASE_BG
                        popup.title_size = 20

                        def on_close(instance):
                            popup.dismiss()
                            # Navigate to chat screen
                            try:
                                chat_screen = self.manager.get_screen("chat")
                                if chat_screen.chat_id == opponent_name or chat_screen.chat_id == self.username:
                                    self.manager.current = "chat"
                                else:
                                    # Load the private chat with that user
                                    chat_screen.load_chat(opponent_name, self)
                                    self.manager.current = "chat"
                            except:
                                self.manager.current = "main"

                        btn.bind(on_press=on_close)
                        popup.open()

                    Clock.schedule_once(show_left_popup, 0.1)
            except Exception:
                pass
            return

        # Check for game end messages
        if body.startswith("***GAME_END***"):
            # Opponent's game ended, update our score
            try:
                winner_symbol = body.replace("***GAME_END***", "")
                game_screen = self.manager.get_screen("game")
                show_popup = self.manager.current == "game"
                game_screen.receive_opponent_game_end(
                    winner_symbol, show_popup=show_popup)

                # After updating game screen, refresh the chat invite stats if in chat
                # Get opponent name from game_screen if available, otherwise from current chat
                opponent_name = game_screen.opponent_name if game_screen.opponent_name else None
                if not opponent_name and self.manager.current == "chat":
                    try:
                        chat_screen = self.manager.get_screen("chat")
                        if chat_screen.chat_id != "general":
                            opponent_name = chat_screen.chat_id
                    except Exception:
                        pass

                if self.manager.current == "chat" and opponent_name:
                    try:
                        chat_screen = self.manager.get_screen("chat")
                        if chat_screen.chat_id == opponent_name:
                            chat_screen.update_invite_stats()
                    except Exception:
                        pass
            except Exception:
                pass
            return

        # Check for game reset messages
        if body.startswith("***GAME_RESET***"):
            # Opponent started a new game
            try:
                msg_content = body.replace("***GAME_RESET***", "")
                # Parse format: player_name|their_symbol
                if "|" in msg_content:
                    player_name, their_symbol = msg_content.split("|", 1)
                else:
                    # Fallback for old format without symbol
                    player_name = msg_content
                    their_symbol = "X"

                game_screen = self.manager.get_screen("game")
                if self.manager.current == "game":
                    # Opponent got their_symbol, so we get the opposite
                    my_symbol = "O" if their_symbol == "X" else "X"
                    game_screen.next_game_opponent_symbol = their_symbol
                    game_screen.next_game_my_symbol = my_symbol
                    game_screen.receive_opponent_reset()
            except Exception:
                pass
            return

        # Check for game acceptance messages
        if body.startswith("***GAME_ACCEPTED***"):
            # Extract opponent name and acceptor's symbol from message
            try:
                msg_content = body.replace("***GAME_ACCEPTED***", "")
                # Parse format: opponent_name|acceptor_symbol
                if "|" in msg_content:
                    opponent_name, acceptor_symbol = msg_content.split("|", 1)
                else:
                    # Fallback for old format without symbol
                    opponent_name = msg_content
                    acceptor_symbol = random.choice(["X", "O"])

                # Inviter gets the opposite symbol of what acceptor chose
                inviter_symbol = "O" if acceptor_symbol == "X" else "X"

                # Redirect to game screen
                game_screen = self.manager.get_screen("game")
                try:
                    chat_screen = self.manager.get_screen("chat")
                except:
                    chat_screen = None

                # Clear invites now that a game is starting
                self.clear_invites_for_chat(opponent_name)
                if chat_screen and chat_screen.chat_id == opponent_name:
                    chat_screen.has_pending_invite = False
                    chat_screen.update_invite_stats()

                game_screen.setup_game(
                    player_name=self.username,
                    opponent_name=opponent_name,
                    chat_screen=chat_screen,
                    # Pass ChatScreen as score holder
                    score_holder=chat_screen if chat_screen else None,
                    initial_player="X"
                )

                # Inviter is the opposite symbol of acceptor
                game_screen.player_symbol = inviter_symbol
                game_screen.opponent_symbol = acceptor_symbol

                Clock.schedule_once(lambda dt: setattr(
                    self.manager, 'current', 'game'), 0.1)
            except Exception:
                pass
            return

        # Check for game move messages
        if body.startswith("***GAME_MOVE***"):
            # Extract game state and process it
            try:
                game_screen = self.manager.get_screen("game")
                if self.manager.current == "game":
                    # Parse: ***GAME_MOVE***[board_state]***current_player
                    parts = body.split("***")
                    if len(parts) >= 4:
                        board_str = parts[2]
                        current_player = parts[3]
                        game_screen.receive_opponent_move(
                            board_str, current_player)
                return
            except Exception:
                pass

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

    def route_json_message(self, msg_obj):
        """Route incoming JSON messages to appropriate handler"""
        try:
            msg_type = msg_obj.get("type", "")
            data = msg_obj.get("data", {})

            # Debug logging
            print(f"[JSON] Received: type={msg_type}, data={data}")

            if msg_type == "USERLIST":
                names = data.get("users", [])
                print(f"[JSON] Processing USERLIST: {names}")
                Clock.schedule_once(
                    lambda dt, n=names: self.update_user_buttons(n), 0.1)
                return  # Early return

            elif msg_type == "AVATAR":
                username = data.get("username", "")
                avatar = data.get("avatar", "")
                print(f"[JSON] Processing AVATAR: {username} -> {avatar}")
                if username and avatar:
                    user_avatars[username] = avatar
                    if username == self.username:
                        Clock.schedule_once(
                            lambda dt: self.update_current_user_avatar())
                    Clock.schedule_once(
                        lambda dt: self.update_user_buttons(self.online_users))
                    Clock.schedule_once(lambda dt: self.update_chat_cards())
                    try:
                        chat_screen = self.manager.get_screen("chat")
                        if self.manager.current == "chat":
                            if chat_screen.chat_id == "general" or chat_screen.chat_id == username or self.username == username:
                                Clock.schedule_once(
                                    lambda dt: chat_screen.refresh_messages())
                    except Exception:
                        pass
                return  # Early return

            elif msg_type == "AVATAR_ERROR":
                Clock.schedule_once(lambda dt: self.show_avatar_error_popup())
                return  # Early return

            elif msg_type == "CHAT":
                sender = data.get("sender", "")
                recipient = data.get("recipient", "general")
                text = data.get("text", "")
                is_self = (sender == self.username)

                print(
                    f"[JSON] Processing CHAT: from={sender}, to={recipient}, self={is_self}")

                if recipient == "general":
                    chat_id = "general"
                else:
                    # For private chat, use sender name if it's from someone else, else use recipient
                    chat_id = sender if not is_self else recipient

                if chat_id not in self.chats:
                    self.chats[chat_id] = {"messages": [], "unread": 0}

                if is_self:
                    return  # Don't process our own echo
                else:
                    self.chats[chat_id]["messages"].append(
                        {"username": sender, "text": text, "is_own": False})
                    try:
                        chat_screen = self.manager.get_screen("chat")
                        if self.manager.current == "chat" and chat_screen.chat_id == chat_id:
                            self.chats[chat_id]["unread"] = 0
                            chat_screen.add_message_bubble(
                                sender, text, is_own=False)
                            Clock.schedule_once(
                                lambda dt: chat_screen.scroll_to_bottom(), 0.05)
                        else:
                            self.chats[chat_id]["unread"] += 1
                    except Exception:
                        self.chats[chat_id]["unread"] += 1
                    self.update_chat_cards()
                return  # Early return

            elif msg_type == "SYSTEM":
                text = data.get("text", "")
                chat_id = data.get("chat_id", "general")
                print(f"[JSON] Processing SYSTEM: {text} in {chat_id}")
                if chat_id not in self.chats:
                    self.chats[chat_id] = {"messages": [], "unread": 0}
                self.chats[chat_id]["messages"].append(
                    {"username": "SYSTEM", "text": text, "is_own": False})
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == chat_id:
                        chat_screen.add_system_message(text)
                        Clock.schedule_once(
                            lambda dt: chat_screen.scroll_to_bottom(), 0.05)
                    else:
                        self.chats[chat_id]["unread"] += 1
                except Exception:
                    self.chats[chat_id]["unread"] += 1
                self.update_chat_cards()
                return  # Early return

            elif msg_type == "GAME_INVITE":
                opponent = data.get("opponent", "")
                if opponent not in self.chats:
                    self.chats[opponent] = {"messages": [], "unread": 0}
                self.chats[opponent]["messages"].append(
                    {"username": opponent, "text": f"***GAME_INVITE***{opponent}", "is_own": False})
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == opponent:
                        chat_screen.add_game_invite_button(opponent, opponent)
                        chat_screen.has_pending_invite = True
                        Clock.schedule_once(
                            lambda dt: chat_screen.scroll_to_bottom(), 0.05)
                    else:
                        self.chats[opponent]["unread"] += 1
                except Exception:
                    self.chats[opponent]["unread"] += 1
                self.update_chat_cards()
                return  # Early return

            elif msg_type == "GAME_MOVE":
                board = data.get("board", [])
                current_player = data.get("current_player", "X")
                try:
                    game_screen = self.manager.get_screen("game")
                    if game_screen and hasattr(game_screen, 'receive_opponent_move'):
                        game_screen.receive_opponent_move(
                            str(board), current_player)
                except Exception:
                    pass
                return  # Early return

            elif msg_type == "GAME_END":
                result = data.get("result", "DRAW")
                try:
                    game_screen = self.manager.get_screen("game")
                    if game_screen and hasattr(game_screen, 'receive_opponent_game_end'):
                        game_screen.receive_opponent_game_end(
                            result, show_popup=True)
                except Exception:
                    pass
                return  # Early return

            elif msg_type == "GAME_RESET":
                player_name = data.get("player", "")
                symbol = data.get("symbol", "X")
                try:
                    game_screen = self.manager.get_screen("game")
                    if game_screen:
                        game_screen.next_game_my_symbol = "O" if symbol == "X" else "X"
                        game_screen.next_game_opponent_symbol = symbol
                        game_screen.receive_opponent_reset()
                except Exception:
                    pass
                return  # Early return

            elif msg_type == "GAME_ACCEPTED":
                player_name = data.get("player", "")  # The acceptor
                symbol = data.get("symbol", "X")  # Acceptor's chosen symbol
                # Should be us (the inviter)
                opponent = data.get("opponent", "")

                # This means someone accepted OUR invite, so we're the inviter
                # The acceptor chose their symbol, we get the opposite
                inviter_symbol = "O" if symbol == "X" else "X"

                try:
                    # Find the chat screen to use as reference
                    chat_screen = None
                    try:
                        chat_screen = self.manager.get_screen("chat")
                    except:
                        pass

                    # Setup and navigate to game screen
                    game_screen = self.manager.get_screen("game")
                    game_screen.setup_game(
                        player_name=self.username,
                        opponent_name=player_name,
                        chat_screen=chat_screen,
                        score_holder=chat_screen if chat_screen and chat_screen.chat_id == player_name else None,
                        initial_player="X"  # X always starts
                    )
                    game_screen.player_symbol = inviter_symbol
                    game_screen.opponent_symbol = symbol

                    # Clear pending invite
                    if chat_screen and chat_screen.chat_id == player_name:
                        chat_screen.has_pending_invite = False
                        self.clear_invites_for_chat(player_name)

                    # Navigate to game screen
                    self.manager.current = "game"
                except Exception as e:
                    print(f"Error handling GAME_ACCEPTED: {e}")
                    import traceback
                    traceback.print_exc()
                return  # Early return

            elif msg_type == "GAME_LEFT":
                player_name = data.get("player", "")
                try:
                    self.clear_invites_for_chat(player_name)
                    if self.manager.current == "game":
                        # Show popup and redirect to chat
                        def show_left_popup(dt):
                            content = BoxLayout(
                                orientation="vertical", spacing=15, padding=20)
                            content.add_widget(
                                Label(text=f"{player_name} left the game", font_size=18))
                            btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                                         background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

                            # Add rounded border
                            with btn.canvas.after:
                                Color(*OWN_COLOR)
                                btn.border_line = Line(rounded_rectangle=(
                                    btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
                            btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                                     size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

                            content.add_widget(btn)

                            popup = Popup(title="Game Ended", content=content,
                                          size_hint=(0.7, 0.3), auto_dismiss=False)
                            popup.background = ""
                            popup.background_color = BASE_BG
                            popup.title_size = 20

                            def on_close(instance):
                                popup.dismiss()
                                # Navigate to chat screen
                                try:
                                    chat_screen = self.manager.get_screen(
                                        "chat")
                                    if chat_screen.chat_id == player_name or chat_screen.chat_id == self.username:
                                        self.manager.current = "chat"
                                    else:
                                        # Load the private chat with that user
                                        chat_screen.load_chat(
                                            player_name, self)
                                        self.manager.current = "chat"
                                except:
                                    self.manager.current = "main"

                            btn.bind(on_press=on_close)
                            popup.open()

                        Clock.schedule_once(show_left_popup, 0.1)
                except Exception as e:
                    print(f"Error handling GAME_LEFT: {e}")
                return  # Early return

            else:
                # Unknown message type
                print(f"[JSON] Unknown message type: {msg_type}")
                return  # Early return

        except Exception as e:
            print(f"[JSON] Error routing JSON message: {e}")
            import traceback
            traceback.print_exc()

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

                # Check if user is currently viewing this chat or game
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == user:
                        # Navigate back to main screen
                        Clock.schedule_once(lambda dt: setattr(
                            self.manager, 'current', 'main'), 0.5)
                    elif self.manager.current == "game":
                        # If on game screen with this user, go back to main
                        Clock.schedule_once(lambda dt: setattr(
                            self.manager, 'current', 'main'), 0.5)
                except Exception:
                    pass

                # Remove the chat
                self.remove_chat(user)

        holder = self.ids.user_list
        holder.clear_widgets()

        # Update user bubble widget
        avatar_file = user_avatars.get(self.username)
        avatar_source = None
        if avatar_file:
            avatar_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "assets", "avatars", avatar_file)
            if os.path.exists(avatar_path):
                avatar_source = avatar_path

        self.ids.user_bubble_widget.set_user(self.username, avatar_source)

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
                     background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

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
                     background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

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

    def show_avatar_error_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Avatar change failed", font_size=18))
        btn = Button(text="OK", size_hint_y=None, height=45, background_normal="",
                     background_color=DARK_BG2, color=TEXT_PRIMARY, bold=True)

        with btn.canvas.after:
            Color(*ALERT_COLOR)
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(pos=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)),
                 size=lambda inst, val: setattr(inst.border_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, 8)))

        content.add_widget(btn)
        popup = Popup(title="Avatar Error", content=content,
                      size_hint=(0.6, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda x: popup.dismiss())
        popup.open()
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def remove_chat(self, chat_id):
        """Remove a chat from the chats dictionary and update UI"""
        if chat_id in self.chats:
            del self.chats[chat_id]
        # Clear game records for this user to reset scores
        if chat_id in self.game_records:
            del self.game_records[chat_id]
        self.update_chat_cards()

    def return_to_login(self, popup):
        popup.dismiss()
        self.manager.current = "login"

    def update_current_user_avatar(self):
        if not self.username:
            return

        avatar_file = user_avatars.get(self.username)
        avatar_source = None
        if avatar_file:
            avatar_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "assets", "avatars", avatar_file)
            if os.path.exists(avatar_path):
                avatar_source = avatar_path

        # Update the bubble widget
        self.ids.user_bubble_widget.set_user(self.username, avatar_source)

        try:
            chat_screen = self.manager.get_screen("chat")
            chat_screen.ids.user_bubble_widget.set_user(
                self.username, avatar_source)
        except Exception:
            pass


class ChatScreen(Screen):
    invite_stats_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_id = None
        self.main_screen = None
        self.has_pending_invite = False  # Track if there's an active invite
        self.wins = 0  # This chat's game wins
        self.losses = 0  # This chat's game losses

    def load_chat(self, chat_id, main_screen):
        self.chat_id = chat_id
        self.main_screen = main_screen
        self.has_pending_invite = False  # Reset when loading chat

        # Load scores from game_records
        if chat_id != "general" and main_screen:
            record = main_screen.game_records.get(
                chat_id, {"wins": 0, "losses": 0})
            self.wins = record.get("wins", 0)
            self.losses = record.get("losses", 0)
        else:
            self.wins = 0
            self.losses = 0

        # Set title
        if chat_id == "general":
            self.ids.chat_title.text = "General Chat"
        else:
            self.ids.chat_title.text = f"{chat_id}"

        # Update user bubble widget
        avatar_file = user_avatars.get(main_screen.username)
        avatar_source = None
        if avatar_file:
            avatar_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "assets", "avatars", avatar_file)
            if os.path.exists(avatar_path):
                avatar_source = avatar_path

        self.ids.user_bubble_widget.set_user(
            main_screen.username, avatar_source)
        self.ids.user_bubble_widget.on_press_callback = self.main_screen.open_avatar_picker

        # Show game invite button only for private chats (not "general")
        is_private = chat_id != "general"
        self.ids.invite_container.opacity = 1 if is_private else 0
        self.ids.invite_container.disabled = not is_private
        if is_private:
            self.update_invite_stats()
        else:
            self.invite_stats_text = ""

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

    def update_invite_stats(self):
        """Refresh the invite W/L indicator for this chat"""
        if not self.main_screen or self.chat_id == "general":
            self.invite_stats_text = ""
            return

        self.invite_stats_text = f"{self.wins}/{self.losses}"

    def add_message_bubble(self, username, text, is_own):
        # Check if this is a game invite
        if text.startswith("***GAME_INVITE***"):
            opponent_name = text.replace("***GAME_INVITE***", "")
            if is_own:
                # Show confirmation for the sender
                self.add_system_message(
                    f"You invited {opponent_name} to play Tic-Tac-Toe!")
                self.has_pending_invite = True  # Mark that invite is pending
            else:
                # Show invite button for the receiver
                # username is the inviter, so they are the opponent
                self.add_game_invite_button(username, username)
                self.has_pending_invite = True  # Mark that invite is pending
            return

        # Don't display GAME_ACCEPTED messages
        if text.startswith("***GAME_ACCEPTED***"):
            return

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

        # Add to local chat
        if self.chat_id not in self.main_screen.chats:
            self.main_screen.chats[self.chat_id] = {
                "messages": [], "unread": 0}

        self.main_screen.chats[self.chat_id]["messages"].append(
            {"username": self.main_screen.username, "text": text.strip(), "is_own": True})
        self.add_message_bubble(self.main_screen.username,
                                text.strip(), is_own=True)

        # Send to server as JSON
        try:
            send_json_message(
                self.main_screen.sock,
                "CHAT",
                {
                    "sender": self.main_screen.username,
                    "recipient": self.chat_id,
                    "text": text.strip()
                }
            )
        except:
            self.main_screen.on_disconnected()

        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)
        # Refocus the message input so user can send multiple messages quickly
        Clock.schedule_once(lambda dt: setattr(
            self.ids.message_input, 'focus', True), 0.1)

    def add_game_invite_button(self, opponent_name, inviter_name):
        """Add a clickable game invite button to the chat"""
        container = BoxLayout(size_hint_y=None, height=dp(
            60), padding=dp(10), spacing=dp(10))

        # Invite message
        msg_label = Label(
            text=f"{inviter_name} invited you to Tic-Tac-Toe!",
            color=TEXT_PRIMARY,
            size_hint_x=1,
            font_size='14sp'
        )
        msg_label.bind(texture_size=msg_label.setter('size'))

        # Accept button
        accept_btn = StyledButton(
            text="PLAY",
            size_hint_x=None,
            width=dp(70)
        )

        def on_accept_press(instance):
            # Disable button after first click
            accept_btn.disabled = True
            accept_btn.opacity = 0.5
            self.has_pending_invite = False  # Clear pending invite
            self.accept_game_invite(opponent_name)

        accept_btn.bind(on_press=on_accept_press)

        container.add_widget(msg_label)
        container.add_widget(accept_btn)

        # Style the container
        with container.canvas.before:
            Color(*OTHER_COLOR)
            container.bg = RoundedRectangle(
                radius=[dp(12)], pos=container.pos, size=container.size)

        container.bind(
            pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
            size=lambda inst, v: setattr(inst.bg, "size", inst.size)
        )

        self.ids.chat_box.add_widget(container)
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)

    def scroll_to_bottom(self):
        if self.ids.chat_box.height > self.ids.chat_scroll.height:
            self.ids.chat_scroll.scroll_y = 0

    def go_back(self):
        self.manager.current = "main"

    def send_game_invite(self):
        """Send a game invite to the user in this private chat"""
        if self.chat_id == "general":
            return

        # Always clear previous invites so only one stays visible per chat
        if self.main_screen:
            self.main_screen.clear_invites_for_chat(self.chat_id)
        self.has_pending_invite = False

        # Send special game invite message as JSON
        try:
            send_json_message(
                self.main_screen.sock,
                "GAME_INVITE",
                {"opponent": self.chat_id}
            )
            # Show confirmation message to the sender
            self.add_system_message(
                f"You invited {self.chat_id} to play Tic-Tac-Toe!")
            self.has_pending_invite = True  # Mark that we sent an invite
        except:
            self.main_screen.on_disconnected()

    def accept_game_invite(self, opponent):
        """Accept a game invite and navigate to game screen"""
        # The acceptor (this player) randomly chooses their own symbol
        acceptor_symbol = random.choice(["X", "O"])

        # Send acceptance message with acceptor's symbol as JSON
        try:
            send_json_message(
                self.main_screen.sock,
                "GAME_ACCEPTED",
                {
                    "player": self.main_screen.username,
                    "symbol": acceptor_symbol,
                    "opponent": opponent
                }
            )
        except:
            self.main_screen.on_disconnected()

        # Clear pending invite flag
        self.has_pending_invite = False
        if self.main_screen:
            self.main_screen.clear_invites_for_chat(self.chat_id)

        # Setup game with the acceptor's symbol
        game_screen = self.manager.get_screen("game")
        game_screen.setup_game(
            player_name=self.main_screen.username,
            opponent_name=opponent,
            chat_screen=self,
            score_holder=self,  # Pass ChatScreen's score container
            initial_player="X"  # Will be overridden below
        )
        # Acceptor is the chosen symbol, opponent is the other
        game_screen.player_symbol = acceptor_symbol
        game_screen.opponent_symbol = "O" if acceptor_symbol == "X" else "X"

        self.manager.current = "game"


# ============ TIC-TAC-TOE GAME LOGIC ============

class TicTacToeGame:
    """Tic-Tac-Toe game logic"""

    def __init__(self):
        self.board = [None] * 9  # 9 cells: 0-8
        self.current_player = "X"  # X always goes first
        self.game_over = False
        self.winner = None
        self.move_count = 0

    def is_valid_move(self, cell):
        """Check if a move is valid"""
        return 0 <= cell < 9 and self.board[cell] is None

    def make_move(self, cell, player):
        """Make a move. Returns True if successful"""
        if not self.is_valid_move(cell):
            return False
        self.board[cell] = player
        self.move_count += 1
        return True

    def get_winner(self):
        """Check if there's a winner. Returns 'X', 'O', 'DRAW', or None"""
        # Winning combinations
        winning_combos = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]               # Diagonals
        ]

        # Check for winning combinations first
        for combo in winning_combos:
            a, b, c = combo
            if self.board[a] is not None and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]

        # Check for draw (all cells filled, no winner)
        if None not in self.board:
            return "DRAW"

        return None

        return None

    def reset(self):
        """Reset the game"""
        self.board = [None] * 9
        self.current_player = "X"
        self.game_over = False
        self.winner = None
        self.move_count = 0


class GameScreen(Screen):
    """Tic-Tac-Toe game screen"""
    cell_size = NumericProperty(dp(80))
    grid_size = NumericProperty(dp(258))  # (3 * 80) + (2 * 6) + 6 = 258

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game = TicTacToeGame()
        self.player_name = ""
        self.opponent_name = ""
        self.player_symbol = "X"  # This player's symbol
        self.opponent_symbol = "O"
        self.player_score = 0
        self.opponent_score = 0
        self.chat_screen = None
        self.main_screen = None  # Store main_screen reference for score updates
        self.score_holder = None  # Reference to ChatScreen for direct score updates
        self.cell_buttons = []
        self.next_game_my_symbol = "X"  # Default symbol for next game
        self.next_game_opponent_symbol = "O"  # Default opponent symbol for next game

    def on_enter(self):
        """Called when screen is displayed"""
        self.setup_board()

    def setup_game(self, player_name, opponent_name, chat_screen, score_holder=None, initial_player="X", randomize_start=False):
        """Setup the game with player info"""
        self.player_name = player_name
        self.opponent_name = opponent_name
        self.chat_screen = chat_screen
        self.score_holder = score_holder  # Store reference to ChatScreen's score container
        if chat_screen:
            self.main_screen = chat_screen.main_screen

        # Randomize starting player if requested
        if randomize_start:
            initial_player = random.choice(["X", "O"])

        self.player_symbol = initial_player
        self.opponent_symbol = "O" if initial_player == "X" else "X"

        # Load initial scores from score_holder if available
        if self.score_holder:
            self.player_score = self.score_holder.wins
            self.opponent_score = self.score_holder.losses

        self.game.reset()

        # Hide new game button since a fresh game is starting
        self.ids.new_game_btn.opacity = 0
        self.ids.new_game_btn.disabled = True

        # Clear the board immediately to prevent flashing old grid
        Clock.schedule_once(lambda dt: self.setup_board(), 0)

        if self.chat_screen:
            try:
                self.chat_screen.main_screen.clear_invites_for_chat(
                    self.chat_screen.chat_id)
                self.chat_screen.has_pending_invite = False
                self.chat_screen.update_invite_stats()
            except Exception:
                pass

    def setup_board(self):
        """Create the game board with buttons"""
        board_widget = self.ids.game_board
        board_widget.clear_widgets()
        self.cell_buttons = []

        for i in range(9):
            btn = StyledButton(
                text="",
                size_hint=(None, None),
                size=(self.cell_size, self.cell_size)
            )
            btn.cell_index = i
            # Prepare buttons to display icons instead of text
            btn.display_mode = "icon"
            btn.image_source = ""
            btn.bind(on_press=self.on_cell_press)
            board_widget.add_widget(btn)
            self.cell_buttons.append(btn)

        self.update_status()
        self.update_score()

    def on_cell_press(self, button):
        """Handle cell press"""
        if self.game.game_over:
            return

        cell = button.cell_index

        # Check if it's the current player's turn
        if self.game.current_player != self.player_symbol:
            return

        # Make the move
        if self.game.make_move(cell, self.player_symbol):
            self.update_board()

            # Check for winner
            result = self.game.get_winner()
            if result:
                self.game.game_over = True
                # Send the final move first so opponent sees the complete board
                self.send_game_move(cell)
                self.handle_game_end(result)
                return

            # Switch player
            self.game.current_player = self.opponent_symbol
            self.update_status()

            # Send move to opponent via chat message
            self.send_game_move(cell)

    def send_game_move(self, cell):
        """Send move to opponent through chat"""
        if not self.chat_screen:
            return

        try:
            send_json_message(
                self.chat_screen.main_screen.sock,
                "GAME_MOVE",
                {
                    "board": self.game.board,
                    "current_player": self.game.current_player,
                    "opponent": self.opponent_name
                }
            )
        except:
            pass

    def handle_game_end(self, result):
        """Handle game end"""
        if result == "DRAW":
            self.ids.game_status_label.text = "It's a Tie!"
            status_msg = "DRAW"
        elif result == self.player_symbol:
            self.ids.game_status_label.text = "You Won!"
            self.player_score += 1
            status_msg = "WON"
        else:
            self.ids.game_status_label.text = "You Lost!"
            self.opponent_score += 1
            status_msg = "LOST"

        self.update_score()
        self.record_result(status_msg)

        # Show new game button
        self.ids.new_game_btn.opacity = 1
        self.ids.new_game_btn.disabled = False

        # Send game end message so opponent knows game ended and can show their popup
        if self.chat_screen:
            try:
                send_json_message(
                    self.chat_screen.main_screen.sock,
                    "GAME_END",
                    {
                        "result": result,
                        "opponent": self.opponent_name
                    }
                )
            except:
                pass

        # Show result popup
        self.show_game_end_popup(status_msg)

    def update_board(self):
        """Update board display using X/O images"""
        for i, btn in enumerate(self.cell_buttons):
            cell_value = self.game.board[i]
            if cell_value == "X":
                btn.text = ""
                btn.display_mode = "icon"
                btn.image_source = "assets/icons/X.png"
                if cell_value == self.player_symbol:
                    # User's cells: blue background and border
                    btn.background_color = OWN_COLOR
                    btn.border_color = OWN_COLOR
                else:
                    # Opponent's cells: purple
                    btn.background_color = OTHER_COLOR
                    btn.border_color = OTHER_COLOR
            elif cell_value == "O":
                btn.text = ""
                btn.display_mode = "icon"
                btn.image_source = "assets/icons/O.png"
                if cell_value == self.player_symbol:
                    # User's cells: blue background and border
                    btn.background_color = OWN_COLOR
                    btn.border_color = OWN_COLOR
                else:
                    # Opponent's cells: purple
                    btn.background_color = OTHER_COLOR
                    btn.border_color = OTHER_COLOR
            else:
                # Empty cell
                btn.text = ""
                btn.image_source = ""

    def update_status(self):
        """Update game status label"""
        if not self.game.game_over:
            if self.game.current_player == self.player_symbol:
                self.ids.game_status_label.text = "Your Turn"
                self.ids.game_status_label.color = OWN_COLOR
            else:
                self.ids.game_status_label.text = f"{self.opponent_name}'s Turn"
                self.ids.game_status_label.color = OTHER_COLOR

    def update_score(self):
        """Update score display"""
        self.ids.score_label.text = f"You: {self.player_score} | {self.opponent_name}: {self.opponent_score}"

    def record_result(self, status_msg):
        """Persist win/loss stats by updating score_holder directly"""
        # Update the score_holder (ChatScreen) directly so both players see the update
        if self.score_holder:
            self.score_holder.wins = self.player_score
            self.score_holder.losses = self.opponent_score
            self.score_holder.update_invite_stats()

        # Also update game_records for persistence
        main_screen = None
        if self.chat_screen and self.chat_screen.main_screen:
            main_screen = self.chat_screen.main_screen
        elif self.main_screen:
            main_screen = self.main_screen

        if main_screen:
            record = main_screen.game_records.setdefault(
                self.opponent_name, {"wins": 0, "losses": 0})
            record["wins"] = self.player_score
            record["losses"] = self.opponent_score

    def reset_game(self):
        """Start a new game"""
        self.game.reset()

        # This player (the one pressing the button) chooses their own symbol
        my_symbol = random.choice(["X", "O"])
        self.player_symbol = my_symbol
        self.opponent_symbol = "O" if my_symbol == "X" else "X"

        self.setup_board()

        # Hide new game button
        self.ids.new_game_btn.opacity = 0
        self.ids.new_game_btn.disabled = True

        # Send reset message to opponent with my chosen symbol
        self.send_game_reset(my_symbol)

    def send_game_reset(self, my_symbol):
        """Send game reset message to opponent with my chosen symbol"""
        if not self.chat_screen:
            return

        try:
            send_json_message(
                self.chat_screen.main_screen.sock,
                "GAME_RESET",
                {
                    "player": self.player_name,
                    "symbol": my_symbol,
                    "opponent": self.opponent_name
                }
            )
        except:
            pass

    def receive_opponent_reset(self):
        """Receive and process opponent's game reset"""
        if self.game.game_over:
            # Show notification
            self.chat_screen.add_system_message(
                f"{self.opponent_name} started a new game!")

        self.game.reset()

        # Use the symbols received from the opponent's reset message
        if hasattr(self, 'next_game_my_symbol'):
            self.player_symbol = self.next_game_my_symbol
            self.opponent_symbol = self.next_game_opponent_symbol
        else:
            # Fallback if symbols weren't set (shouldn't happen)
            self.player_symbol = "X"
            self.opponent_symbol = "O"

        self.setup_board()

        # Hide new game button
        self.ids.new_game_btn.opacity = 0
        self.ids.new_game_btn.disabled = True

    def show_game_end_popup(self, result):
        """Show popup with game result"""
        if result == "WON":
            status_text = "You Won!"
            popup_msg = f"Congratulations! You defeated {self.opponent_name}!"
            print(self.opponent_name)
            border_color = (34/255, 177/255, 76/255, 1)  # Green
        elif result == "LOST":
            status_text = "You Lost"
            popup_msg = f"{self.opponent_name} defeated you!"
            print(self.opponent_name)
            border_color = (231/255, 76/255, 60/255, 1)  # Red
        else:  # DRAW
            status_text = "It's a Draw!"
            popup_msg = "Great match! It's a draw!"
            border_color = (52/255, 152/255, 219/255, 1)  # Cyan/Blue

        # Create custom popup content
        content = BoxLayout(
            orientation="vertical",
            spacing=0,
            padding=0,
            size_hint=(None, None),
            size=(dp(320), dp(320))
        )

        # Add background and border
        with content.canvas.before:
            # Dark background
            Color(14/255, 16/255, 32/255, 1)  # BASE_BG
            content.bg = RoundedRectangle(
                radius=[dp(15)],
                pos=content.pos,
                size=content.size
            )
            # Colored border
            Color(*border_color)
            content.border = Line(
                rounded_rectangle=(content.x, content.y,
                                   content.width, content.height, dp(15)),
                width=dp(3)
            )

        def update_popup_graphics(inst, val):
            content.bg.pos = inst.pos
            content.bg.size = inst.size
            content.border.rounded_rectangle = (
                inst.x, inst.y, inst.width, inst.height, dp(15))

        content.bind(pos=update_popup_graphics, size=update_popup_graphics)

        # Status label
        status_label = Label(
            text=status_text,
            color=border_color,
            font_size="28sp",
            bold=True,
            size_hint_y=0.35,
            halign="center",
            valign="middle"
        )
        status_label.bind(size=lambda inst, val: setattr(
            inst, 'text_size', inst.size))
        content.add_widget(status_label)

        # Separator line
        separator = Widget(size_hint_y=0.05)
        with separator.canvas:
            Color(*border_color)
            separator.line = Line(
                points=[0, 0, dp(320), 0],
                width=dp(2)
            )

        def update_separator(inst, val):
            separator.line.points = [
                inst.x, inst.center_y, inst.x + inst.width, inst.center_y]

        separator.bind(pos=update_separator, size=update_separator)
        content.add_widget(separator)

        # Message label
        message_label = Label(
            text=popup_msg,
            color=TEXT_PRIMARY,
            font_size="16sp",
            size_hint_y=0.35,
            halign="center",
            valign="middle",
            padding=(dp(15), dp(10))
        )
        message_label.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (inst.width - dp(30), inst.height)))
        content.add_widget(message_label)

        # OK Button
        close_btn = StyledButton(
            text="OK",
            size_hint_y=0.25,
            border_color=border_color,
            background_color=DARK_BG2
        )
        content.add_widget(close_btn)

        # Create popup
        popup = Popup(
            content=content,
            size_hint=(None, None),
            size=(dp(320), dp(320)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            background="",
            background_color=(0, 0, 0, 0)
        )

        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def receive_opponent_game_end(self, winner_symbol, show_popup=True):
        """Receive opponent's game end result to update score and show popup"""
        self.game.game_over = True

        if winner_symbol == "DRAW":
            # Draw - no score change
            self.ids.game_status_label.text = "It's a Tie!"
            status_msg = "DRAW"
        elif winner_symbol == self.opponent_symbol:
            # Opponent won, I lost
            self.opponent_score += 1
            self.ids.game_status_label.text = "You Lost!"
            status_msg = "LOST"
        elif winner_symbol == self.player_symbol:
            # I won
            self.player_score += 1
            self.ids.game_status_label.text = "You Won!"
            status_msg = "WON"
        else:
            # Fallback to draw if unexpected value
            self.ids.game_status_label.text = "It's a Tie!"
            status_msg = "DRAW"

        self.update_score()
        self.record_result(status_msg)

        # Show new game button
        self.ids.new_game_btn.opacity = 1
        self.ids.new_game_btn.disabled = False

        # Show popup for this player too when applicable
        if show_popup:
            self.show_game_end_popup(status_msg)

    def exit_game(self):
        """Exit the game and go back to chat"""
        # Send message that user is leaving
        if self.chat_screen:
            try:
                send_json_message(
                    self.chat_screen.main_screen.sock,
                    "GAME_LEFT",
                    {
                        "player": self.player_name,
                        "opponent": self.opponent_name
                    }
                )
            except:
                pass

        self.manager.current = "chat"

        if self.chat_screen:
            try:
                self.chat_screen.main_screen.clear_invites_for_chat(
                    self.chat_screen.chat_id)
                self.chat_screen.has_pending_invite = False
                self.chat_screen.update_invite_stats()
            except Exception:
                pass

    def receive_opponent_move(self, board_str, current_player):
        """Receive and process opponent's move"""
        if self.game.game_over:
            return

        try:
            # Parse the board string: "[None, None, ..., 'X', ...]"
            board_str = board_str.replace("None", "None")
            # Safe here since it's from our own protocol
            board_list = eval(board_str)

            # Update game board
            self.game.board = board_list
            self.game.move_count = sum(
                1 for cell in board_list if cell is not None)
            self.game.current_player = current_player

            # Update UI
            self.update_board()

            # Don't check for winner here - wait for explicit GAME_END message
            # This avoids double-processing game end (once here, once from GAME_END message)
            self.update_status()
        except Exception:
            pass


class ChatApp(App):
    def build(self):
        # Set window title and icon
        self.title = "Lord of the Pings"
        self.icon = "assets/icons/Lotp_Icon_BP.ico"

        # Start server discovery when app starts
        start_discovery()
        return Builder.load_string(KV)


if __name__ == "__main__":
    ChatApp().run()
