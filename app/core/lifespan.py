import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import db_manager
from app.modules.rag.vector_store import VectorStoreService
from app.modules.users.repository import UsersRepository
from app.modules.wallets.repository import WalletsRepository
from app.modules.transactions.repository import TransactionsRepository

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to database
    try:
        await db_manager.connect()
        if db_manager.db is not None:
            logger.info("Database connected successfully during startup.")
            # Ensure Vector Search indexes exist on Atlas
            vector_store = VectorStoreService()
            await vector_store.ensure_search_indexes()
            # Ensure collection indexes
            await UsersRepository().ensure_indexes()
            await WalletsRepository().ensure_indexes()
            await TransactionsRepository().ensure_indexes()
        try:
            from app.modules.transactions.classifier.model import get_classifier
            get_classifier()
            logger.info("Transaction classifier model preloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to preload transaction classifier model: {e}")
    except Exception as e:
        logger.error(f"Startup database connection or index setup failed: {e}")
    yield
    # Shutdown: Close database connection
    await db_manager.close()
