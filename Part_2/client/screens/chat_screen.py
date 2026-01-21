import random
from datetime import datetime

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from client.core import state
from client.config.constants import ALERT_COLOR, OTHER_COLOR, OWN_COLOR, SYSTEM_COLOR, TEXT_PRIMARY, TEXT_HINT
from client.config.paths import AVATARS_DIR
from client.core.protocol import send_json_message
from client.widgets.styled_button import StyledButton
from kivy.uix.image import Image


class ChatScreen(Screen):
    """Screen for displaying and managing chat conversations."""

    invite_stats_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_id = None
        self.main_screen = None
        self.has_pending_invite = False
        self.wins = 0
        self.losses = 0

    def load_chat(self, chat_id, main_screen):
        self.chat_id = chat_id
        self.main_screen = main_screen
        self.has_pending_invite = False

        if chat_id != "general" and main_screen:
            record = main_screen.game_records.get(
                chat_id, {"wins": 0, "losses": 0})
            self.wins = record.get("wins", 0)
            self.losses = record.get("losses", 0)
        else:
            self.wins = 0
            self.losses = 0

        if chat_id == "general":
            self.ids.chat_title.text = "General Chat"
        else:
            self.ids.chat_title.text = f"{chat_id}"

        avatar_file = state.user_avatars.get(main_screen.username)
        avatar_source = None
        if avatar_file:
            avatar_path = AVATARS_DIR / avatar_file
            if avatar_path.exists():
                avatar_source = str(avatar_path)

        self.ids.user_bubble_widget.set_user(
            main_screen.username, avatar_source)
        self.ids.user_bubble_widget.on_press_callback = self.main_screen.open_avatar_picker

        is_private = chat_id != "general"
        self.ids.invite_container.opacity = 1 if is_private else 0
        self.ids.invite_container.disabled = not is_private
        if is_private:
            self.update_invite_stats()
        else:
            self.invite_stats_text = ""

        self.refresh_messages()
        Clock.schedule_once(lambda dt: setattr(
            self.ids.message_input, "focus", True), 0.1)

    def refresh_messages(self):
        box = self.ids.chat_box
        box.clear_widgets()

        if self.chat_id and self.chat_id in self.main_screen.chats:
            messages = self.main_screen.chats[self.chat_id]["messages"]
            for msg in messages:
                username = msg.get("username", "Unknown")
                text = msg.get("text", "")
                is_own = msg.get("is_own", False)
                kind = msg.get("kind", "chat")

                if kind == "game_invite":
                    self.has_pending_invite = True
                    inviter = username or self.chat_id
                    if is_own:
                        self.add_system_message(
                            f"You invited {self.chat_id} to play Tic-Tac-Toe!")
                    else:
                        self.add_game_invite_button(inviter, inviter)
                    continue

                if kind == "system":
                    self.add_system_message(text)
                    continue

                self.add_message_bubble(username, text, is_own, kind=kind)

        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)

    def update_invite_stats(self):
        """Refresh the invite W/L indicator for this chat."""
        if not self.main_screen or self.chat_id == "general":
            self.invite_stats_text = ""
            return
        self.invite_stats_text = f"{self.wins}/{self.losses}"

    def add_message_bubble(self, username, text, is_own, kind="chat"):
        if kind == "game_invite":
            inviter = username or self.chat_id
            if is_own:
                self.add_system_message(
                    f"You invited {self.chat_id} to play Tic-Tac-Toe!")
            else:
                self.add_game_invite_button(inviter, inviter)
            self.has_pending_invite = True
            return

        if kind == "system":
            self.add_system_message(text)
            return

        is_system_message = "joined the chat" in text or "left the chat" in text

        if is_system_message:
            self.add_system_message(text)
            return

        bubble_color = OWN_COLOR if is_own else OTHER_COLOR
        time_str = datetime.now().strftime("%H:%M")
        avatar_file = state.user_avatars.get(username)
        avatar_widget = None

        if avatar_file:
            avatar_path = AVATARS_DIR / avatar_file
            if avatar_path.exists():
                avatar_widget = Image(
                    source=str(avatar_path),
                    size_hint=(None, None),
                    size=(dp(32), dp(32)),
                )

        bubble_layout = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            padding=(dp(12), dp(7)),
            spacing=dp(10),
        )

        username_label = None
        if not is_own:
            username_label = Label(
                text=username,
                color=TEXT_PRIMARY,
                size_hint=(None, None),
                halign="left",
                font_size="11sp",
                bold=True,
            )

            def update_username_size(inst, _val):
                inst.size = inst.texture_size

            username_label.bind(texture_size=update_username_size)
            username_label.text_size = (None, None)

        msg_label = Label(
            text=text,
            color=TEXT_PRIMARY,
            size_hint=(None, None),
            halign="left",
        )

        def update_msg_size(inst, _val):
            inst.size = inst.texture_size

        msg_label.bind(texture_size=update_msg_size)

        def set_text_size(_dt=None, width=None):
            max_width = width if width is not None else self.ids.chat_box.width * 0.7
            msg_label.text_size = (max(dp(100), min(max_width, dp(300))), None)

        Clock.schedule_once(set_text_size, 0)
        self.ids.chat_box.bind(
            width=lambda inst, val: set_text_size(width=val * 0.7))

        time_label = Label(
            text=time_str,
            color=(1, 1, 1, 1),
            font_size="10sp",
            size_hint=(1, None),
            height=18,
            halign="right",
        )
        time_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", (inst.width, None)))

        if username_label:
            bubble_layout.add_widget(username_label)
        bubble_layout.add_widget(msg_label)
        bubble_layout.add_widget(time_label)

        def update_bubble_size(inst, _val):
            name_width = username_label.width if username_label else 0
            name_height = username_label.height if username_label else 0
            num_elements = (1 if username_label else 0) + 1 + 1
            spacing_total = dp(6) * max(0, num_elements - 1)
            inst.width = max(msg_label.width, name_width, 65) + 24
            inst.height = name_height + msg_label.height + \
                time_label.height + dp(24) + spacing_total

        bubble_layout.bind(minimum_size=update_bubble_size)

        container = BoxLayout(size_hint_y=None)
        bubble_layout.bind(height=lambda inst,
                           val: setattr(container, "height", val))

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

        bubble_layout.bind(
            pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
            size=lambda inst, v: setattr(inst.bg, "size", inst.size),
        )

        self.ids.chat_box.add_widget(container)

    def add_system_message(self, text):
        """Add a centered system message."""
        time_str = datetime.now().strftime("%H:%M")

        container = BoxLayout(size_hint_y=None, height=dp(
            50), padding=(dp(10), dp(5)))

        bubble_layout = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            padding=(dp(15), dp(8)),
            pos_hint={"center_x": 0.5},
        )

        msg_label = Label(
            text=text,
            color=TEXT_PRIMARY,
            size_hint=(None, None),
            halign="center",
            italic=True,
            font_size="12sp",
        )

        def update_msg_size(inst, _val):
            inst.size = inst.texture_size

        msg_label.bind(texture_size=update_msg_size)

        def set_text_size(_dt=None, width=None):
            max_width = width if width is not None else self.ids.chat_box.width * 0.55
            msg_label.text_size = (max(dp(100), min(max_width, dp(250))), None)

        Clock.schedule_once(set_text_size, 0)
        self.ids.chat_box.bind(
            width=lambda inst, val: set_text_size(width=val * 0.55))

        time_label = Label(
            text=time_str,
            color=(1, 1, 1, 1),
            font_size="9sp",
            size_hint=(1, None),
            height=12,
            halign="center",
        )
        time_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", (inst.width, None)))

        bubble_layout.add_widget(msg_label)
        bubble_layout.add_widget(time_label)

        def update_bubble_size(inst, _val):
            inst.width = msg_label.width + 30
            inst.height = msg_label.height + time_label.height + 15

        bubble_layout.bind(minimum_size=update_bubble_size)

        container.add_widget(Widget())
        container.add_widget(bubble_layout)
        container.add_widget(Widget())

        with bubble_layout.canvas.before:
            Color(*SYSTEM_COLOR)
            bubble_layout.bg = RoundedRectangle(
                radius=[dp(12)], pos=bubble_layout.pos, size=bubble_layout.size)

        bubble_layout.bind(
            pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
            size=lambda inst, v: setattr(inst.bg, "size", inst.size),
        )

        self.ids.chat_box.add_widget(container)

    def send_message(self, text):
        if not text.strip():
            return
        self.ids.message_input.text = ""

        if self.chat_id not in self.main_screen.chats:
            self.main_screen.chats[self.chat_id] = {
                "messages": [], "unread": 0}

        self.main_screen.chats[self.chat_id]["messages"].append(
            {"username": self.main_screen.username,
                "text": text.strip(), "is_own": True, "kind": "chat"}
        )
        self.add_message_bubble(self.main_screen.username,
                                text.strip(), is_own=True, kind="chat")

        try:
            send_json_message(
                self.main_screen.sock,
                "CHAT",
                {
                    "sender": self.main_screen.username,
                    "recipient": self.chat_id,
                    "text": text.strip(),
                },
            )
        except Exception:
            self.main_screen.on_disconnected()

        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)
        Clock.schedule_once(lambda dt: setattr(
            self.ids.message_input, "focus", True), 0.1)

    def add_game_invite_button(self, opponent_name, inviter_name):
        """Add a clickable game invite button to the chat."""
        container = BoxLayout(size_hint_y=None, height=dp(
            60), padding=dp(10), spacing=dp(10))

        msg_label = Label(
            text=f"{inviter_name} invited you to Tic-Tac-Toe!",
            color=TEXT_PRIMARY,
            size_hint_x=1,
            font_size="14sp",
        )
        msg_label.bind(texture_size=msg_label.setter("size"))

        accept_btn = StyledButton(text="PLAY", size_hint_x=None, width=dp(70))

        def on_accept_press(_instance):
            accept_btn.disabled = True
            accept_btn.opacity = 0.5
            self.has_pending_invite = False
            self.accept_game_invite(opponent_name)

        accept_btn.bind(on_press=on_accept_press)

        container.add_widget(msg_label)
        container.add_widget(accept_btn)

        with container.canvas.before:
            Color(*OTHER_COLOR)
            container.bg = RoundedRectangle(
                radius=[dp(12)], pos=container.pos, size=container.size)

        container.bind(
            pos=lambda inst, v: setattr(inst.bg, "pos", inst.pos),
            size=lambda inst, v: setattr(inst.bg, "size", inst.size),
        )

        self.ids.chat_box.add_widget(container)
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)

    def scroll_to_bottom(self):
        if self.ids.chat_box.height > self.ids.chat_scroll.height:
            self.ids.chat_scroll.scroll_y = 0

    def go_back(self):
        self.manager.current = "main"

    def send_game_invite(self):
        """Send a game invite to the user in this private chat."""
        if self.chat_id == "general":
            return

        if self.main_screen:
            self.main_screen.clear_invites_for_chat(self.chat_id)
        self.has_pending_invite = False

        if self.main_screen:
            if self.chat_id not in self.main_screen.chats:
                self.main_screen.chats[self.chat_id] = {
                    "messages": [], "unread": 0}
            self.main_screen.chats[self.chat_id]["messages"].append(
                {"username": self.main_screen.username,
                    "is_own": True, "kind": "game_invite"}
            )

        try:
            send_json_message(self.main_screen.sock, "GAME_INVITE", {
                              "opponent": self.chat_id})
            self.add_system_message(
                f"You invited {self.chat_id} to play Tic-Tac-Toe!")
            self.has_pending_invite = True
        except Exception:
            self.main_screen.on_disconnected()

    def accept_game_invite(self, opponent):
        """Accept a game invite and navigate to game screen."""
        acceptor_symbol = random.choice(["X", "O"])

        try:
            send_json_message(
                self.main_screen.sock,
                "GAME_ACCEPTED",
                {"player": self.main_screen.username,
                    "symbol": acceptor_symbol, "opponent": opponent},
            )
        except Exception:
            self.main_screen.on_disconnected()

        self.has_pending_invite = False
        if self.main_screen:
            self.main_screen.clear_invites_for_chat(self.chat_id)

        game_screen = self.manager.get_screen("game")
        game_screen.setup_game(
            player_name=self.main_screen.username,
            opponent_name=opponent,
            chat_screen=self,
            score_holder=self,
            initial_player="X",
        )
        game_screen.player_symbol = acceptor_symbol
        game_screen.opponent_symbol = "O" if acceptor_symbol == "X" else "X"

        self.manager.current = "game"
