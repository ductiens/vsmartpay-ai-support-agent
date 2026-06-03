import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import db_manager
from app.common.exceptions import AppException
from app.common.response import error_response
from fastapi.exceptions import RequestValidationError

from app.modules.chat.router import router as chat_router
from app.modules.tools.router import router as tools_router
from app.modules.documents.router import router as documents_router
from app.modules.finance.router import router as finance_router
from app.modules.rag.vector_store import VectorStoreService
from app.modules.finance.repository import FinanceRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
            await vector_store.ensure_vector_search_index()
            # Ensure Finance collection indexes
            await FinanceRepository.ensure_indexes()
    except Exception as e:
        logger.error(f"Startup database connection or index setup failed: {e}")
    yield
    # Shutdown: Close database connection
    await db_manager.close()
 
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include Routers
app.include_router(chat_router)
app.include_router(tools_router)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(finance_router, prefix=settings.API_V1_STR)

# Global Exception Handlers for Unified API Responses
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return error_response(
        message=exc.message,
        error_code=exc.error_code,
        status_code=exc.status_code,
        details=exc.details
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return error_response(
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        status_code=422,
        details=exc.errors()
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    if settings.DEBUG:
        return error_response(
            message=str(exc),
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
    return error_response(
        message="An unexpected error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        status_code=500
    )

# Health endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "VSmartPay AI Support Agent"
    }
