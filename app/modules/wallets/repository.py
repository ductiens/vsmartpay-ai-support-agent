"""Wallets repository"""
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.common.utils import generate_id, now_utc
from app.common.constants import WalletStatus

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Ensure required database indexes are created on the wallets collection.
    """
    await db.wallets.create_index("user_id")


async def create_wallet(db: AsyncIOMotorDatabase, wallet_data: dict) -> dict:
    """
    Create a new wallet document in MongoDB.
    """
    wallet_id = generate_id()
    current_time = now_utc()
    
    wallet_document = {
        "_id": wallet_id,
        "user_id": wallet_data["user_id"],
        "currency": wallet_data["currency"],
        "balance": wallet_data.get("balance", 0),
        "status": wallet_data.get("status", WalletStatus.ACTIVE.value),
        "created_at": current_time,
        "updated_at": current_time,
    }
    
    await db.wallets.insert_one(wallet_document)
    
    # Map _id to id for API schema compatibility
    wallet_document["id"] = wallet_document["_id"]
    return wallet_document


async def get_wallet_by_id(db: AsyncIOMotorDatabase, wallet_id: str) -> Optional[dict]:
    """
    Retrieve a wallet document by its unique ID.
    """
    wallet = await db.wallets.find_one({"_id": wallet_id})
    if wallet:
        wallet["id"] = wallet["_id"]
    return wallet


async def get_wallets_by_user_id(db: AsyncIOMotorDatabase, user_id: str) -> List[dict]:
    """
    Retrieve all wallet documents for a specific user ID.
    """
    wallets = []
    cursor = db.wallets.find({"user_id": user_id})
    async for wallet in cursor:
        wallet["id"] = wallet["_id"]
        wallets.append(wallet)
    return wallets


async def update_wallet_balance(db: AsyncIOMotorDatabase, wallet_id: str, new_balance: int) -> bool:
    """
    Atomically update the balance and updated_at timestamp of a wallet.
    """
    current_time = now_utc()
    result = await db.wallets.update_one(
        {"_id": wallet_id},
        {"$set": {"balance": new_balance, "updated_at": current_time}}
    )
    return result.modified_count > 0
