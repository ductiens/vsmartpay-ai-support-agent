import json
import os
from typing import Optional, Dict, Any

class MockWalletClient:
    def __init__(self):
        self.mock_dir = "data/mock"
        
    def _read_json(self, filename: str) -> list:
        filepath = os.path.join(self.mock_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        wallets = self._read_json("wallets.json")
        for w in wallets:
            if w.get("user_id") == user_id:
                return w
        # Fallback default mock data if files do not exist or user not found
        return {"user_id": user_id, "balance": 1500000, "currency": "VND", "status": "ACTIVE"}

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        transactions = self._read_json("transactions.json")
        for t in transactions:
            if t.get("transaction_id") == transaction_id:
                return t
        # Fallback default mock data
        return {
            "transaction_id": transaction_id,
            "user_id": "usr_test_default",
            "amount": 50000,
            "type": "TRANSFER",
            "status": "SUCCESS",
            "timestamp": "2026-05-28T09:00:00Z",
            "currency": "VND"
        }


# Standalone functions for direct call and mock_wallet tools integration
_client = MockWalletClient()

def check_balance(user_id: str) -> Optional[Dict[str, Any]]:
    """
    check_balance(user_id) - Reads wallets.json and returns wallet info.
    """
    return _client.get_wallet_by_user_id(user_id)

def get_fee(transaction_type: str, amount: int) -> Dict[str, Any]:
    """
    get_fee(transaction_type, amount) - Returns fee info based on transaction type and amount.
    """
    fee = 0
    tx_type_upper = transaction_type.upper()
    if tx_type_upper == "WITHDRAWAL":
        fee = 1100
    elif tx_type_upper == "TRANSFER":
        fee = 0
    elif tx_type_upper == "DEPOSIT":
        fee = 0
    return {
        "transaction_type": transaction_type,
        "amount": amount,
        "fee": fee,
        "currency": "VND"
    }

def get_transaction_status(transaction_id: str) -> Optional[Dict[str, Any]]:
    """
    get_transaction_status(transaction_id) - Reads transactions.json and returns transaction status details.
    """
    transactions = _client._read_json("transactions.json")
    for t in transactions:
        if t.get("transaction_id") == transaction_id:
            return t
    return None

def get_user_kyc_status(user_id: str) -> str:
    """
    get_user_kyc_status(user_id) - Reads users.json and returns the user KYC status.
    """
    users = _client._read_json("users.json")
    for u in users:
        if u.get("user_id") == user_id:
            return u.get("kyc_status", "UNVERIFIED")
    return "UNVERIFIED"

async def create_support_ticket(user_id: str, issue_type: str, message: str) -> Dict[str, Any]:
    """
    create_support_ticket(user_id, issue_type, message) - Creates support ticket and saves it to MongoDB escalation_tickets.
    """
    from app.common.utils import generate_id, now_utc
    from app.database import get_db
    
    ticket_id = f"tkt_{generate_id()}"
    utc_now = now_utc()
    ticket = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "issue_type": issue_type,
        "message": message,
        "status": "OPEN",
        "created_at": utc_now,
    }
    
    db = get_db()
    if db is not None:
        # Create a copy to prevent inserting _id field into the returned dict
        await db["escalation_tickets"].insert_one(ticket.copy())
    
    # Format UTC time to string for JSON serialization
    ticket_resp = ticket.copy()
    ticket_resp["created_at"] = utc_now.isoformat()
    return ticket_resp
