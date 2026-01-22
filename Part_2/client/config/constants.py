"""Color theme constants for Lord of the Pings UI.

Defines all color values used throughout the application for consistent theming.
Uses RGBA format normalized to 0-1 range.
"""

# Primary theme colors
BASE_BG = (14/255, 16/255, 32/255, 1)  # Deep dark blue background
DARK_BG = (26/255, 31/255, 58/255, 1)  # Darker blue for elements
DARK_BG2 = (18/255, 20/255, 38/255, 1)  # Even darker blue for buttons

# User message colors
OWN_COLOR = (78/255, 138/255, 255/255, 1)  # Blue for own messages
OTHER_COLOR = (132/255, 99/255, 255/255, 1)  # Purple for others' messages

# Text and UI colors
TEXT_PRIMARY = (242/255, 245/255, 255/255, 1)  # Main text (light)
TEXT_HINT = (140/255, 154/255, 188/255, 1)  # Hint text (muted)
SYSTEM_COLOR = (44/255, 52/255, 86/255, 1)  # System messages
INPUT_BG = (18/255, 20/255, 38/255, 1)  # Input field background

# Alert and status colors
ALERT_COLOR = (255/255, 88/255, 160/255, 1)  # Alert/error (pink)
