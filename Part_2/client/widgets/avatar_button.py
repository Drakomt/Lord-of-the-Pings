"""Avatar selection button widget for picker UI.

Displays an avatar image in a selectable button format with visual indication
of the currently selected avatar.
"""

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image

from client.config.constants import OTHER_COLOR, OWN_COLOR


class AvatarButton(ButtonBehavior, FloatLayout):
    """Avatar button used in the picker popup.

    Displays an avatar image with a colored border indicating
    whether it's currently selected.
    """

    def __init__(self, avatar_path, is_current=False, **kwargs):
        """Initialize avatar button.

        Args:
            avatar_path: Path to the avatar image file
            is_current: True if this is the currently selected avatar
        """
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = dp(50)
        self.height = dp(50)

        self.img = Image(
            source=avatar_path,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        self.add_widget(self.img)

        # Use different color for current vs available avatars
        highlight_color = OWN_COLOR if is_current else OTHER_COLOR
        with self.canvas.after:
            Color(*highlight_color)
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, dp(12)),
                width=2,
            )

        self.bind(pos=self._update_border, size=self._update_border)

    def _update_border(self, *args):
        """Update border position and size when widget changes."""
        self.border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            dp(12),
        )
