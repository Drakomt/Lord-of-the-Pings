"""Avatar management for Lord of the Pings server.

Provides utilities to load and select random avatars from the client assets
directory for new users joining the chat.
"""

import random
from pathlib import Path

# Point to the client's avatar assets from the server side.
AVATARS_DIR = Path(__file__).resolve(
).parents[2] / "client" / "assets" / "avatars"


def get_random_avatar():
    """Get a random avatar filename from available avatars.

    Returns:
        Random avatar filename (e.g., "avatar_1.png"), or None if none found
    """
    try:
        avatars = [p.name for p in AVATARS_DIR.glob("*.png")]
        return random.choice(avatars) if avatars else None
    except Exception:
        return None


def list_available_avatars():
    """List all available avatar filenames.

    Returns:
        List of avatar filenames, empty list if directory not found
    """
    try:
        return [p.name for p in AVATARS_DIR.glob("*.png")]
    except Exception:
        return []
