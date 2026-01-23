"""Tic-Tac-Toe game implementation for Lord of the Pings.

Contains game logic (TicTacToeGame class) and the game UI screen (GameScreen).
Handles game state, move validation, win conditions, and networked gameplay.
"""

import random

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget

from client.config.constants import BASE_BG, DARK_BG2, OTHER_COLOR, OWN_COLOR, TEXT_PRIMARY
from client.core.protocol import send_json_message
from client.widgets.styled_button import StyledButton


class TicTacToeGame:
    """Core Tic-Tac-Toe game logic.

    Manages board state, move validation, current player tracking, and win detection.
    Board is represented as a list of 9 cells (3x3 grid), indexed 0-8.
    """

    def __init__(self):
        """Initialize game with empty board and default state."""
        self.board = [None] * 9
        self.current_player = "X"
        self.game_over = False
        self.winner = None
        self.move_count = 0

    def is_valid_move(self, cell):
        """Check if a move is valid for the given cell."""
        return 0 <= cell < 9 and self.board[cell] is None

    def make_move(self, cell, player):
        """Make a move on the board.

        Args:
            cell: Cell index (0-8) to place move
            player: Player symbol ("X" or "O")

        Returns:
            True if move was successful, False otherwise
        """
        if not self.is_valid_move(cell):
            return False
        self.board[cell] = player
        self.move_count += 1
        return True

    def get_winner(self):
        """Determine game state.

        Returns:
            "X" if X wins, "O" if O wins, "DRAW" if board full, None if ongoing
        """
        winning_combos = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            [0, 4, 8],
            [2, 4, 6],
        ]

        for combo in winning_combos:
            a, b, c = combo
            if self.board[a] is not None and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]

        if None not in self.board:
            return "DRAW"

        return None

    def reset(self):
        """Reset the game to initial state."""
        self.board = [None] * 9
        self.current_player = "X"
        self.game_over = False
        self.winner = None
        self.move_count = 0


