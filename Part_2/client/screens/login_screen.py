"""Login screen for Lord of the Pings application.

Handles server discovery, connection, and user authentication. Performs
server connectivity checks and manages the initial connection flow.
"""

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
from kivy.uix.textinput import TextInput

from client.core import state
from client.config.constants import ALERT_COLOR, BASE_BG, DARK_BG2, OWN_COLOR, TEXT_PRIMARY
from client.core.discovery import stop_discovery, restart_discovery
from client.core.protocol import parse_json_message

# Global status socket - created when entering login screen, closed when leaving
_status_socket = None
_status_socket_connected = False
_status_check_thread = None
_stop_status_check = False


class LoginScreen(Screen):
    """Initial login screen handling discovery, connectivity, and authentication.

    Performs periodic server availability checks and manages user login flow
    including connection establishment and initial message buffering.
    """

    can_login = BooleanProperty(False)

    def on_enter(self):
        """Initialize login screen and start server connectivity checks."""
        global _stop_status_check, _status_check_thread

        Clock.schedule_interval(self.check_status, 0.5)

        # Start background thread only if not already running
        if _status_check_thread is None or not _status_check_thread.is_alive():
            _stop_status_check = False
            _status_check_thread = threading.Thread(
                target=self.maintain_status_socket, daemon=True)
            _status_check_thread.start()
        Clock.schedule_once(lambda dt: setattr(
            self.ids.username_input, "focus", True), 0.2)

    def on_leave(self):
        """Clean up scheduled tasks and stop status socket when leaving login screen."""
        Clock.unschedule(self.check_status)
        self.stop_status_socket()

    def _close_status_socket_only(self):
        """Close the status socket without stopping the monitoring thread.

        Used when switching servers to allow reconnection to new address.
        """
        global _status_socket, _status_socket_connected

        # Close socket
        if _status_socket:
            try:
                _status_socket.close()
            except Exception:
                pass
            _status_socket = None
        _status_socket_connected = False

    def stop_status_socket(self):
        """Stop the status monitoring socket and thread.

        Used when leaving login screen to completely shut down monitoring.
        """
        global _stop_status_check

        # Signal thread to stop
        _stop_status_check = True

        # Close socket
        self._close_status_socket_only()

    def maintain_status_socket(self):
        """Maintain a persistent status socket to monitor server connectivity.

        Creates ONE socket when server is available and keeps it alive.
        Only recreates if the socket breaks (server goes down).
        """
        import time
        global _status_socket, _status_socket_connected, _stop_status_check

        while not _stop_status_check:
            # Only try to create socket if we don't have one
            if not _status_socket_connected:
                if state.HOST and state.SERVER_PORT:
                    try:
                        sock = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2.0)
                        sock.connect((state.HOST, state.SERVER_PORT))

                        # Connection successful - mark as connected
                        _status_socket = sock
                        _status_socket_connected = True

                        # Set socket to non-blocking for monitoring
                        sock.setblocking(False)

                        # Now monitor this socket - it stays alive until server dies
                        while not _stop_status_check:
                            # Check if socket was closed externally (e.g., manual override)
                            if _status_socket is None:
                                break
                            
                            try:
                                # Try to peek at socket to see if it's still alive
                                data = sock.recv(1, socket.MSG_PEEK)
                                if not data:
                                    # Socket closed by server
                                    break
                            except BlockingIOError:
                                # No data available, socket still alive
                                pass
                            except Exception as e:
                                # Socket error, connection lost
                                break

                            time.sleep(0.5)

                        # Socket broke - close and mark as disconnected
                        self._close_status_socket_only()
                        # Restart discovery to find server again (unless manual override)
                        if not state.manual_override_mode:
                            restart_discovery()

                    except Exception as e:
                        # Connection failed (server not available)
                        self._close_status_socket_only()
                        # Wait longer before retry to reduce SYN packet spam
                        time.sleep(3)
                else:
                    # No server configured yet
                    time.sleep(0.5)
            else:
                # Socket is connected, just wait
                time.sleep(0.5)

    def check_status(self, _dt):
        """Check current socket status and update UI."""
        global _status_socket_connected
        Clock.schedule_once(
            lambda dt: self.update_label(_status_socket_connected))

    def update_label(self, online):
        """Update server status label based on connectivity."""
        if online:
            self.ids.server_status_lbl.text = "ONLINE"
            self.ids.server_status_lbl.color = OWN_COLOR
            self.can_login = True
            # Update server info label with IP and port
            if state.HOST and state.SERVER_PORT:
                self.ids.server_info_lbl.text = f"Server: {state.HOST}:{state.SERVER_PORT}"
        else:
            self.ids.server_status_lbl.text = "OFFLINE"
            self.ids.server_status_lbl.color = ALERT_COLOR
            self.can_login = False
            self.ids.server_info_lbl.text = ""

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

    def show_manual_override_popup(self):
        """Open manual server configuration popup."""
        content = BoxLayout(orientation="vertical",
                            spacing=10, padding=[15, 0, 15, 15])

        # IP input
        ip_label = Label(
            text="Server IP:",
            font_size=20,
            size_hint_y=None,
            height=25,
            color=TEXT_PRIMARY,
            halign="left"
        )
        ip_label.bind(width=lambda instance, value: setattr(
            instance, 'text_size', (value, None)))
        content.add_widget(ip_label)

        ip_input = TextInput(
            hint_text="e.g., 127.0.0.1",
            multiline=False,
            size_hint_y=None,
            height=55,
            font_size=20,
            foreground_color=TEXT_PRIMARY,
            background_color=DARK_BG2,
            padding=[15, 15]
        )

        # Pre-fill with current override if active
        if state.manual_override_mode and state.manual_override_ip:
            ip_input.text = state.manual_override_ip

        content.add_widget(ip_input)

        # Port input
        port_label = Label(
            text="Server Port:",
            font_size=20,
            size_hint_y=None,
            height=25,
            color=TEXT_PRIMARY,
            halign="left"
        )
        port_label.bind(width=lambda instance, value: setattr(
            instance, 'text_size', (value, None)))
        content.add_widget(port_label)

        port_input = TextInput(
            hint_text="e.g., 9000",
            multiline=False,
            size_hint_y=None,
            height=55,
            font_size=20,
            foreground_color=TEXT_PRIMARY,
            background_color=DARK_BG2,
            padding=[15, 15],
            input_filter="int"
        )

        # Pre-fill with current override if active
        if state.manual_override_mode and state.manual_override_port:
            port_input.text = str(state.manual_override_port)

        content.add_widget(port_input)

        # Error label
        error_label = Label(
            text="",
            font_size=20,
            size_hint_y=None,
            height=25,
            color=ALERT_COLOR
        )
        content.add_widget(error_label)

        # Buttons column (vertical for mobile responsiveness)
        # Reset(50) + Connect(50) + Cancel(50) + spacing(10*2) OR Connect(50) + Cancel(50) + spacing(10)
        btn_height = 170 if state.manual_override_mode else 120
        btn_box = BoxLayout(orientation="vertical", spacing=10,
                            size_hint_y=None, height=btn_height)

        # Reset button (only show if override is active)
        if state.manual_override_mode:
            reset_btn = Button(
                text="Reset",
                size_hint=(1, None),
                height=50,
                background_normal="",
                background_color=DARK_BG2,
                color=TEXT_PRIMARY,
                bold=True
            )

            with reset_btn.canvas.after:
                Color(*ALERT_COLOR)
                reset_btn.border_line = Line(
                    rounded_rectangle=(
                        reset_btn.x, reset_btn.y, reset_btn.width, reset_btn.height, 8),
                    width=1.5
                )
            reset_btn.bind(
                pos=lambda inst, val: setattr(
                    inst.border_line, "rounded_rectangle",
                    (inst.x, inst.y, inst.width, inst.height, 8)
                ),
                size=lambda inst, val: setattr(
                    inst.border_line, "rounded_rectangle",
                    (inst.x, inst.y, inst.width, inst.height, 8)
                ),
            )
            btn_box.add_widget(reset_btn)

        # Connect button
        connect_btn = Button(
            text="Connect",
            size_hint=(1, None),
            height=50,
            background_normal="",
            background_color=DARK_BG2,
            color=TEXT_PRIMARY,
            bold=True
        )

        with connect_btn.canvas.after:
            Color(*OWN_COLOR)
            connect_btn.border_line = Line(
                rounded_rectangle=(connect_btn.x, connect_btn.y,
                                   connect_btn.width, connect_btn.height, 8),
                width=1.5
            )
        connect_btn.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle",
                (inst.x, inst.y, inst.width, inst.height, 8)
            ),
            size=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle",
                (inst.x, inst.y, inst.width, inst.height, 8)
            ),
        )
        btn_box.add_widget(connect_btn)

        # Cancel button
        cancel_btn = Button(
            text="Cancel",
            size_hint=(1, None),
            height=50,
            background_normal="",
            background_color=DARK_BG2,
            color=TEXT_PRIMARY,
            bold=True
        )

        with cancel_btn.canvas.after:
            Color(*OWN_COLOR)
            cancel_btn.border_line = Line(
                rounded_rectangle=(cancel_btn.x, cancel_btn.y,
                                   cancel_btn.width, cancel_btn.height, 8),
                width=1.5
            )
        cancel_btn.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle",
                (inst.x, inst.y, inst.width, inst.height, 8)
            ),
            size=lambda inst, val: setattr(
                inst.border_line, "rounded_rectangle",
                (inst.x, inst.y, inst.width, inst.height, 8)
            ),
        )
        btn_box.add_widget(cancel_btn)

        content.add_widget(btn_box)

        from kivy.metrics import dp

        popup = Popup(
            title="Server Manual Override",
            content=content,
            size_hint=(None, None),
            size=(dp(300), dp(280)),
            auto_dismiss=False,
            title_align='center',
            separator_color=OWN_COLOR

        )
        popup.background = ""
        popup.background_color = BASE_BG
        popup.title_size = 24

        # Add border to popup itself
        with popup.canvas.after:
            Color(*OWN_COLOR)
            popup.border_line = Line(rectangle=(
                popup.x, popup.y, popup.width, popup.height), width=2)

        popup.bind(
            pos=lambda inst, val: setattr(
                inst.border_line, 'rectangle', (inst.x, inst.y, inst.width, inst.height)),
            size=lambda inst, val: setattr(
                inst.border_line, 'rectangle', (inst.x, inst.y, inst.width, inst.height))
        )

        # Button handlers
        cancel_btn.bind(on_release=lambda _: popup.dismiss())

        if state.manual_override_mode:
            reset_btn.bind(
                on_release=lambda _: self.reset_manual_override(popup))

        connect_btn.bind(on_release=lambda _: self.apply_manual_override(
            ip_input.text.strip(),
            port_input.text.strip(),
            error_label,
            popup
        ))

        popup.open()

    def reset_manual_override(self, popup):
        """Clear manual override and restart discovery."""
        # Close old status socket so it can reconnect to discovered server
        self._close_status_socket_only()

        state.manual_override_mode = False
        state.manual_override_ip = None
        state.manual_override_port = None
        state.HOST = None
        state.SERVER_PORT = None
        state.DISCOVERED = False

        # Restart discovery
        restart_discovery()

        popup.dismiss()

        # Update UI
        self.ids.server_status_lbl.text = "Checking status..."
        self.ids.server_info_lbl.text = ""
        self.can_login = False

    def apply_manual_override(self, ip, port, error_label, popup):
        """Validate and apply manual server override."""
        # Validate IP
        if not ip:
            error_label.text = "Please enter a server IP"
            return

        # Basic IP validation (could be hostname too)
        if not self.validate_ip_or_hostname(ip):
            error_label.text = "Invalid IP address or hostname"
            return

        # Validate port
        if not port:
            error_label.text = "Please enter a server port"
            return

        try:
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                error_label.text = "Port must be between 1-65535"
                return
        except ValueError:
            error_label.text = "Invalid port number"
            return

        # Test connection
        error_label.text = "Testing connection..."
        threading.Thread(
            target=self.test_manual_connection,
            args=(ip, port_num, error_label, popup),
            daemon=True
        ).start()

    def validate_ip_or_hostname(self, host):
        """Basic validation for IP address or hostname."""
        if not host:
            return False

        # Allow hostnames and IP addresses
        # Simple check: must contain only valid characters
        import re
        # Allow alphanumeric, dots, dashes for hostnames and IPs
        pattern = r'^[a-zA-Z0-9\.\-]+$'
        return re.match(pattern, host) is not None

    def test_manual_connection(self, ip, port, error_label, popup):
        """Test connection to manual server configuration."""
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(2)
            test_sock.connect((ip, port))
            test_sock.close()

            # Connection successful - apply override
            Clock.schedule_once(
                lambda dt: self.finalize_manual_override(ip, port, popup))

        except socket.timeout:
            Clock.schedule_once(lambda dt: setattr(
                error_label, "text", "Connection timeout"
            ))
        except socket.gaierror:
            Clock.schedule_once(lambda dt: setattr(
                error_label, "text", "Cannot resolve hostname"
            ))
        except ConnectionRefusedError:
            Clock.schedule_once(lambda dt: setattr(
                error_label, "text", "Connection refused"
            ))
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(
                error_label, "text", f"Connection failed: {str(e)[:30]}"
            ))

    def finalize_manual_override(self, ip, port, popup):
        """Finalize manual override after successful connection test."""
        # Close old status socket so it reconnects to new manual override address
        self._close_status_socket_only()

        # Set manual override state
        state.manual_override_mode = True
        state.manual_override_ip = ip
        state.manual_override_port = port
        state.HOST = ip
        state.SERVER_PORT = port
        state.DISCOVERED = True

        # Stop discovery
        stop_discovery()

        # Close popup
        popup.dismiss()

        # Update UI
        self.update_label(True)
        self.can_login = True

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
        """Establish connection to server and authenticate user.

        Validates username input, connects to server, sends login,
        and handles username conflicts. Initializes main screen on success.

        Args:
            username: Username to login with
        """
        if not username.strip():
            self.ids.error_label.text = "Please enter a username"
            return

        self.ids.error_label.text = ""

        # Check if status socket is connected (server is online)
        global _status_socket_connected
        if not _status_socket_connected:
            self.show_server_offline_popup()
            return

        app = App.get_running_app()
        prebuffer = b""
        try:
            # Connect to server and send username
            app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            app.sock.connect((state.HOST, state.SERVER_PORT))
            app.sock.sendall(username.encode())
            app.sock.settimeout(0.4)

            # Receive initial messages (user list, avatars)
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
        except Exception as exc:
            self.show_server_offline_popup()
            print("Connection error:", exc)
            return

        # Check for username conflict
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

        # Initialize main screen with connection and user data
        main = self.manager.get_screen("main")
        main.reset_chat_data()
        main.username = username
        main.sock = app.sock

        # Parse initial messages from server
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
        # Start background thread to listen for incoming messages
        threading.Thread(target=main.listen_to_server, daemon=True).start()
        self.manager.current = "main"
