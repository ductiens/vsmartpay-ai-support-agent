from fastapi import FastAPI
from app.config import settings

from app.modules.chat.router import router as chat_router
from app.modules.tools.router import router as tools_router
from app.modules.documents.router import router as documents_router
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.wallets.router import router as wallets_router
from app.modules.transactions.router import router as transactions_router
from app.modules.fees.router import router as fees_router

def setup_routers(app: FastAPI):
    app.include_router(chat_router)
    app.include_router(tools_router)
    app.include_router(documents_router, prefix=settings.API_V1_STR)
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(users_router, prefix=settings.API_V1_STR)
    app.include_router(wallets_router, prefix=settings.API_V1_STR)
    app.include_router(transactions_router, prefix=settings.API_V1_STR)
    app.include_router(fees_router, prefix=settings.API_V1_STR)
