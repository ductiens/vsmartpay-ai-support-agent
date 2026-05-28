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
        return {"user_id": user_id, "balance": 1500000, "currency": "VND"}

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
