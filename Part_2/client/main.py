import socket
import threading
import sys
from pathlib import Path

# Allow running as `python main.py` inside the client folder.
if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parent.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    __package__ = "client"

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivy.resources import resource_add_path

from client.core.discovery import start_discovery
from client.ui.kv_layout import KV
from client.screens.login_screen import LoginScreen
from client.screens.main_screen import MainScreen
from client.screens.chat_screen import ChatScreen
from client.game.tictactoe import GameScreen
from client.widgets.avatar_button import AvatarButton
from client.widgets.user_bubble import UserBubbleWidget


def main():
    """Main entry point for the chat application."""

    class ChatApp(App):
        def build(self):
            self.title = "Lord of the Pings"
            icon_path = Path(__file__).parent / "assets" / \
                "icons" / "Lotp_Icon_BP.ico"
            self.icon = str(icon_path)

            # Make assets available regardless of current working directory
            client_root = Path(__file__).parent
            assets_root = client_root / "assets"
            resource_add_path(str(client_root))
            resource_add_path(str(assets_root))

            # Load KV layout
            Builder.load_string(KV)

            # Create screen manager and add screens
            sm = ScreenManager()
            sm.add_widget(LoginScreen(name="login"))
            sm.add_widget(MainScreen(name="main"))
            sm.add_widget(ChatScreen(name="chat"))
            sm.add_widget(GameScreen(name="game"))

            # Start server discovery
            start_discovery()

            return sm

    ChatApp().run()


if __name__ == "__main__":
    main()
