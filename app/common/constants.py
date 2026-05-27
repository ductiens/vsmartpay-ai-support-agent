from enum import Enum

class TransactionType(str, Enum):
    """Supported transaction types in the system."""
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, Enum):
    """Possible statuses of a transaction."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class WalletStatus(str, Enum):
    """Possible statuses of a user's wallet."""
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    INACTIVE = "INACTIVE"


class LedgerEntryType(str, Enum):
    """Types of entries in the financial ledger (double-entry bookkeeping)."""
    DEBIT = "DEBIT"    # Decreases balance (asset reduction or liability increase)
    CREDIT = "CREDIT"  # Increases balance (asset increase or liability reduction)


class Currency(str, Enum):
    """Supported currencies in the system."""
    VND = "VND"
    USD = "USD"
