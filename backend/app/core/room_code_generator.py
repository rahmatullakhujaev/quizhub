import random
import string


def generate_room_code(length: int = 6) -> str:
    """Generate a random alphanumeric room code like 'A3X9K2'."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))