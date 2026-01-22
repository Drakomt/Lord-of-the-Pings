KV = """
<LoginScreen>:
    name: "login"
    canvas.before:
        Color:
            rgba: 14/255., 16/255., 32/255., 1  # BASE_BG
        Rectangle:
            pos: self.pos
            size: self.size

    # Server info label in top left corner
    Label:
        id: server_info_lbl
        text: ""
        font_size: "12sp"
        color: 140/255., 154/255., 188/255., 0.8  # TEXT_HINT with transparency
        size_hint: None, None
        size: self.texture_size
        pos: dp(10), root.height - self.height - dp(10)
        halign: "left"

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
                    on_text_validate: root.login(username_input.text) if root.can_login else root.show_server_offline_popup()

            StyledButton:
                text: "ENTER"
                size_hint: (0.9, None)
                height: dp(60)
                pos_hint: {"center_x": 0.5}
                border_color: 78/255, 138/255, 255/255, 1
                background_color: 18/255, 20/255, 38/255, 1
                disabled: not root.can_login
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
