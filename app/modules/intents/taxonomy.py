from enum import Enum

class IntentTaxonomy(str, Enum):
    # FAQs
    FAQ_GENERAL = "FAQ_GENERAL"
    FAQ_FEES = "FAQ_FEES"
    FAQ_LIMITS = "FAQ_LIMITS"
    FAQ_TERMS = "FAQ_TERMS"
    FAQ_TROUBLESHOOTING = "FAQ_TROUBLESHOOTING"
    
    # Financial Tools / Operations
    WALLET_BALANCE = "WALLET_BALANCE"
    TRANSACTION_HISTORY = "TRANSACTION_HISTORY"
    SYSTEM_FEES = "SYSTEM_FEES"
    
    # Escalation
    ESC_HUMAN = "ESC_HUMAN"
    
    # Other
    UNKNOWN = "UNKNOWN"
