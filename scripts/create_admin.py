"""
Script to create the Admin/CSKH user account in MongoDB.
Run using: .\venv\Scripts\python scripts/create_admin.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.common.utils import hash_password, now_utc
from motor.motor_asyncio import AsyncIOMotorClient


async def create_admin():
    print(f"Connecting to MongoDB database '{settings.DATABASE_NAME}'...")
    client = AsyncIOMotorClient(settings.MONGODB_URL, uuidRepresentation="standard")
    db = client[settings.DATABASE_NAME]

    phone = "0909090909"
    email = "admin_cskh@vsmartpay.vn"
    full_name = "Admin CSKH"
    password = "adminpassword123"
    role = "admin"
    user_id = "usr_admin_cskh"
    wallet_id = "wlt_admin_cskh"
    utc_now = now_utc()

    # Hash the password using the application helper
    hashed_pw = hash_password(password)

    user_doc = {
        "user_id": user_id,
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "role": role,
        "hashed_password": hashed_pw,
        "kyc_status": "VERIFIED",
        "created_at": utc_now,
        "updated_at": utc_now,
    }

    wallet_doc = {
        "wallet_id": wallet_id,
        "user_id": user_id,
        "balance": 10000000,  # 10,000,000 VND
        "currency": "VND",
        "status": "ACTIVE",
        "created_at": utc_now,
        "updated_at": utc_now,
    }

    # Clean up any existing admin user with the same phone/user_id
    await db["users"].delete_many({"$or": [{"phone": phone}, {"user_id": user_id}]})
    await db["wallets"].delete_many({"$or": [{"wallet_id": wallet_id}, {"user_id": user_id}]})

    # Insert new admin user and wallet
    await db["users"].insert_one(user_doc)
    await db["wallets"].insert_one(wallet_doc)

    print("\n[SUCCESS] Admin/CSKH account created successfully!")
    print(f"  - User ID: {user_id}")
    print(f"  - Full Name: {full_name}")
    print(f"  - Phone Number: {phone}")
    print(f"  - Password: {password}")
    print(f"  - Role: {role}")
    print(f"  - Wallet ID: {wallet_id}")
    print(f"  - Wallet Balance: 10,000,000 VND")

    client.close()


if __name__ == "__main__":
    asyncio.run(create_admin())
