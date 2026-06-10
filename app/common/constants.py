from enum import Enum

class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class WalletStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"

class Currency(str, Enum):
    VND = "VND"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class KYCStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class SessionStatus(str, Enum):
    BOT_ACTIVE = "BOT_ACTIVE"
    CLOSED = "CLOSED"
    WAITING_HUMAN = "WAITING_HUMAN"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
