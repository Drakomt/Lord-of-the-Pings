import random
from pathlib import Path

# Point to the client's avatar assets from the server side.
AVATARS_DIR = Path(__file__).resolve(
).parents[2] / "client" / "assets" / "avatars"


def get_random_avatar():
    """Get a random avatar from the client assets folder."""
    try:
        avatars = [p.name for p in AVATARS_DIR.glob("*.png")]
        return random.choice(avatars) if avatars else None
    except Exception:
        return None


def list_available_avatars():
    """List all available avatars."""
    try:
        return [p.name for p in AVATARS_DIR.glob("*.png")]
    except Exception:
        return []
