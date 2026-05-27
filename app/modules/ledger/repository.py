"""Ledger repository"""
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.common.utils import generate_id, now_utc

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Ensure required indexes are created for lookup-heavy fields in ledger_entries.
    """
    await db.ledger_entries.create_index("wallet_id")
    await db.ledger_entries.create_index("transaction_id")


async def create_ledger_entry(db: AsyncIOMotorDatabase, entry_data: dict) -> dict:
    """
    Create a new ledger entry document in MongoDB.
    """
    entry_id = generate_id()
    current_time = now_utc()
    
    entry_document = {
        "_id": entry_id,
        "transaction_id": entry_data["transaction_id"],
        "wallet_id": entry_data["wallet_id"],
        "entry_type": entry_data["entry_type"],
        "amount": entry_data["amount"],
        "currency": entry_data["currency"],
        "description": entry_data.get("description"),
        "created_at": current_time,
    }
    
    await db.ledger_entries.insert_one(entry_document)
    
    # Map _id to id for API schema compatibility
    entry_document["id"] = entry_document["_id"]
    return entry_document


async def get_entries_by_transaction_id(db: AsyncIOMotorDatabase, transaction_id: str) -> List[dict]:
    """
    Retrieve all ledger entries associated with a specific transaction ID.
    """
    entries = []
    cursor = db.ledger_entries.find({"transaction_id": transaction_id})
    async for entry in cursor:
        entry["id"] = entry["_id"]
        entries.append(entry)
    return entries


async def get_entries_by_wallet_id(db: AsyncIOMotorDatabase, wallet_id: str) -> List[dict]:
    """
    Retrieve all ledger entries associated with a specific wallet ID.
    """
    entries = []
    cursor = db.ledger_entries.find({"wallet_id": wallet_id})
    async for entry in cursor:
        entry["id"] = entry["_id"]
        entries.append(entry)
    return entries
