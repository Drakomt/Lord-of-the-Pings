from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from client.constants import INPUT_BG, OTHER_COLOR, TEXT_HINT, TEXT_PRIMARY


class UserBubbleWidget(BoxLayout):
    """Styled bubble showing the current user and avatar."""

    def __init__(self, username="", avatar_source=None, **kwargs):
        if "size_hint" not in kwargs:
            kwargs["size_hint"] = (None, 1)
        if "height" not in kwargs:
            kwargs["height"] = dp(50)

        super().__init__(orientation="horizontal", spacing=dp(12), **kwargs)
        self.size_hint_x = None
        self.bind(minimum_width=lambda inst, val: setattr(inst, "width", val))
        self.username = username
        self.avatar_widget = None
        self.name_label = None
        self.bubble_bg = None
        self.on_press_callback = None

        self._build_widget(username, avatar_source)

    def _build_widget(self, username, avatar_source):
        self.clear_widgets()
        self.username = username

        bubble_container = BoxLayout(
            orientation="horizontal",
            padding=[dp(10), dp(6), dp(10), dp(6)],
            spacing=dp(10),
            size_hint=(None, None),
            height=dp(50),
        )

        with bubble_container.canvas.before:
            Color(rgba=INPUT_BG)
            self.bubble_bg = RoundedRectangle(
                radius=[dp(10)], pos=bubble_container.pos, size=bubble_container.size
            )
            Color(rgba=OTHER_COLOR)
            self.bubble_border = Line(
                rounded_rectangle=(
                    bubble_container.x,
                    bubble_container.y,
                    bubble_container.width,
                    bubble_container.height,
                    dp(10),
                ),
                width=1.5,
            )

        def update_bubble_graphics(inst, _val):
            self.bubble_bg.pos = inst.pos
            self.bubble_bg.size = inst.size
            self.bubble_border.rounded_rectangle = (
                inst.x,
                inst.y,
                inst.width,
                inst.height,
                dp(10),
            )

        bubble_container.bind(pos=update_bubble_graphics,
                              size=update_bubble_graphics)

        if avatar_source:
            self.avatar_widget = Image(
                source=avatar_source,
                size_hint=(None, None),
                size=(dp(36), dp(36)),
            )
            bubble_container.add_widget(self.avatar_widget)
        else:
            self.avatar_widget = None

        text_layout = BoxLayout(
            orientation="vertical",
            padding=[0, dp(2)],
            spacing=dp(1),
            size_hint=(None, None),
            width=dp(90),
            height=dp(38),
        )

        header_label = Label(
            text="User:",
            color=TEXT_HINT,
            font_size="12sp",
            size_hint=(None, None),
            height=dp(12),
            halign="left",
            valign="bottom",
        )
        header_label.bind(texture_size=lambda inst,
                          val: setattr(inst, "width", val[0]))
        header_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", (inst.width, None)))

        self.name_label = Label(
            text=username,
            color=TEXT_PRIMARY,
            font_size="18sp",
            bold=True,
            size_hint=(None, None),
            height=dp(20),
            halign="left",
            valign="top",
        )
        self.name_label.bind(texture_size=lambda inst,
                             val: setattr(inst, "width", val[0]))
        self.name_label.bind(size=lambda inst, val: setattr(
            inst, "text_size", (inst.width, None)))

        text_layout.add_widget(header_label)
        text_layout.add_widget(self.name_label)
        bubble_container.add_widget(text_layout)

        def update_width(*_args):
            avatar_width = (dp(36) + dp(10)) if avatar_source else 0
            header_width = header_label.texture_size[0] if header_label.texture_size[0] > 0 else dp(
                40)
            name_width = self.name_label.texture_size[0] if self.name_label.texture_size[0] > 0 else dp(
                60)
            text_width = max(header_width, name_width)
            bubble_container.width = dp(
                10) + avatar_width + text_width + dp(10)
            text_layout.width = text_width

        header_label.bind(texture_size=update_width)
        self.name_label.bind(texture_size=update_width)
        update_width()

        self.add_widget(bubble_container)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if callable(self.on_press_callback):
                self.on_press_callback()
            return True
        return super().on_touch_down(touch)

    def set_user(self, username, avatar_source=None):
        """Update the bubble with new user info."""
        self._build_widget(username, avatar_source)
