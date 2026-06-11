from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings
from app.modules.users.repository import UsersRepository
from app.modules.users.schema import UserResponse
from app.common.exceptions import UnauthorizedException, ForbiddenException

# Define HTTPBearer schema for JWT Authentication
security_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT Access Token.
    The payload contains the user_id in the 'sub' key.
    """
    to_encode = data.copy()
    
    # Calculate expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    
    # Encode JWT token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> UserResponse:
    """
    FastAPI dependency to authenticate requests.
    Decodes the JWT token and fetches the current user from MongoDB.
    Raises 401 Unauthorized if invalid or expired.
    """
    credentials_exception = UnauthorizedException(
        message="Could not validate credentials",
        details={"headers": {"WWW-Authenticate": "Bearer"}}
    )
    
    if credentials is None:
        raise credentials_exception
        
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Query user from database
    user = await UsersRepository().get_user_by_id(user_id)
    if user is None:
        raise UnauthorizedException(
            message="User not found",
            details={"headers": {"WWW-Authenticate": "Bearer"}}
        )
        
    return UserResponse(**user)


async def get_current_admin(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    FastAPI dependency to authorize requests.
    Ensures that the current user has the 'admin' role.
    """
    if getattr(current_user, "role", "user") != "admin":
        raise ForbiddenException(
            message="Bạn không có quyền truy cập chức năng này. Chỉ dành cho Admin."
        )
    return current_user
