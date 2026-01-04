from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
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
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Line, RoundedRectangle

OTHER_COLOR = (239 / 255, 246 / 255, 173 / 255, 1)
OWN_COLOR = (242 / 255, 235 / 255, 50 / 255, 1)
# Light blue for system messages
SYSTEM_COLOR = (1, 1, 1, 0)

load_dotenv()

# ====== DISCOVERY CONFIG ======
DISCOVERY_PORT = 9001
DISCOVERY_TIMEOUT = 5  # seconds
DISCOVERY_PREFIX = "LOTP_SERVER|"

# ====== SERVER CONFIG ======
# Will be set dynamically via discovery, fallback to env vars if discovery fails
HOST = os.environ.get("HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 9000))

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
                    size_hint: (None, None)
                    size: (320, 55)
                    pos_hint: {"center_x": 0.5}
                    foreground_color: 0, 0, 0, 1
                    hint_text_color: 0.5, 0.5, 0.5, 1
                    background_color: 1, 1, 1, 1 
                    background_normal: "" 
                    padding: [15, (self.height - self.line_height) / 2]
                    on_text_validate: root.login(username_input.text)

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

<MainScreen>:
    name: "main"
    BoxLayout:
        orientation: "horizontal"

        # Main content - chat cards
        BoxLayout:
            orientation: "vertical"
            padding: 0
            spacing: 10

            # Header with Exit button
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

                BoxLayout:
                    size_hint: (None, None)
                    size: (85, 45)
                    pos_hint: {"center_y": 0.5}
                    halign: "left"
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
                        on_press: root.Exit_to_login()

                Label:
                    id: current_user_lbl
                    text: "User:"
                    color: 1, 1, 1, 1
                    bold: True
                    font_size: "18sp"
                    halign: "right"
                    text_size: self.size

            Label:
                text: "Chats"
                size_hint_y: None
                height: 50
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "left"
                padding: 15, 0
                text_size: self.size

            ScrollView:
                id: chats_scroll
                do_scroll_x: False
                bar_width: 6
                canvas.before:
                    Color:
                        rgba: 0.08, 0.08, 0.08, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                BoxLayout:
                    id: chats_container
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: [15, 10]
                    spacing: 12

        # Sidebar user list
        BoxLayout:
            orientation: "vertical"
            size_hint_x: 0.28
            padding: [10, 10]
            spacing: 10
            canvas.before:
                Color:
                    rgba: 0.1, 0.1, 0.1, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                text: "Users Online"
                size_hint_y: None
                height: 30
                color: 1, 1, 1, 1
                bold: True

            ScrollView:
                id: users_scroll
                do_scroll_x: False

                BoxLayout:
                    id: user_list
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: 8
                    padding: [0, 5]

<ChatScreen>:
    name: "chat"
    BoxLayout:
        orientation: "vertical"

        # Header with back button
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

            Button:
                text: "<--"
                size_hint: (None, None)
                size: (80, 45)
                background_normal: ""
                background_color: 0.25, 0.25, 0.25, 1
                color: 1, 1, 1, 1
                bold: True
                font_size: "24sp"
                on_press: root.go_back()

            Label:
                id: chat_title
                text: "General Chat"
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "left"
                text_size: self.size

            Label:
                id: current_user_lbl
                text: "User:"
                color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"
                halign: "right"
                text_size: self.size

        ScrollView:
            id: chat_scroll
            do_scroll_x: False
            bar_width: 6
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
            spacing: 10
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
                on_text_validate: root.send_message(message_input.text)

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

# ============ SERVER DISCOVERY FUNCTIONS =============


def discover_server():
    """
    Listens for UDP broadcast messages from the server.
    Returns (ip, port) or None if not found within timeout.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
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
    return None


def start_discovery():
    """
    Starts server discovery in a background thread.
    Updates the app's HOST and SERVER_PORT when found.
    """
    def worker():
        result = discover_server()
        Clock.schedule_once(lambda dt: on_discovery_finished(result))

    threading.Thread(target=worker, daemon=True).start()


def on_discovery_finished(result):
    """
    Handle discovery result and update global HOST and SERVER_PORT.
    """
    global HOST, SERVER_PORT
    if result:
        server_ip, server_port = result
        HOST = server_ip
        SERVER_PORT = server_port
        print(f"[Discovery] Discovered server at {HOST}:{SERVER_PORT}")
    else:
        print("[Discovery] Server not found automatically, using env vars")


# ============ if server online check function =============


def server_online():
    try:
        with socket.create_connection((HOST, SERVER_PORT), timeout=1.0) as s:
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

# ============LoginsScreen==================================================


class LoginScreen(Screen):
    def on_enter(self):
        # This tells Kivy: "Run self.check_status every 1 second"
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
            self.ids.server_status_lbl.color = (0, 1, 0, 1)
        else:
            self.ids.server_status_lbl.text = "OFFLINE"
            self.ids.server_status_lbl.color = (1, 0, 0, 1)

    def show_server_offline_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="server is down try again later", font_size=25))
        btn = Button(text="OK", size_hint_y=None, height=45)
        content.add_widget(btn)
        popup = Popup(title="Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        btn.bind(on_release=lambda x: self.return_to_login(popup))
        popup.open()
        # Give focus to the button by simulating a keyboard event
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def show_username_taken_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Username already taken. Please choose another.", font_size=22))
        btn = Button(text="OK", size_hint_y=None, height=45)
        content.add_widget(btn)
        popup = Popup(title="Username Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
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
            Color(242 / 255, 235 / 255, 50 / 255, 1)
            self.border_line = Line(rectangle=(
                ti.x, ti.y, ti.width, ti.height), width=1.5)

        def update_border(instance, value):
            self.border_line.rectangle = (ti.x, ti.y, ti.width, ti.height)

        ti.bind(pos=update_border, size=update_border)

    def login(self, username):
        if not username.strip():
            return
        app = App.get_running_app()
        prebuffer = b""
        try:
            app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            app.sock.connect((HOST, SERVER_PORT))
            app.sock.sendall(username.encode())

            # Short wait to capture immediate server response (e.g., username taken)
            app.sock.settimeout(1.0)
            try:
                prebuffer = app.sock.recv(1024)
            except socket.timeout:
                prebuffer = b""
            finally:
                # Return socket to blocking mode for listener thread
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
                else:
                    Clock.schedule_once(
                        lambda dt, m=line: main.route_message(m))

        threading.Thread(target=main.listen_to_server, daemon=True).start()
        self.manager.current = "main"


# ============ Main Screen ===============================


class ChatCard(ButtonBehavior, BoxLayout):
    def __init__(self, title, chat_id, parent_with_open_chat, unread=0, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=80, padding=(15, 10), spacing=15, **kwargs)
        self.chat_id = chat_id

        # Background
        with self.canvas.before:
            Color(0.18, 0.18, 0.18, 1)
            self.bg = RoundedRectangle(
                radius=[10], pos=self.pos, size=self.size)

        self.bind(pos=lambda inst, val: setattr(self.bg, "pos", inst.pos),
                  size=lambda inst, val: setattr(self.bg, "size", inst.size))

        # Chat info
        info_box = BoxLayout(orientation="vertical", spacing=5)

        title_label = Label(
            text=title,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="16sp",
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=25
        )
        title_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", inst.size))

        unread_label = Label(
            text=f"{unread} new messages" if unread > 0 else "No new messages",
            color=(0.7, 0.7, 0.7, 1),
            font_size="12sp",
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=20
        )
        unread_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", inst.size))

        info_box.add_widget(title_label)
        info_box.add_widget(unread_label)
        self.add_widget(info_box)

        # Bind click using the parent reference
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
            btn = Button(
                text=name,
                size_hint_y=None,
                height=40,
                background_normal="",
                background_color=(0.24, 0.24, 0.24, 1),
                color=(1, 1, 1, 1),
                bold=True
            )
            btn.bind(on_release=lambda inst, n=name: self.open_chat(n))
            holder.add_widget(btn)
        self.update_chat_cards()

    def update_chat_cards(self):
        container = self.ids.chats_container
        container.clear_widgets()

        # General chat card
        general_card = self.create_chat_card("General Chat", "general")
        container.add_widget(general_card)

        # Private chat cards
        for user in self.online_users:
            if user in self.chats:
                private_card = self.create_chat_card(f"{user}", user)
                container.add_widget(private_card)

    def create_chat_card(self, title, chat_id):
        unread = self.chats.get(chat_id, {}).get("unread", 0)
        return ChatCard(title, chat_id, parent_with_open_chat=self, unread=unread)

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
        # Only show disconnect popup if it wasn't a user-initiated disconnect
        if not self.user_initiated_disconnect:
            Clock.schedule_once(lambda dt: self.show_disconnect_popup())
        else:
            # Reset the flag for next session
            self.user_initiated_disconnect = False

    def show_disconnect_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Disconnected from server", font_size=16))
        btn = Button(text="OK", size_hint_y=None, height=45)
        content.add_widget(btn)
        popup = Popup(title="Error", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
        btn.bind(on_release=lambda x: self.return_to_login(popup))
        popup.open()
        # Give focus to the button by pressing it after a short delay
        Clock.schedule_once(lambda dt: btn.dispatch('on_press'), 0.2)

    def show_user_disconnected_popup(self, username):
        """Show popup when a user in a private chat disconnects"""
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text=f"{username} has disconnected", font_size=16))
        btn = Button(text="OK", size_hint_y=None, height=45)
        content.add_widget(btn)
        popup = Popup(title="User Disconnected", content=content,
                      size_hint=(0.7, 0.3), auto_dismiss=False)
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

        bubble_layout = BoxLayout(
            orientation='vertical', size_hint=(None, None), padding=(12, 8), spacing=5)

        # Username label
        username_label = Label(
            text=username,
            color=(0, 0, 0, 0.6),
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
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            halign='left'
        )

        def update_msg_size(inst, val):
            inst.size = inst.texture_size

        msg_label.bind(texture_size=update_msg_size)

        # Defer text_size until layout is ready to avoid 0-width wrap
        def set_text_size(_dt=None, width=None):
            w = width if width is not None else self.ids.chat_box.width * 0.75
            msg_label.text_size = (max(10, w), None)

        # Initial scheduling and live binding to container width
        Clock.schedule_once(set_text_size, 0)
        self.ids.chat_box.bind(
            width=lambda inst, val: set_text_size(width=val * 0.75))

        # Time label
        time_label = Label(
            text=time_str,
            color=(0, 0, 0, 0.4),
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
            container.add_widget(bubble_layout)
            container.add_widget(Widget())

        with bubble_layout.canvas.before:
            Color(*bubble_color)
            bubble_layout.bg = RoundedRectangle(
                radius=[12], pos=bubble_layout.pos, size=bubble_layout.size)

        bubble_layout.bind(pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
                           size=lambda inst, v: setattr(inst.bg, "size", inst.size))

        self.ids.chat_box.add_widget(container)

    def add_system_message(self, text):
        """Add a centered system message with different styling"""
        time_str = datetime.now().strftime("%H:%M")

        # Create centered container
        container = BoxLayout(
            size_hint_y=None,
            height=50,
            padding=(10, 5)
        )

        # Create system message bubble
        bubble_layout = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            padding=(15, 8),
            pos_hint={'center_x': 0.5}
        )

        msg_label = Label(
            text=text,
            color=(1, 1, 1, 1),  # White text for system messages
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
            w = width if width is not None else self.ids.chat_box.width * 0.6
            msg_label.text_size = (max(10, w), None)

        # Initial scheduling and live binding to container width
        Clock.schedule_once(set_text_size, 0)
        self.ids.chat_box.bind(
            width=lambda inst, val: set_text_size(width=val * 0.6))

        time_label = Label(
            text=time_str,
            color=(1, 1, 1, 0.5),
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
                radius=[12],
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
        # Start server discovery when app starts
        start_discovery()
        return Builder.load_string(KV)


if __name__ == "__main__":
    ChatApp().run()
