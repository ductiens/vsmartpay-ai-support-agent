"""Users service"""
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.users import repository
from app.modules.users.schema import UserCreateRequest
from app.common.exceptions import BadRequestException, NotFoundException
from app.common.utils import hash_password

async def create_user(db: AsyncIOMotorDatabase, request: UserCreateRequest) -> dict:
    """
    Handle user creation business logic:
    - Validate email uniqueness.
    - Hash password if provided.
    - Insert into the database.
    """
    # 1. Check for duplicate email
    existing_user = await repository.get_user_by_email(db, request.email)
    if existing_user:
        raise BadRequestException(
            message="Email already registered",
            error_code="EMAIL_ALREADY_EXISTS"
        )
    
    # 2. Prepare user document dictionary
    user_data = {
        "email": request.email,
        "full_name": request.full_name,
    }
    
    # 3. Hash password if it is provided
    if request.password:
        user_data["password_hash"] = hash_password(request.password)
    else:
        user_data["password_hash"] = None
        
    # 4. Save user document
    return await repository.create_user(db, user_data)


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    """
    Retrieve user by ID, raising an exception if not found.
    """
    user = await repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException(
            message=f"User with ID {user_id} not found"
        )
    return user


async def list_users(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    List users with pagination.
    """
    return await repository.list_users(db, skip=skip, limit=limit)
