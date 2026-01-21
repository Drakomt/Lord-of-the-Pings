from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import StringProperty
import kivy.properties
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from client.constants import DARK_BG2, OTHER_COLOR, TEXT_PRIMARY


class StyledButton(ButtonBehavior, FloatLayout):
    """Custom button widget with rounded corners and optional icon."""

    text = StringProperty("")
    image_source = StringProperty("")
    display_mode = StringProperty("text")  # "text", "icon", or "icon_text"
    text_orientation = StringProperty("vertical")  # "vertical" or "horizontal"
    border_color = kivy.properties.ListProperty(OTHER_COLOR)
    background_color = kivy.properties.ListProperty(DARK_BG2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_widget = None

        with self.canvas.before:
            self.bg_color = Color(*self.background_color)
            self.bg = RoundedRectangle(
                radius=[dp(8)], pos=self.pos, size=self.size)
            self.border_color_obj = Color(*self.border_color)
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, dp(8)),
                width=1.5,
            )

        self.bind(pos=self._update_graphics, size=self._update_graphics)
        self.bind(
            text=self._update_content,
            image_source=self._update_content,
            display_mode=self._update_content,
            text_orientation=self._update_content,
        )
        self.bind(
            background_color=self._update_bg_color,
            border_color=self._update_border_color,
        )

        self._update_content()

    def _update_content(self, *args):
        if self.content_widget:
            self.remove_widget(self.content_widget)
            self.content_widget = None

        if self.display_mode == "text" and self.text:
            self.content_widget = Label(
                text=self.text,
                color=TEXT_PRIMARY,
                bold=True,
                font_size="12sp",
                size_hint=(1, 1),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                halign="center",
                valign="middle",
            )
            self.content_widget.bind(
                size=lambda inst, val: setattr(inst, "text_size", inst.size)
            )
            self.add_widget(self.content_widget)
        elif self.display_mode == "icon" and self.image_source:
            self.content_widget = Image(
                source=self.image_source,
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
            self.add_widget(self.content_widget)
        elif self.display_mode == "icon_text":
            is_vertical = self.text_orientation == "vertical"
            container = BoxLayout(
                orientation="vertical" if is_vertical else "horizontal",
                size_hint=(None, None),
                spacing=dp(4),
                padding=(dp(4), dp(4)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
            container.size = self.size
            self.bind(size=lambda inst, val: setattr(container, "size", val))

            if self.image_source:
                img = Image(
                    source=self.image_source,
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                    size_hint=(None, None),
                    size=(dp(26), dp(26)),
                )
                container.add_widget(img)

            if self.text:
                lbl = Label(
                    text=self.text,
                    color=TEXT_PRIMARY,
                    font_size="14sp",
                    halign="left" if not is_vertical else "center",
                    valign="middle",
                    size_hint=(1, 1),
                    text_size=(None, None),
                )

                if not is_vertical:
                    def update_label_width(*_args):
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
            if self.text:
                self.content_widget = Label(
                    text=self.text,
                    color=TEXT_PRIMARY,
                    bold=True,
                    font_size="16sp",
                    size_hint=(1, 1),
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                    halign="center",
                    valign="middle",
                )
                self.content_widget.bind(
                    size=lambda inst, val: setattr(
                        inst, "text_size", inst.size)
                )
                self.add_widget(self.content_widget)
            elif self.image_source:
                self.content_widget = Image(
                    source=self.image_source,
                    size_hint=(None, None),
                    size=(dp(24), dp(24)),
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                )
                self.add_widget(self.content_widget)

    def _update_graphics(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            dp(8),
        )

    def _update_bg_color(self, *args):
        self.bg_color.rgba = self.background_color

    def _update_border_color(self, *args):
        self.border_color_obj.rgba = self.border_color
