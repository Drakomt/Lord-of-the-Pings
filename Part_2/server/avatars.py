import os
import random


def get_random_avatar():
    """Get a random avatar from the client assets folder."""
    avatars_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "client", "assets", "avatars")
    try:
        avatars = [f for f in os.listdir(avatars_dir) if f.endswith(".png")]
        return random.choice(avatars) if avatars else None
    except Exception:
        return None


def list_available_avatars():
    """List all available avatars."""
    avatars_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "client", "assets", "avatars")
    try:
        return [f for f in os.listdir(avatars_dir) if f.endswith(".png")]
    except Exception:
        return []
