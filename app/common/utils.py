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
    from app.config import settings
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_LOG_ROUNDS)
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

import hashlib
import re

def hash_user_id(user_id: str | None) -> str:
    """Hash the user ID for anonymized tracing."""
    if not user_id:
        return "anonymous"
    return hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:16]

def mask_pii_in_message(message: str) -> str:
    """Mask potential PII (like card numbers, OTPs, emails) from user messages."""
    if not message:
        return message
        
    # Mask 16-digit card numbers (allowing spaces/dashes)
    card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    def mask_card(match):
        val = match.group(0).replace('-', '').replace(' ', '')
        if len(val) >= 16:
            return f"****-****-****-{val[-4:]}"
        return "****"
    
    masked = re.sub(card_pattern, mask_card, message)
    
    # Mask 4 to 6 digit OTP codes if explicitly mentioned near "otp"
    otp_pattern = r'(?i)(?:\botp\b.*?\b)(\d{4,6})\b'
    masked = re.sub(otp_pattern, r'OTP: ***', masked)
    
    # Mask email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    masked = re.sub(email_pattern, r'***@***.***', masked)

    return masked
