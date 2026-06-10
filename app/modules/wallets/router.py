from fastapi import APIRouter, Depends
from app.common.response import success_response, BaseSuccessResponse
from app.common.security import get_current_user
from app.modules.wallets.schema import WalletResponse
from app.modules.wallets.service import WalletsService
from app.modules.users.schema import UserResponse

router = APIRouter(prefix="/users/me/wallet", tags=["Wallets"])
wallets_service = WalletsService()

@router.get("", response_model=BaseSuccessResponse[WalletResponse])
async def get_wallet_me(current_user: UserResponse = Depends(get_current_user)):
    wallet = await wallets_service.get_wallet_by_user(current_user.user_id)
    return success_response(data=wallet.model_dump())
