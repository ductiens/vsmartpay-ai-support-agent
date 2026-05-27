from datetime import datetime, timezone
from uuid6 import uuid7
import bcrypt


def generate_id() -> str:
    """
    Generate a unique ID using UUID v7 (time-ordered).
    This ensures lexicographical sortability and better database index performance.
    """
    return str(uuid7())


def now_utc() -> datetime:
    """
    Get the current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt algorithm.
    """
    # bcrypt password must be converted to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Decode to return a unicode string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed bcrypt password.
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

