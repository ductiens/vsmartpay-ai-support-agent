"""
Seed Finance Data Script.
Nạp dữ liệu demo (users, wallets, transactions) vào MongoDB.

Chạy: .\venv\Scripts\python scripts/seed_finance_data.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from app.config import settings
from motor.motor_asyncio import AsyncIOMotorClient


async def seed():
    """Nạp dữ liệu demo vào MongoDB."""
    print(f"Connecting to MongoDB: {settings.DATABASE_NAME}...")
    client = AsyncIOMotorClient(settings.MONGODB_URL, uuidRepresentation="standard")
    db = client[settings.DATABASE_NAME]

    base_time = datetime(2026, 5, 28, 8, 0, 0, tzinfo=timezone.utc)

    # ──────────────────── Users ────────────────────
    users = [
        {
            "user_id": "usr_001",
            "full_name": "Nguyễn Văn A",
            "phone": "0987654321",
            "email": "vana@example.com",
            "kyc_status": "VERIFIED",
            "created_at": base_time,
            "updated_at": base_time,
        },
        {
            "user_id": "usr_002",
            "full_name": "Trần Thị B",
            "phone": "0901234567",
            "email": "thib@example.com",
            "kyc_status": "UNVERIFIED",
            "created_at": base_time,
            "updated_at": base_time,
        },
        {
            "user_id": "usr_003",
            "full_name": "Lê Văn C",
            "phone": "0912345678",
            "email": "vanc@example.com",
            "kyc_status": "VERIFIED",
            "created_at": base_time,
            "updated_at": base_time,
        },
    ]

    # ──────────────────── Wallets ────────────────────
    wallets = [
        {
            "wallet_id": "wlt_001",
            "user_id": "usr_001",
            "balance": 2500000,
            "currency": "VND",
            "status": "ACTIVE",
            "created_at": base_time,
            "updated_at": base_time,
        },
        {
            "wallet_id": "wlt_002",
            "user_id": "usr_002",
            "balance": 350000,
            "currency": "VND",
            "status": "ACTIVE",
            "created_at": base_time,
            "updated_at": base_time,
        },
        {
            "wallet_id": "wlt_003",
            "user_id": "usr_003",
            "balance": 10000000,
            "currency": "VND",
            "status": "ACTIVE",
            "created_at": base_time,
            "updated_at": base_time,
        },
    ]

    # ──────────────────── Transactions ────────────────────
    transactions = [
        {
            "transaction_id": "txn_001",
            "user_id": "usr_001",
            "wallet_id": "wlt_001",
            "amount": 500000,
            "type": "DEPOSIT",
            "status": "SUCCESS",
            "fee": 0,
            "recipient_user_id": None,
            "recipient_wallet_id": None,
            "description": "Nạp tiền vào ví",
            "idempotency_key": "idem_seed_001",
            "created_at": base_time + timedelta(minutes=30),
            "updated_at": base_time + timedelta(minutes=30),
        },
        {
            "transaction_id": "txn_002",
            "user_id": "usr_001",
            "wallet_id": "wlt_001",
            "amount": 100000,
            "type": "TRANSFER",
            "status": "SUCCESS",
            "fee": 0,
            "recipient_user_id": "usr_002",
            "recipient_wallet_id": "wlt_002",
            "description": "Chuyển tiền cho Trần Thị B",
            "idempotency_key": "idem_seed_002",
            "created_at": base_time + timedelta(hours=1),
            "updated_at": base_time + timedelta(hours=1),
        },
        {
            "transaction_id": "txn_003",
            "user_id": "usr_001",
            "wallet_id": "wlt_001",
            "amount": 200000,
            "type": "WITHDRAWAL",
            "status": "SUCCESS",
            "fee": 1100,
            "recipient_user_id": None,
            "recipient_wallet_id": None,
            "description": "Rút tiền ATM",
            "idempotency_key": "idem_seed_003",
            "created_at": base_time + timedelta(hours=2),
            "updated_at": base_time + timedelta(hours=2),
        },
        {
            "transaction_id": "txn_004",
            "user_id": "usr_002",
            "wallet_id": "wlt_002",
            "amount": 50000,
            "type": "DEPOSIT",
            "status": "SUCCESS",
            "fee": 0,
            "recipient_user_id": None,
            "recipient_wallet_id": None,
            "description": "Nạp tiền qua ngân hàng",
            "idempotency_key": "idem_seed_004",
            "created_at": base_time + timedelta(hours=3),
            "updated_at": base_time + timedelta(hours=3),
        },
        {
            "transaction_id": "txn_005",
            "user_id": "usr_003",
            "wallet_id": "wlt_003",
            "amount": 1000000,
            "type": "TRANSFER",
            "status": "PENDING",
            "fee": 0,
            "recipient_user_id": "usr_001",
            "recipient_wallet_id": "wlt_001",
            "description": "Chuyển tiền cho Nguyễn Văn A",
            "idempotency_key": "idem_seed_005",
            "created_at": base_time + timedelta(hours=4),
            "updated_at": base_time + timedelta(hours=4),
        },
        {
            "transaction_id": "txn_006",
            "user_id": "usr_001",
            "wallet_id": "wlt_001",
            "amount": 300000,
            "type": "TRANSFER",
            "status": "FAILED",
            "fee": 0,
            "recipient_user_id": "usr_002",
            "recipient_wallet_id": "wlt_002",
            "description": "Chuyển tiền thất bại do lỗi hệ thống",
            "idempotency_key": "idem_seed_006",
            "created_at": base_time + timedelta(hours=5),
            "updated_at": base_time + timedelta(hours=5),
        },
    ]

    # ──────────────────── Drop & Insert ────────────────────
    print("Dropping existing finance collections...")
    await db["users"].drop()
    await db["wallets"].drop()
    await db["transactions"].drop()

    print(f"Inserting {len(users)} users...")
    await db["users"].insert_many(users)

    print(f"Inserting {len(wallets)} wallets...")
    await db["wallets"].insert_many(wallets)

    print(f"Inserting {len(transactions)} transactions...")
    await db["transactions"].insert_many(transactions)

    # ──────────────────── Create Indexes ────────────────────
    print("Creating indexes...")
    await db["users"].create_index("user_id", unique=True)
    await db["users"].create_index("phone")
    await db["wallets"].create_index("wallet_id", unique=True)
    await db["wallets"].create_index("user_id", unique=True)
    await db["transactions"].create_index("transaction_id", unique=True)
    await db["transactions"].create_index("user_id")
    await db["transactions"].create_index("idempotency_key", unique=True, sparse=True)
    await db["transactions"].create_index("created_at")

    # ──────────────────── Verify ────────────────────
    user_count = await db["users"].count_documents({})
    wallet_count = await db["wallets"].count_documents({})
    txn_count = await db["transactions"].count_documents({})
    print(f"\n✅ Seed complete! Users: {user_count}, Wallets: {wallet_count}, Transactions: {txn_count}")

    # Print summary
    print("\n📋 Users:")
    async for u in db["users"].find({}, {"_id": 0, "user_id": 1, "full_name": 1, "kyc_status": 1}):
        print(f"  - {u['user_id']}: {u['full_name']} (KYC: {u['kyc_status']})")

    print("\n💰 Wallets:")
    async for w in db["wallets"].find({}, {"_id": 0, "wallet_id": 1, "user_id": 1, "balance": 1}):
        print(f"  - {w['wallet_id']} ({w['user_id']}): {w['balance']:,} VND")

    print("\n📄 Transactions:")
    async for t in db["transactions"].find({}, {"_id": 0}).sort("created_at", 1):
        recipient = f" → {t.get('recipient_user_id')}" if t.get('recipient_user_id') else ""
        print(f"  - {t['transaction_id']}: {t['type']} {t['amount']:,} VND [{t['status']}]{recipient}")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
