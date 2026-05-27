"""Users repository"""
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.common.utils import generate_id, now_utc

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Ensure required database indexes are created on the users collection.
    """
    await db.users.create_index("email", unique=True)


async def create_user(db: AsyncIOMotorDatabase, user_data: dict) -> dict:
    """
    Create a new user document in MongoDB.
    """
    user_id = generate_id()
    current_time = now_utc()
    
    user_document = {
        "_id": user_id,
        "email": user_data["email"].strip().lower(),
        "password_hash": user_data.get("password_hash"),
        "full_name": user_data.get("full_name"),
        "created_at": current_time,
        "updated_at": current_time,
    }
    
    await db.users.insert_one(user_document)
    
    # Map _id to id for API schema compatibility
    user_document["id"] = user_document["_id"]
    return user_document


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[dict]:
    """
    Retrieve a user document by their unique ID.
    """
    user = await db.users.find_one({"_id": user_id})
    if user:
        user["id"] = user["_id"]
    return user


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[dict]:
    """
    Retrieve a user document by their email address (case-insensitive).
    """
    user = await db.users.find_one({"email": email.strip().lower()})
    if user:
        user["id"] = user["_id"]
    return user


async def list_users(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    List user documents with skip and limit pagination support.
    """
    users = []
    cursor = db.users.find().skip(skip).limit(limit)
    async for user in cursor:
        user["id"] = user["_id"]
        users.append(user)
    return users
