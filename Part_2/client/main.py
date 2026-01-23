"""Client application entry point for Lord of the Pings chat application.

This module initializes the Kivy application, sets up the screen manager with
all available screens (login, main, chat, game), and starts server discovery.
"""

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
    """Initialize and run the Lord of the Pings chat application.

    Sets up the Kivy application with UI resources, configures all screens
    (login, main, chat, game), and starts background server discovery.
    """

    class ChatApp(App):
        def build(self):
            """Build the application UI and initialize screens."""
            self.title = "Lord of the Pings"
            icon_path = Path(__file__).parent / "assets" / \
                "icons" / "Lotp_Icon_BP.ico"
            self.icon = str(icon_path)

            # Register asset directories with Kivy resource loader
            client_root = Path(__file__).parent
            assets_root = client_root / "assets"
            resource_add_path(str(client_root))
            resource_add_path(str(assets_root))

            # Load KV layout from string
            Builder.load_string(KV)

            # Create screen manager and register all application screens
            sm = ScreenManager()
            sm.add_widget(LoginScreen(name="login"))
            sm.add_widget(MainScreen(name="main"))
            sm.add_widget(ChatScreen(name="chat"))
            sm.add_widget(GameScreen(name="game"))

            # Start background server discovery thread
            start_discovery()

            return sm

    ChatApp().run()


if __name__ == "__main__":
    main()
