"""
Comprehensive tests for Finance module with JWT Authentication.
Tests User CRUD (Register, Login), Wallet CRUD, Transactions (DEPOSIT, WITHDRAWAL, TRANSFER),
Balance checks, Fee lookups, idempotency, security ownership (Forbidden/Unauthorized), and error handling.
"""
import pytest
from httpx import AsyncClient
from app.config import settings

API_PREFIX = settings.API_V1_STR  # /api/v1


# ──────────────────── Helper: Seed user + wallet into test DB ────────────────────

async def seed_user_and_wallet(
    client: AsyncClient, 
    user_id_suffix: str = "A", 
    balance: int = 0, 
    password: str = "password123"
):
    """
    Helper to create a user (wallet is auto-created), login to get JWT, and optionally deposit balance.
    Returns (user_data, wallet_data, auth_headers).
    """
    phone = f"09000000{ord(user_id_suffix) % 100:02d}"
    
    # 1. Register User (wallet is auto-created here)
    user_resp = await client.post(f"{API_PREFIX}/users", json={
        "full_name": f"Test User {user_id_suffix}",
        "phone": phone,
        "email": f"test_{user_id_suffix.lower()}@example.com",
        "password": password,
    })
    assert user_resp.status_code == 201
    user_data = user_resp.json()["data"]

    # 2. Login to get Access Token
    login_resp = await client.post(f"{API_PREFIX}/login", json={
        "phone": phone,
        "password": password,
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Get the auto-created wallet
    wallet_resp = await client.get(f"{API_PREFIX}/users/me/wallet", headers=headers)
    assert wallet_resp.status_code == 200
    wallet_data = wallet_resp.json()["data"]

    # 4. Deposit initial balance if specified
    if balance > 0:
        deposit_resp = await client.post(f"{API_PREFIX}/transactions", json={
            "amount": balance,
            "type": "DEPOSIT",
            "description": "Seed balance",
        }, headers=headers)
        assert deposit_resp.status_code == 201

    return user_data, wallet_data, headers


# ══════════════════════════════════════════════════════════════
# 1. USER CRUD & AUTHENTICATION
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_register_user_success(client):
    """POST /users → Đăng ký người dùng demo thành công."""
    response = await client.post(f"{API_PREFIX}/users", json={
        "full_name": "Nguyễn Văn Test",
        "phone": "0999888777",
        "email": "vantest@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["user_id"].startswith("usr_")
    assert data["full_name"] == "Nguyễn Văn Test"
    assert data["phone"] == "0999888777"
    assert "hashed_password" not in data  # Mật khẩu hash không được phép lộ ra ngoài
    assert data["kyc_status"] == "UNVERIFIED"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_register_user_duplicate_phone(client):
    """POST /users → 409 nếu trùng số điện thoại."""
    req_body = {
        "full_name": "Trùng Số ĐT",
        "phone": "0911222333",
        "password": "password123",
    }
    # Lần 1
    resp1 = await client.post(f"{API_PREFIX}/users", json=req_body)
    assert resp1.status_code == 201
    
    # Lần 2 → trùng
    resp2 = await client.post(f"{API_PREFIX}/users", json=req_body)
    assert resp2.status_code == 409
    assert resp2.json()["error_code"] == "PHONE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_success(client):
    """POST /login → Đăng nhập thành công trả về JWT Token."""
    # Register first
    await client.post(f"{API_PREFIX}/users", json={
        "full_name": "Đăng Nhập Thành Công",
        "phone": "0988777666",
        "password": "password123",
    })

    # Login
    response = await client.post(f"{API_PREFIX}/login", json={
        "phone": "0988777666",
        "password": "password123",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["phone"] == "0988777666"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """POST /login → 400 nếu sai mật khẩu hoặc tài khoản không tồn tại."""
    # Register first
    await client.post(f"{API_PREFIX}/users", json={
        "full_name": "Sai Mật Khẩu",
        "phone": "0977666555",
        "password": "correct_password",
    })

    # Login với mật khẩu sai
    resp1 = await client.post(f"{API_PREFIX}/login", json={
        "phone": "0977666555",
        "password": "wrong_password",
    })
    assert resp1.status_code == 400
    assert resp1.json()["error_code"] == "INVALID_CREDENTIALS"

    # Login với tài khoản không tồn tại
    resp2 = await client.post(f"{API_PREFIX}/login", json={
        "phone": "0900000999",
        "password": "some_password",
    })
    assert resp2.status_code == 400
    assert resp2.json()["error_code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_user_me_success(client):
    """GET /users/me → Lấy thông tin user hiện tại qua JWT."""
    user_data, _, headers = await seed_user_and_wallet(client, "U")

    response = await client.get(f"{API_PREFIX}/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_id"] == user_data["user_id"]
    assert data["full_name"] == user_data["full_name"]


@pytest.mark.asyncio
async def test_get_user_me_unauthorized(client):
    """GET /users/me → 401 Unauthorized nếu không gửi token hoặc token lỗi."""
    response = await client.get(f"{API_PREFIX}/users/me")
    assert response.status_code == 401
    
    # Token sai định dạng
    response_bad_token = await client.get(
        f"{API_PREFIX}/users/me", 
        headers={"Authorization": "Bearer bad_token_here"}
    )
    assert response_bad_token.status_code == 401


# ══════════════════════════════════════════════════════════════
# 2. WALLET CRUD
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_wallet_auto_created_on_register(client):
    """POST /users → Wallet auto-created upon registration."""
    phone = "0944333222"
    await client.post(f"{API_PREFIX}/users", json={
        "full_name": "Create Wallet User",
        "phone": phone,
        "password": "password123",
    })
    login_resp = await client.post(f"{API_PREFIX}/login", json={
        "phone": phone,
        "password": "password123",
    })
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify wallet was auto-created and can be fetched
    response = await client.get(f"{API_PREFIX}/users/me/wallet", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["wallet_id"].startswith("wlt_")
    assert data["balance"] == 0
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_wallet_me(client):
    """GET /users/me/wallet → Xem ví của chính mình."""
    _, wallet_data, headers = await seed_user_and_wallet(client, "G")

    response = await client.get(f"{API_PREFIX}/users/me/wallet", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["wallet_id"] == wallet_data["wallet_id"]


# ══════════════════════════════════════════════════════════════
# 3. BALANCE
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_balance_after_deposit(client):
    """GET /users/me/wallet → Phản ánh đúng số dư sau khi nạp tiền."""
    _, _, headers = await seed_user_and_wallet(client, "B", balance=1000000)

    response = await client.get(f"{API_PREFIX}/users/me/wallet", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["balance"] == 1000000
    assert data["currency"] == "VND"


# ══════════════════════════════════════════════════════════════
# 4. TRANSACTIONS - DEPOSIT
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_deposit_success(client):
    """POST /transactions DEPOSIT → Balance ví tăng."""
    _, _, headers = await seed_user_and_wallet(client, "D")

    # Deposit 500,000 VND
    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 500000,
        "type": "DEPOSIT",
        "description": "Nạp tiền ví điện tử",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["type"] == "DEPOSIT"
    assert data["status"] == "SUCCESS"
    assert data["amount"] == 500000
    assert data["fee"] == 0

    # Verify balance
    balance_resp = await client.get(f"{API_PREFIX}/users/me/wallet", headers=headers)
    assert balance_resp.json()["data"]["balance"] == 500000


# ══════════════════════════════════════════════════════════════
# 5. TRANSACTIONS - WITHDRAWAL
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_withdrawal_success(client):
    """POST /transactions WITHDRAWAL → Balance giảm bao gồm phí."""
    _, _, headers = await seed_user_and_wallet(client, "R", balance=1000000)

    # Withdraw 200,000 VND (phí cố định 1,100 VND)
    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 200000,
        "type": "WITHDRAWAL",
        "description": "Rút tiền về tài khoản ngân hàng",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "SUCCESS"
    assert data["fee"] == 1100

    # Verify balance: 1,000,000 - 200,000 - 1,100 = 798,900
    balance_resp = await client.get(f"{API_PREFIX}/users/me/wallet", headers=headers)
    assert balance_resp.json()["data"]["balance"] == 798900


@pytest.mark.asyncio
async def test_withdrawal_insufficient_balance(client):
    """POST /transactions WITHDRAWAL → 400 nếu số dư không đủ."""
    _, _, headers = await seed_user_and_wallet(client, "I", balance=5000)

    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "WITHDRAWAL",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["error_code"] == "INSUFFICIENT_BALANCE"


# ══════════════════════════════════════════════════════════════
# 6. TRANSACTIONS - TRANSFER (Trừ ví gửi + Cộng ví nhận)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_transfer_success(client):
    """
    POST /transactions TRANSFER
    → Trừ 200,000 từ ví gửi (S), cộng 200,000 vào ví nhận (T).
    """
    sender_user, _, sender_headers = await seed_user_and_wallet(client, "S", balance=1000000)
    recipient_user, _, recipient_headers = await seed_user_and_wallet(client, "T", balance=500000)

    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 200000,
        "type": "TRANSFER",
        "recipient_user_id": recipient_user["user_id"],
        "description": "Chuyển khoản thanh toán",
    }, headers=sender_headers)
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "SUCCESS"
    assert data["type"] == "TRANSFER"
    assert data["recipient_user_id"] == recipient_user["user_id"]
    assert data["fee"] == 0

    # Verify sender balance: 1,000,000 - 200,000 = 800,000
    sender_bal = await client.get(f"{API_PREFIX}/users/me/wallet", headers=sender_headers)
    assert sender_bal.json()["data"]["balance"] == 800000

    # Verify recipient balance: 500,000 + 200,000 = 700,000
    recipient_bal = await client.get(f"{API_PREFIX}/users/me/wallet", headers=recipient_headers)
    assert recipient_bal.json()["data"]["balance"] == 700000


@pytest.mark.asyncio
async def test_transfer_missing_recipient(client):
    """POST /transactions TRANSFER → 400 nếu thiếu recipient_user_id."""
    _, _, headers = await seed_user_and_wallet(client, "M", balance=1000000)

    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "TRANSFER",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["error_code"] == "MISSING_RECIPIENT"


@pytest.mark.asyncio
async def test_transfer_self_not_allowed(client):
    """POST /transactions TRANSFER → 400 nếu tự chuyển cho chính mình."""
    user_data, _, headers = await seed_user_and_wallet(client, "X", balance=1000000)

    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "TRANSFER",
        "recipient_user_id": user_data["user_id"],
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["error_code"] == "SELF_TRANSFER"


@pytest.mark.asyncio
async def test_transfer_insufficient_balance(client):
    """POST /transactions TRANSFER → 400 nếu số dư ví gửi không đủ."""
    sender_user, _, sender_headers = await seed_user_and_wallet(client, "P", balance=1000)
    recipient_user, _, _ = await seed_user_and_wallet(client, "Q", balance=500000)

    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "TRANSFER",
        "recipient_user_id": recipient_user["user_id"],
    }, headers=sender_headers)
    assert response.status_code == 400
    assert response.json()["error_code"] == "INSUFFICIENT_BALANCE"


@pytest.mark.asyncio
async def test_transfer_recipient_not_found(client):
    """POST /transactions TRANSFER → 404 nếu ví người nhận không tồn tại."""
    _, _, headers = await seed_user_and_wallet(client, "Y", balance=1000000)

    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "TRANSFER",
        "recipient_user_id": "usr_not_exist",
    }, headers=headers)
    assert response.status_code == 404
    assert response.json()["error_code"] == "RECIPIENT_WALLET_NOT_FOUND"


# ══════════════════════════════════════════════════════════════
# 7. IDEMPOTENCY
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_idempotency_duplicate_rejected(client):
    """POST /transactions với trùng idempotency_key → 409 Conflict."""
    _, _, headers = await seed_user_and_wallet(client, "K", balance=1000000)

    txn_body = {
        "amount": 50000,
        "type": "DEPOSIT",
        "idempotency_key": "idem_test_unique_999",
    }

    # Lần 1 → Thành công
    resp1 = await client.post(f"{API_PREFIX}/transactions", json=txn_body, headers=headers)
    assert resp1.status_code == 201

    # Lần 2 → Duplicate
    resp2 = await client.post(f"{API_PREFIX}/transactions", json=txn_body, headers=headers)
    assert resp2.status_code == 409
    assert resp2.json()["error_code"] == "DUPLICATE_TRANSACTION"


# ══════════════════════════════════════════════════════════════
# 8. INVALID AMOUNT & TYPE
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_invalid_amount_zero(client):
    """POST /transactions amount=0 → 422 Validation Error."""
    _, _, headers = await seed_user_and_wallet(client, "Z")
    
    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 0,
        "type": "DEPOSIT",
    }, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_transaction_type(client):
    """POST /transactions type không hợp lệ → 400."""
    _, _, headers = await seed_user_and_wallet(client, "V")
    
    response = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "INVALID_TYPE",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_TRANSACTION_TYPE"


# ══════════════════════════════════════════════════════════════
# 9. TRANSACTION DETAILS & SECURITY OWNERSHIP
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_transaction_success(client):
    """GET /transactions/{id} → Xem chi tiết giao dịch thành công (chủ sở hữu)."""
    _, _, headers = await seed_user_and_wallet(client, "H")

    # Tạo giao dịch
    txn_resp = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 300000,
        "type": "DEPOSIT",
    }, headers=headers)
    txn_id = txn_resp.json()["data"]["transaction_id"]

    # Xem giao dịch
    response = await client.get(f"{API_PREFIX}/transactions/{txn_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["transaction_id"] == txn_id
    assert data["amount"] == 300000


@pytest.mark.asyncio
async def test_get_transaction_forbidden_for_other_users(client):
    """GET /transactions/{id} → 403 Forbidden nếu user khác cố truy cập."""
    # User A tạo giao dịch
    _, _, headers_a = await seed_user_and_wallet(client, "A")
    txn_resp = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 150000,
        "type": "DEPOSIT",
    }, headers=headers_a)
    txn_id = txn_resp.json()["data"]["transaction_id"]

    # User B cố xem giao dịch của User A
    _, _, headers_b = await seed_user_and_wallet(client, "B")
    response = await client.get(f"{API_PREFIX}/transactions/{txn_id}", headers=headers_b)
    
    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_get_transaction_not_found(client):
    """GET /transactions/non_existent → 404."""
    _, _, headers = await seed_user_and_wallet(client, "N")
    
    response = await client.get(f"{API_PREFIX}/transactions/txn_ghost", headers=headers)
    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_transaction_history(client):
    """GET /users/me/transactions → Lịch sử giao dịch sắp xếp mới nhất trước."""
    _, _, headers = await seed_user_and_wallet(client, "L")

    # Tạo 3 giao dịch
    for i in range(3):
        await client.post(f"{API_PREFIX}/transactions", json={
            "amount": (i + 1) * 100000,
            "type": "DEPOSIT",
        }, headers=headers)

    response = await client.get(f"{API_PREFIX}/users/me/transactions", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert len(data["transactions"]) == 3
    # Mới nhất xếp trước: 300,000 -> 200,000 -> 100,000
    assert data["transactions"][0]["amount"] == 300000


# ══════════════════════════════════════════════════════════════
# 10. FEE LOOKUP (PUBLIC API)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_fee_transfer(client):
    """GET /fees?type=TRANSFER&amount=1000000 → Phí 0 (Public)."""
    response = await client.get(f"{API_PREFIX}/fees?type=TRANSFER&amount=1000000")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["transaction_type"] == "TRANSFER"
    assert data["fee"] == 0


@pytest.mark.asyncio
async def test_fee_withdrawal(client):
    """GET /fees?type=WITHDRAWAL&amount=500000 → Phí 1,100 (Public)."""
    response = await client.get(f"{API_PREFIX}/fees?type=WITHDRAWAL&amount=500000")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["transaction_type"] == "WITHDRAWAL"
    assert data["fee"] == 1100


@pytest.mark.asyncio
async def test_fee_deposit(client):
    """GET /fees?type=DEPOSIT&amount=200000 → Phí 0 (Public)."""
    response = await client.get(f"{API_PREFIX}/fees?type=DEPOSIT&amount=200000")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["fee"] == 0


@pytest.mark.asyncio
async def test_fee_invalid_type(client):
    """GET /fees?type=INVALID&amount=100000 → 400."""
    response = await client.get(f"{API_PREFIX}/fees?type=INVALID&amount=100000")
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_TRANSACTION_TYPE"
