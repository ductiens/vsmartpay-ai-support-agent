# AGENTS.md

Project-level instructions for AI coding agents working on `mini-wallet-python`.

Read this file before changing code. Treat it as the project rulebook for architecture, validation, testing, and communication.

## Project overview

`mini-wallet-python` is a learning-oriented Fintech mini-wallet backend built with Python, FastAPI, MongoDB, Motor, and Pydantic v2.

The intended direction is a simple wallet / digital banking backend with:

- user management and authentication
- wallets and balances
- deposits, withdrawals, and peer-to-peer transfers
- double-entry ledger records
- risk / fraud scoring, with future Kaggle PaySim dataset integration

Current code is still early-stage. Do not assume every module described in the README is fully implemented. Check the actual files before wiring routes or business flows.

## Current repository facts

Important existing files:

- `app/main.py` creates the FastAPI app, configures CORS, connects MongoDB in lifespan, and exposes `/` and `/health`.
- `app/config.py` loads settings from `.env` using `pydantic-settings`.
- `app/database.py` owns the async MongoDB `AsyncIOMotorClient` connection manager.
- `app/common/constants.py` defines enums for transaction type/status, wallet status, ledger entry type, and currency.
- `app/common/exceptions.py` defines application exceptions used by global handlers.
- `app/common/response.py` defines unified success/error JSON responses.
- `app/common/utils.py` defines UUID v7 generation, UTC timestamps, and bcrypt password helpers.
- `tests/test_common.py` validates common constants, exceptions, responses, IDs, timestamps, and password hashing.
- `scripts/` currently contains placeholder utilities for dataset download, CSV inspection, PaySim import, demo seed, and DB reset.
- `app/modules/risk/` currently contains placeholder files only.

## Setup commands

Use Python 3.10+.

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Run the app locally:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

- API root: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Test and validation commands

Before finishing any code change, run:

```bash
pytest
```

For changes touching FastAPI startup, MongoDB config, or environment loading, also run the app and manually check `/health` and `/docs`.

Do not rely on Docker as the default validation path yet. `docker-compose.yml` references a `Dockerfile`, but this repository may not have one. Check first before using Docker commands.

## Architecture rules

Follow this modular direction:

```text
app/
  main.py
  config.py
  database.py
  common/
  modules/
    users/
    wallets/
    transactions/
    ledger/
    risk/
scripts/
tests/
```

Recommended module layout when implementing new features:

```text
app/modules/<module_name>/
  router.py       # FastAPI routes only
  schema.py       # Pydantic request/response schemas
  service.py      # business logic
  repository.py   # MongoDB access, if needed
  model.py        # DB document/domain model helpers, if needed
```

Keep route handlers thin. Put business logic in services. Put database queries in repository/helper functions when the logic grows.

Use async code in request paths. Prefer Motor for MongoDB operations. Do not introduce synchronous database calls inside FastAPI async endpoints.

## API response and error rules

Use the existing response helpers:

- `success_response(...)` for successful responses
- `AppException` subclasses for expected application errors

Keep the API response format consistent across modules.

Successful responses should look like:

```json
{
  "success": true,
  "message": "Success",
  "data": {}
}
```

Error responses should look like:

```json
{
  "success": false,
  "error_code": "ERROR_CODE",
  "message": "User-friendly message",
  "details": {}
}
```

## Fintech / wallet business rules

Money-moving code must be conservative and auditable.

When implementing wallet operations:

- Never use `float` for money. Use integer minor units, for example VND as integer amount, or `Decimal` with explicit conversion.
- Validate `amount > 0` for deposit, withdrawal, and transfer operations.
- Use idempotency for payment-like APIs. A repeated request must not create duplicate money movement.
- Keep transaction status explicit: `PENDING`, `SUCCESS`, `FAILED`.
- Do not directly change wallet balance without also creating the matching transaction/ledger records.
- For transfers, design for atomicity. Either all related updates succeed or the operation is marked failed/rolled back.
- For double-entry ledger behavior, total debits must equal total credits for each finalized transaction.
- Ledger records should be append-only. Prefer reversal entries over deleting or mutating historical ledger rows.
- Keep timestamps timezone-aware UTC using `now_utc()`.
- Use UUID v7 via `generate_id()` for new application IDs unless there is a strong reason not to.

## MongoDB rules

- Use collections intentionally; document expected collection names when adding them.
- Create indexes for lookup-heavy fields such as `user_id`, `wallet_id`, `transaction_id`, `idempotency_key`, and timestamps.
- Avoid storing sensitive credentials or plaintext auth data in MongoDB.
- For balance-critical flows, prefer MongoDB transactions if the deployment supports them.
- If transactions are not available locally, clearly document the fallback behavior and tests.

## Security rules

- Do not commit local environment files or real credentials.
- Keep `.env.example` safe and fake.
- Hash user passwords with the project helper in `app/common/utils.py`; never store plaintext passwords.
- Do not log sensitive values, authorization headers, raw passwords, or database connection strings.
- Validate external input with Pydantic schemas.
- For auth work, centralize JWT logic in an auth/security helper.

## Risk / PaySim rules

The risk module is intended to support fraud/risk scoring and Kaggle PaySim experiments, but it should not block the core wallet API.

When adding risk features:

- Keep ML/data-processing code isolated from transaction execution logic.
- Treat Kaggle data as local development data.
- Keep large datasets in `data/raw`, `data/processed`, or `data/sample`.
- Do not require a full Kaggle dataset for normal unit tests.
- Provide small sample fixtures for tests when risk logic needs data.
- Risk scoring should return explainable outputs, for example score, risk level, and reasons.

## Testing rules

Add or update tests for every meaningful behavior change.

Use `pytest` and `pytest-asyncio` for async tests.

Minimum expectations:

- common helpers: pure unit tests
- API routes: FastAPI test client or `httpx`
- service logic: unit tests with mocked repositories when possible
- MongoDB integration: mark clearly and avoid requiring remote credentials
- money movement: test successful flow, insufficient balance, duplicate request, invalid amount, and failed transaction handling

Do not make tests depend on large datasets, real external services, or real credentials.

## Code style

- Python 3.10+.
- Prefer type hints for function parameters and return values.
- Use Pydantic v2 style.
- Keep functions small and named by business meaning.
- Prefer clear code over clever abstractions.
- Do not introduce new frameworks or heavy dependencies without explaining why.
- Keep comments useful: explain business constraints, not obvious syntax.

## Git and change management

Before making changes:

1. Read this file.
2. Read `README.md`.
3. Inspect the specific module/files affected by the task.
4. Check current tests before adding new behavior.

When changing code:

- Make focused changes.
- Do not rewrite unrelated files.
- Do not reformat the whole repository unless the task is formatting.
- Update README or this file when setup, architecture, or commands change.
- Mention validation commands run and any commands that could not be run.

## Communication rules for this repo owner

The repo owner is learning Fintech and backend architecture. When explaining changes or plans, use simple Vietnamese by default, with short English technical terms when useful.

Prefer explaining flows with concrete examples such as:

- deposit 100,000 VND
- transfer 50,000 VND from wallet A to wallet B
- one debit plus one credit ledger entry

Avoid pretending incomplete modules are finished. If a file is a placeholder, say it is a placeholder and propose the next implementation step.
