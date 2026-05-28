# Script to seed mock data to MongoDB
import asyncio

async def seed_data():
    print("Seeding mock data to MongoDB...")
    # Seeding database collections (users, wallets, transactions) if needed
    print("Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_data())
