import threading
from pathlib import Path

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from client.core import state
from client.config.constants import ALERT_COLOR, BASE_BG, DARK_BG, DARK_BG2, OTHER_COLOR, OWN_COLOR, TEXT_PRIMARY
from client.core.discovery import restart_discovery
from client.config.paths import AVATARS_DIR
from client.core.protocol import parse_json_message, send_json_message
from client.widgets.avatar_button import AvatarButton


class UserButton(ButtonBehavior, BoxLayout):
    def __init__(self, username, callback, **kwargs):
        BoxLayout.__init__(self, size_hint_y=None, height=dp(
            40), padding=(dp(10), 0), **kwargs)
        ButtonBehavior.__init__(self)

        with self.canvas.before:
            Color(*DARK_BG)
            self.bg = RoundedRectangle(
                radius=[dp(8)], pos=self.pos, size=self.size)
            Color(*OTHER_COLOR)
            self.border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1.2
            )

        self.bind(pos=self._update_graphics, size=self._update_graphics)

        content = BoxLayout(orientation="horizontal",
                            spacing=dp(8), pos_hint={'center_y': 0.5})

        avatar_file = state.user_avatars.get(username)
        if avatar_file:
            avatar_path = AVATARS_DIR / avatar_file
            if avatar_path.exists():
                content.add_widget(
                    Image(
                        source=str(avatar_path),
                        size_hint=(None, None),
                        size=(dp(24), dp(24)),
                        pos_hint={'center_y': 0.5},
                    )
                )

        label = Label(
            text=username,
            color=TEXT_PRIMARY,
            bold=True,
            font_size="14sp",
            halign="left",
            valign="middle",
            shorten=True,
        )
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
        BoxLayout.__init__(
            self,
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=(dp(15), dp(5)),
            spacing=dp(12),
            **kwargs,
        )
        ButtonBehavior.__init__(self)

        self.chat_id = chat_id

        with self.canvas.before:
            Color(*DARK_BG)
            self.bg = RoundedRectangle(
                radius=[dp(10)], pos=self.pos, size=self.size)

        self.bind(pos=lambda inst, val: setattr(self.bg, "pos", inst.pos),
                  size=lambda inst, val: setattr(self.bg, "size", inst.size))

        info_box = BoxLayout(orientation="vertical",
                             size_hint_y=1, pos_hint={'center_y': 0.5})

        title_label = Label(
            text=title,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="16sp",
            halign="left",
            valign="middle",
        )
        title_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", inst.size))
        info_box.add_widget(title_label)

        if unread > 0:
            unread_label = Label(
                text=f"{unread} new messages",
                color=OWN_COLOR,
                font_size="11sp",
                halign="left",
                valign="middle",
            )
            unread_label.bind(size=lambda inst, val: setattr(
                inst, "text_size", inst.size))
            info_box.add_widget(unread_label)

        if chat_id != "general":
            avatar_file = state.user_avatars.get(chat_id)
            if avatar_file:
                avatar_path = AVATARS_DIR / avatar_file
                if avatar_path.exists():
                    self.add_widget(
                        Image(
                            source=str(avatar_path),
                            size_hint=(None, None),
                            size=(dp(30), dp(30)),
                            pos_hint={'center_y': 0.5},
                        )
                    )

        self.add_widget(info_box)
        self.bind(on_release=lambda inst: parent_with_open_chat.open_chat(chat_id))


