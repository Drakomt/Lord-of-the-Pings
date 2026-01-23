"""Asset path definitions for the Lord of the Pings client.

Provides centralized access to asset directories for avatars, icons,
and other resources relative to the package root.
"""

from pathlib import Path

# Base directories relative to this package
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
AVATARS_DIR = ASSETS_DIR / "avatars"
ICONS_DIR = ASSETS_DIR / "icons"