class GameScreen(Screen):
    """Tic-Tac-Toe game display and controller.

    Manages the game UI, player interaction, move handling, and communication
    with opponent. Synchronizes game state with chat partner over network.
    """

    cell_size = NumericProperty(dp(80))
    grid_size = NumericProperty(dp(258))

    def __init__(self, **kwargs):
        """Initialize game screen with default state."""
        super().__init__(**kwargs)
        self.game = TicTacToeGame()
        self.player_name = ""
        self.opponent_name = ""
        self.player_symbol = "X"
        self.opponent_symbol = "O"
        self.player_score = 0
        self.opponent_score = 0
        self.chat_screen = None
        self.main_screen = None
        self.score_holder = None
        self.cell_buttons = []
        self.next_game_my_symbol = "X"
        self.next_game_opponent_symbol = "O"

    def on_enter(self):
        """Called when screen is displayed."""
        self.setup_board()

    def setup_game(self, player_name, opponent_name, chat_screen, score_holder=None, initial_player="X", randomize_start=False):
        """Configure game with player information.

        Args:
            player_name: Name of the local player
            opponent_name: Name of the opponent
            chat_screen: Reference to chat screen for communication
            score_holder: Object to track win/loss statistics
            initial_player: Symbol of starting player ("X" or "O")
            randomize_start: If True, randomly choose starting player
        """
        self.player_name = player_name
        self.opponent_name = opponent_name
        self.chat_screen = chat_screen
        self.score_holder = score_holder
        if chat_screen:
            self.main_screen = chat_screen.main_screen

        if randomize_start:
            initial_player = random.choice(["X", "O"])

        self.player_symbol = initial_player
        self.opponent_symbol = "O" if initial_player == "X" else "X"

        if self.score_holder:
            self.player_score = self.score_holder.wins
            self.opponent_score = self.score_holder.losses

        self.game.reset()

        self.ids.new_game_btn.opacity = 0
        self.ids.new_game_btn.disabled = True

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
        """Create the game board with buttons."""
        board_widget = self.ids.game_board
        board_widget.clear_widgets()
        self.cell_buttons = []

        for i in range(9):
            btn = StyledButton(text="", size_hint=(
                None, None), size=(self.cell_size, self.cell_size))
            btn.cell_index = i
            btn.display_mode = "icon"
            btn.image_source = ""
            btn.bind(on_press=self.on_cell_press)
            board_widget.add_widget(btn)
            self.cell_buttons.append(btn)

        self.update_status()
        self.update_score()

    def on_cell_press(self, button):
        """Handle cell press."""
        if self.game.game_over:
            return

        cell = button.cell_index

        if self.game.current_player != self.player_symbol:
            return

        if self.game.make_move(cell, self.player_symbol):
            self.update_board()

            result = self.game.get_winner()
            if result:
                self.game.game_over = True
                self.send_game_move(cell)
                self.handle_game_end(result)
                return

            self.game.current_player = self.opponent_symbol
            self.update_status()
            self.send_game_move(cell)

    def send_game_move(self, cell):
        """Send move to opponent through chat."""
        if not self.chat_screen:
            return

        try:
            send_json_message(
                self.chat_screen.main_screen.sock,
                "GAME_MOVE",
                {
                    "board": self.game.board,
                    "current_player": self.game.current_player,
                    "opponent": self.opponent_name,
                },
            )
        except Exception:
            pass

    def handle_game_end(self, result):
        """Handle game end."""
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

        self.ids.new_game_btn.opacity = 1
        self.ids.new_game_btn.disabled = False

        if self.chat_screen:
            try:
                send_json_message(
                    self.chat_screen.main_screen.sock,
                    "GAME_END",
                    {"result": result, "opponent": self.opponent_name},
                )
            except Exception:
                pass

        self.show_game_end_popup(status_msg)

    def update_board(self):
        """Update board display using X/O images."""
        for i, btn in enumerate(self.cell_buttons):
            cell_value = self.game.board[i]
            if cell_value == "X":
                btn.text = ""
                btn.display_mode = "icon"
                btn.image_source = "assets/icons/X.png"
                btn.background_color = OWN_COLOR if cell_value == self.player_symbol else OTHER_COLOR
                btn.border_color = OWN_COLOR if cell_value == self.player_symbol else OTHER_COLOR
            elif cell_value == "O":
                btn.text = ""
                btn.display_mode = "icon"
                btn.image_source = "assets/icons/O.png"
                btn.background_color = OWN_COLOR if cell_value == self.player_symbol else OTHER_COLOR
                btn.border_color = OWN_COLOR if cell_value == self.player_symbol else OTHER_COLOR
            else:
                btn.text = ""
                btn.image_source = ""

    def update_status(self):
        """Update game status label."""
        if not self.game.game_over:
            if self.game.current_player == self.player_symbol:
                self.ids.game_status_label.text = "Your Turn"
                self.ids.game_status_label.color = OWN_COLOR
            else:
                self.ids.game_status_label.text = f"{self.opponent_name}'s Turn"
                self.ids.game_status_label.color = OTHER_COLOR

    def update_score(self):
        """Update score display."""
        self.ids.score_label.text = f"You: {self.player_score} | {self.opponent_name}: {self.opponent_score}"

    def record_result(self, status_msg):
        """Persist win/loss stats."""
        if self.score_holder:
            self.score_holder.wins = self.player_score
            self.score_holder.losses = self.opponent_score
            self.score_holder.update_invite_stats()

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
        """Start a new game."""
        self.game.reset()

        my_symbol = random.choice(["X", "O"])
        self.player_symbol = my_symbol
        self.opponent_symbol = "O" if my_symbol == "X" else "X"

        self.setup_board()

        self.ids.new_game_btn.opacity = 0
        self.ids.new_game_btn.disabled = True

        self.send_game_reset(my_symbol)

    def send_game_reset(self, my_symbol):
        """Send game reset message to opponent."""
        if not self.chat_screen:
            return

        try:
            send_json_message(
                self.chat_screen.main_screen.sock,
                "GAME_RESET",
                {
                    "player": self.player_name,
                    "symbol": my_symbol,
                    "opponent": self.opponent_name,
                },
            )
        except Exception:
            pass

    def receive_opponent_reset(self):
        """Receive and process opponent's game reset."""
        if self.game.game_over:
            self.chat_screen.add_system_message(
                f"{self.opponent_name} started a new game!")

        self.game.reset()

        if hasattr(self, "next_game_my_symbol"):
            self.player_symbol = self.next_game_my_symbol
            self.opponent_symbol = self.next_game_opponent_symbol
        else:
            self.player_symbol = "X"
            self.opponent_symbol = "O"

        self.setup_board()

        self.ids.new_game_btn.opacity = 0
        self.ids.new_game_btn.disabled = True

    def show_game_end_popup(self, result):
        """Show popup with game result."""
        from kivy.uix.popup import Popup

        if result == "WON":
            status_text = "You Won!"
            popup_msg = f"Congratulations! You defeated {self.opponent_name}!"
            border_color = (34 / 255, 177 / 255, 76 / 255, 1)
        elif result == "LOST":
            status_text = "You Lost"
            popup_msg = f"{self.opponent_name} defeated you!"
            border_color = (231 / 255, 76 / 255, 60 / 255, 1)
        else:
            status_text = "It's a Draw!"
            popup_msg = "Great match! It's a draw!"
            border_color = (52 / 255, 152 / 255, 219 / 255, 1)

        content = BoxLayout(orientation="vertical", spacing=0, padding=0, size_hint=(
            None, None), size=(dp(320), dp(320)))

        with content.canvas.before:
            Color(14 / 255, 16 / 255, 32 / 255, 1)
            content.bg = RoundedRectangle(
                radius=[dp(15)], pos=content.pos, size=content.size)
            Color(*border_color)
            content.border = Line(
                rounded_rectangle=(content.x, content.y,
                                   content.width, content.height, dp(15)),
                width=dp(3),
            )

        def update_popup_graphics(inst, _val):
            content.bg.pos = inst.pos
            content.bg.size = inst.size
            content.border.rounded_rectangle = (
                inst.x, inst.y, inst.width, inst.height, dp(15))

        content.bind(pos=update_popup_graphics, size=update_popup_graphics)

        status_label = Label(
            text=status_text,
            color=border_color,
            font_size="28sp",
            bold=True,
            size_hint_y=0.35,
            halign="center",
            valign="middle",
        )
        status_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", inst.size))
        content.add_widget(status_label)

        separator = Widget(size_hint_y=0.05)
        with separator.canvas:
            Color(*border_color)
            separator.line = Line(points=[0, 0, dp(320), 0], width=dp(2))

        def update_separator(inst, _val):
            separator.line.points = [
                inst.x, inst.center_y, inst.x + inst.width, inst.center_y]

        separator.bind(pos=update_separator, size=update_separator)
        content.add_widget(separator)

        message_label = Label(
            text=popup_msg,
            color=TEXT_PRIMARY,
            font_size="16sp",
            size_hint_y=0.35,
            halign="center",
            valign="middle",
            padding=(dp(15), dp(10)),
        )
        message_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", (inst.width - dp(30), inst.height)))
        content.add_widget(message_label)

        close_btn = StyledButton(
            text="OK", size_hint_y=0.25, border_color=border_color, background_color=DARK_BG2)
        content.add_widget(close_btn)

        popup = Popup(
            content=content,
            size_hint=(None, None),
            size=(dp(320), dp(320)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            background="",
            background_color=(0, 0, 0, 0),
        )

        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def receive_opponent_game_end(self, winner_symbol, show_popup=True):
        """Receive opponent's game end result."""
        try:
            self.game.game_over = True

            if winner_symbol == "DRAW":
                self.ids.game_status_label.text = "It's a Tie!"
                status_msg = "DRAW"
            elif winner_symbol == self.opponent_symbol:
                self.opponent_score += 1
                self.ids.game_status_label.text = "You Lost!"
                status_msg = "LOST"
            elif winner_symbol == self.player_symbol:
                self.player_score += 1
                self.ids.game_status_label.text = "You Won!"
                status_msg = "WON"
            else:
                self.ids.game_status_label.text = "It's a Tie!"
                status_msg = "DRAW"

            self.update_score()
            self.record_result(status_msg)

            self.ids.new_game_btn.opacity = 1
            self.ids.new_game_btn.disabled = False

            if show_popup:
                self.show_game_end_popup(status_msg)
        except Exception as e:
            pass

    def exit_game(self):
        """Exit the game and go back to chat."""
        if self.chat_screen:
            try:
                send_json_message(
                    self.chat_screen.main_screen.sock,
                    "GAME_LEFT",
                    {"player": self.player_name, "opponent": self.opponent_name},
                )
            except Exception:
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
        """Receive and process opponent's move."""
        if self.game.game_over:
            return

        try:
            board_str = board_str.replace("None", "None")
            board_list = eval(board_str)

            self.game.board = board_list
            self.game.move_count = sum(
                1 for cell in board_list if cell is not None)
            self.game.current_player = current_player

            self.update_board()
            self.update_status()
        except Exception:
            pass