class MainScreen(Screen):
    username = StringProperty("")
    drawer_open = BooleanProperty(False)
    sock = None
    user_initiated_disconnect = False

    def toggle_drawer(self):
        self.drawer_open = not self.drawer_open

    def close_drawer(self):
        self.drawer_open = False

    def disconnect_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def reset_chat_data(self):
        self.chats = {}
        self.online_users = []
        self.game_records = {}
        self.ids.chats_container.clear_widgets()
        self.ids.user_list.clear_widgets()
        state.user_avatars.clear()

    def clear_invites_for_chat(self, chat_id):
        if not chat_id or chat_id not in self.chats:
            return
        messages = self.chats[chat_id].get("messages", [])
        filtered = [m for m in messages if m.get("kind") != "game_invite"]
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
        self.chats = {}
        self.online_users = []
        self.game_records = {}

    def on_kv_post(self, base_widget):
        self.ids.user_bubble_widget.on_press_callback = self.open_avatar_picker

    def open_avatar_picker(self):
        try:
            avatars = [f.name for f in AVATARS_DIR.glob("*.png")]
        except Exception:
            avatars = []

        if not avatars or not self.username:
            return

        current_avatar = state.user_avatars.get(self.username)

        grid = GridLayout(
            cols=4,
            spacing=dp(12),
            padding=dp(12),
            size_hint_x=None,
            size_hint_y=None,
        )
        grid.bind(minimum_height=grid.setter("height"))
        grid.bind(minimum_width=grid.setter("width"))
        grid.bind(children=lambda inst, val: setattr(
            inst, "width", inst.minimum_width))

        def add_avatar_button(filename):
            avatar_path = AVATARS_DIR / filename
            is_current = filename == current_avatar
            btn = AvatarButton(str(avatar_path), is_current=is_current)
            btn.bind(on_release=lambda _inst,
                     name=filename: self._select_avatar(name))
            grid.add_widget(btn)

        for avatar in sorted(avatars):
            add_avatar_button(avatar)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)

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
                radius=[dp(12)], pos=popup.pos, size=popup.size)
            Color(*BASE_BG)
            popup.outer_bg = RoundedRectangle(
                radius=[dp(10)], pos=(popup.x + dp(2), popup.y + dp(2)), size=(popup.width - dp(4), popup.height - dp(4))
            )

        def update_popup_graphics(inst, _val):
            popup.outer_border.pos = inst.pos
            popup.outer_border.size = inst.size
            popup.outer_bg.pos = (inst.x + dp(2), inst.y + dp(2))
            popup.outer_bg.size = (inst.width - dp(4), inst.height - dp(4))

        popup.bind(pos=update_popup_graphics, size=update_popup_graphics)

        def set_popup_size(_dt=None):
            title_height = dp(40)
            total_height = grid.height + dp(24) + title_height
            total_width = grid.width + dp(24)
            popup.size = (
                min(total_width, self.width * 0.9),
                min(total_height, self.height * 0.9),
            )

        Clock.schedule_once(set_popup_size, 0)

        def close_on_select(_dt=None):
            popup.dismiss()

        self._avatar_popup_closer = close_on_select

        def open_popup(_dt):
            popup.open()
            popup.overlay_color = [0, 0, 0, 0]

        Clock.schedule_once(open_popup, 0.1)

    def _select_avatar(self, avatar_name):
        state.user_avatars[self.username] = avatar_name
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
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    message = message.strip()
                    if not message:
                        continue
                    parsed = parse_json_message(message)
                    if parsed:
                        Clock.schedule_once(
                            lambda dt, msg=parsed: self.route_json_message(msg))
        except Exception:
            self.on_disconnected()

    def route_json_message(self, msg_obj):
        try:
            msg_type = msg_obj.get("type", "")
            data = msg_obj.get("data", {})

            if msg_type == "USERLIST":
                names = data.get("users", [])
                Clock.schedule_once(
                    lambda dt, n=names: self.update_user_buttons(n), 0.1)
                return

            if msg_type == "AVATAR":
                username = data.get("username", "")
                avatar = data.get("avatar", "")
                if username and avatar:
                    state.user_avatars[username] = avatar
                    if username == self.username:
                        Clock.schedule_once(
                            lambda dt: self.update_current_user_avatar())
                    Clock.schedule_once(
                        lambda dt: self.update_user_buttons(self.online_users))
                    Clock.schedule_once(lambda dt: self.update_chat_cards())
                    try:
                        chat_screen = self.manager.get_screen("chat")
                        if self.manager.current == "chat":
                            if chat_screen.chat_id in ("general", username) or self.username == username:
                                Clock.schedule_once(
                                    lambda dt: chat_screen.refresh_messages())
                    except Exception:
                        pass
                return

            if msg_type == "AVATAR_ERROR":
                Clock.schedule_once(lambda dt: self.show_avatar_error_popup())
                return

            if msg_type == "CHAT":
                sender = data.get("sender", "")
                recipient = data.get("recipient", "general")
                text = data.get("text", "")
                is_self = sender == self.username
                chat_id = "general" if recipient == "general" else (
                    sender if not is_self else recipient)
                if chat_id not in self.chats:
                    self.chats[chat_id] = {"messages": [], "unread": 0}
                if is_self:
                    return
                self.chats[chat_id]["messages"].append(
                    {"username": sender, "text": text, "is_own": False, "kind": "chat"})
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == chat_id:
                        self.chats[chat_id]["unread"] = 0
                        chat_screen.add_message_bubble(
                            sender, text, is_own=False, kind="chat")
                        Clock.schedule_once(
                            lambda dt: chat_screen.scroll_to_bottom(), 0.05)
                    else:
                        self.chats[chat_id]["unread"] += 1
                except Exception:
                    self.chats[chat_id]["unread"] += 1
                self.update_chat_cards()
                return

            if msg_type == "SYSTEM":
                text = data.get("text", "")
                chat_id = data.get("chat_id", "general")
                if chat_id not in self.chats:
                    self.chats[chat_id] = {"messages": [], "unread": 0}
                self.chats[chat_id]["messages"].append(
                    {"username": "SYSTEM", "text": text, "is_own": False, "kind": "system"})
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
                return

            if msg_type == "GAME_INVITE":
                inviter = data.get("opponent", "")
                if not inviter:
                    return
                if inviter not in self.chats:
                    self.chats[inviter] = {"messages": [], "unread": 0}
                self.chats[inviter]["messages"].append(
                    {"username": inviter, "is_own": False, "kind": "game_invite"})
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == inviter:
                        chat_screen.add_game_invite_button(inviter, inviter)
                        chat_screen.has_pending_invite = True
                        Clock.schedule_once(
                            lambda dt: chat_screen.scroll_to_bottom(), 0.05)
                    else:
                        self.chats[inviter]["unread"] += 1
                except Exception:
                    self.chats[inviter]["unread"] += 1
                self.update_chat_cards()
                return

            if msg_type == "GAME_MOVE":
                board = data.get("board", [])
                current_player = data.get("current_player", "X")
                try:
                    game_screen = self.manager.get_screen("game")
                    if game_screen and hasattr(game_screen, "receive_opponent_move"):
                        game_screen.receive_opponent_move(
                            str(board), current_player)
                except Exception:
                    pass
                return

            if msg_type == "GAME_END":
                result = data.get("result", "DRAW")
                try:
                    game_screen = self.manager.get_screen("game")
                    if game_screen and hasattr(game_screen, "receive_opponent_game_end"):
                        game_screen.receive_opponent_game_end(
                            result, show_popup=True)
                except Exception:
                    pass
                return

            if msg_type == "GAME_RESET":
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
                return

            if msg_type == "GAME_ACCEPTED":
                player_name = data.get("player", "")
                symbol = data.get("symbol", "X")
                opponent = data.get("opponent", "")
                inviter_symbol = "O" if symbol == "X" else "X"
                try:
                    chat_screen = None
                    try:
                        chat_screen = self.manager.get_screen("chat")
                    except Exception:
                        pass

                    game_screen = self.manager.get_screen("game")
                    game_screen.setup_game(
                        player_name=self.username,
                        opponent_name=player_name,
                        chat_screen=chat_screen,
                        score_holder=chat_screen if chat_screen and chat_screen.chat_id == player_name else None,
                        initial_player="X",
                    )
                    game_screen.player_symbol = inviter_symbol
                    game_screen.opponent_symbol = symbol
                    if chat_screen and chat_screen.chat_id == player_name:
                        chat_screen.has_pending_invite = False
                        self.clear_invites_for_chat(player_name)
                    self.manager.current = "game"
                except Exception as exc:
                    print(f"Error handling GAME_ACCEPTED: {exc}")
                return

            if msg_type == "GAME_LEFT":
                player_name = data.get("player", "")
                try:
                    self.clear_invites_for_chat(player_name)
                    if self.manager.current == "game":
                        def show_left_popup(_dt):
                            content = BoxLayout(
                                orientation="vertical", spacing=15, padding=20)
                            content.add_widget(
                                Label(text=f"{player_name} left the game", font_size=18))
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
                                title="Game Ended",
                                content=content,
                                size_hint=(0.7, 0.3),
                                auto_dismiss=False,
                            )
                            popup.background = ""
                            popup.background_color = BASE_BG
                            popup.title_size = 20

                            def on_close(_instance):
                                popup.dismiss()
                                try:
                                    chat_screen_local = self.manager.get_screen(
                                        "chat")
                                    if chat_screen_local.chat_id == player_name or chat_screen_local.chat_id == self.username:
                                        self.manager.current = "chat"
                                    else:
                                        chat_screen_local.load_chat(
                                            player_name, self)
                                        self.manager.current = "chat"
                                except Exception:
                                    self.manager.current = "main"

                            btn.bind(on_press=on_close)
                            popup.open()

                        Clock.schedule_once(show_left_popup, 0.1)
                except Exception as exc:
                    print(f"Error handling GAME_LEFT: {exc}")
                return
        except Exception as exc:
            print(f"Error routing JSON message: {exc}")

    def update_user_buttons(self, names):
        previous_users = set(self.online_users)
        self.online_users = [n for n in names if n and n != self.username]
        current_users = set(self.online_users)
        disconnected_users = previous_users - current_users

        for user in disconnected_users:
            if user in self.chats:
                self.show_user_disconnected_popup(user)
                try:
                    chat_screen = self.manager.get_screen("chat")
                    if self.manager.current == "chat" and chat_screen.chat_id == user:
                        Clock.schedule_once(lambda dt: setattr(
                            self.manager, "current", "main"), 0.5)
                    elif self.manager.current == "game":
                        Clock.schedule_once(lambda dt: setattr(
                            self.manager, "current", "main"), 0.5)
                except Exception:
                    pass
                self.remove_chat(user)

        holder = self.ids.user_list
        holder.clear_widgets()

        avatar_file = state.user_avatars.get(self.username)
        avatar_source = None
        if avatar_file:
            avatar_path = AVATARS_DIR / avatar_file
            if avatar_path.exists():
                avatar_source = str(avatar_path)

        self.ids.user_bubble_widget.set_user(self.username, avatar_source)

        for name in self.online_users:
            user_btn = UserButton(
                name, callback=lambda inst, n=name: self.open_chat(n))
            holder.add_widget(user_btn)
        self.update_chat_cards()

    def update_chat_cards(self):
        container = self.ids.chats_container
        container.clear_widgets()
        general_card = self.create_chat_card("General Chat", "general")
        container.add_widget(general_card)
        private_chats = [
            user for user in self.online_users if user in self.chats]
        if private_chats:
            divider = self.create_divider()
            container.add_widget(divider)
        for user in private_chats:
            private_card = self.create_chat_card(f"{user}", user)
            container.add_widget(private_card)

    def create_chat_card(self, title, chat_id):
        unread = self.chats.get(chat_id, {}).get("unread", 0)
        return ChatCard(title, chat_id, parent_with_open_chat=self, unread=unread)

    def create_divider(self):
        divider_container = BoxLayout(
            size_hint_y=None, height=30, padding=(15, 8))
        divider_line = Widget(size_hint_y=None, height=1)
        with divider_line.canvas:
            Color(*OTHER_COLOR)
            divider_line.rect = RoundedRectangle(
                pos=divider_line.pos, size=divider_line.size, radius=[0])
        divider_line.bind(
            pos=lambda inst, val: setattr(inst.rect, "pos", inst.pos),
            size=lambda inst, val: setattr(inst.rect, "size", inst.size),
        )
        divider_container.add_widget(divider_line)
        return divider_container

    def open_chat(self, chat_id):
        if chat_id not in self.chats:
            self.chats[chat_id] = {"messages": [], "unread": 0}
        self.chats[chat_id]["unread"] = 0
        self.update_chat_cards()
        chat_screen = self.manager.get_screen("chat")
        chat_screen.load_chat(chat_id, self)
        self.manager.current = "chat"

    def on_disconnected(self):
        restart_discovery()
        if not self.user_initiated_disconnect:
            Clock.schedule_once(lambda dt: self.show_disconnect_popup())
        else:
            self.user_initiated_disconnect = False

    def show_disconnect_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text="Disconnected from server", font_size=18))
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
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
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

    def show_user_disconnected_popup(self, username):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(
            Label(text=f"{username} has disconnected", font_size=18))
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
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
            size=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
        )

        content.add_widget(btn)
        popup = Popup(
            title="User Disconnected",
            content=content,
            size_hint=(0.7, 0.3),
            auto_dismiss=False,
        )
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda _x: popup.dismiss())
        popup.open()
        Clock.schedule_once(lambda dt: btn.dispatch("on_press"), 0.2)

    def show_avatar_error_popup(self):
        content = BoxLayout(orientation="vertical", spacing=15, padding=20)
        content.add_widget(Label(text="Avatar change failed", font_size=18))
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
            Color(*ALERT_COLOR)
            btn.border_line = Line(rounded_rectangle=(
                btn.x, btn.y, btn.width, btn.height, 8), width=1.5)
        btn.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
            size=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle", (inst.x, inst.y, inst.width, inst.height, 8)),
        )

        content.add_widget(btn)
        popup = Popup(title="Avatar Error", content=content,
                      size_hint=(0.6, 0.3), auto_dismiss=False)
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 20
        btn.bind(on_release=lambda _x: popup.dismiss())
        popup.open()
        Clock.schedule_once(lambda dt: btn.dispatch("on_press"), 0.2)

    def remove_chat(self, chat_id):
        if chat_id in self.chats:
            del self.chats[chat_id]
        if chat_id in self.game_records:
            del self.game_records[chat_id]
        self.update_chat_cards()

    def return_to_login(self, popup):
        popup.dismiss()
        self.manager.current = "login"

    def update_current_user_avatar(self):
        if not self.username:
            return
        avatar_file = state.user_avatars.get(self.username)
        avatar_source = None
        if avatar_file:
            avatar_path = AVATARS_DIR / avatar_file
            if avatar_path.exists():
                avatar_source = str(avatar_path)
        self.ids.user_bubble_widget.set_user(self.username, avatar_source)
        try:
            chat_screen = self.manager.get_screen("chat")
            chat_screen.ids.user_bubble_widget.set_user(
                self.username, avatar_source)
        except Exception:
            pass
