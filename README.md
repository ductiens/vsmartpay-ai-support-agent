# Mini Wallet Python

A secure, high-performance Fintech Mini-Wallet application backend built with FastAPI, MongoDB, and Python. This project features asynchronous database operations, modular design, and robust data analytics/risk scoring ready for Kaggle dataset integrations.

---

## 🚀 Key Features

* **FastAPI Backend**: Fully asynchronous endpoint handlers with automated Swagger UI documentation.
* **MongoDB & Motor**: Non-blocking database transactions and high-concurrency connections suited for high-volume transactions (fully compatible with MongoDB Atlas).
* **Modular Architecture**: Separate sub-modules for `users`, `wallets`, `transactions`, `ledger`, and `risk` scoring.
* **Risk & Fraud Analytics**: Built-in foundation for risk analysis using machine learning on the Kaggle PaySim dataset.

---

## 🛠️ Technology Stack

* **Language**: Python 3.10+
* **Web Framework**: FastAPI (Uvicorn as ASGI server)
* **Database**: MongoDB (via `motor` asynchronous driver & `pymongo`)
* **Validation & Settings**: Pydantic v2 & Pydantic Settings
* **Data Processing**: Pandas, tqdm
* **Machine Learning & Datasets**: Kaggle API (for PaySim dataset download & training)
* **Containerization**: Docker & Docker Compose

---

## 📂 Project Structure

```text
mini-wallet-python/
├── app/
│   ├── main.py            # Main application entrypoint
│   ├── config.py          # Configuration & environment variables reader
│   ├── database.py        # Asynchronous MongoDB (Motor) connection manager
│   │
│   ├── modules/           # Business logic modules
│   │   ├── users/         # User management, authentication, & profiles
│   │   ├── wallets/       # Wallet accounts & balances
│   │   ├── transactions/  # Peer-to-peer transfers, deposits, withdrawals
│   │   ├── ledger/        # Double-entry ledger entries for absolute consistency
│   │   └── risk/          # Kaggle dataset integration & real-time risk scoring
│   │       ├── service.py
│   │       ├── rules.py
│   │       └── schema.py
│   │
│   └── common/            # Shared utilities, exceptions, & helpers
│
├── scripts/               # Helper & automation scripts
│   ├── download_kaggle_dataset.py   # Pulls datasets from Kaggle
│   ├── inspect_csv.py               # Utility to inspect large raw data
│   ├── import_paysim_to_mongo.py   # Imports CSV datasets to MongoDB
│   ├── seed_demo_data.py            # Generates test sandbox data
│   ├── reset_db.py                  # Resets database collections
│   └── README.md
│
├── data/                  # Git-ignored local data directories
│   ├── raw/               # Downloaded Kaggle datasets (e.g. PaySim CSV)
│   ├── processed/         # Cleaned/processed datasets
│   └── sample/            # Sandbox/sample sets for fast testing
│
├── tests/                 # Unit & integration testing suites
├── requirements.txt       # Dependencies
├── .env                   # Environment configurations
├── .env.example           # Example environment template
└── docker-compose.yml     # Local services deployment orchestration
```

---

## ⚙️ Quick Start

### 1. Prerequisites
Ensure you have the following installed on your machine:
* Python 3.10 or higher
* MongoDB Atlas cluster or a local MongoDB instance

### 2. Install Dependencies
Create a virtual environment and install the required dependencies:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Environment Configurations
Copy `.env.example` to `.env` and fill in your connection details (especially your **MongoDB Atlas connection URI**):
```bash
cp .env.example .env
```

Open `.env` and adjust the variables:
```env
MONGODB_URL=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=mini_wallet
SECRET_KEY=generate-a-secure-random-key-here
```

### 4. Run the Application
Start the FastAPI development server using Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

* **API Base URL**: `http://127.0.0.1:8000`
* **Interactive API Docs (Swagger)**: `http://127.0.0.1:8000/docs`
* **Health Check Endpoint**: `http://127.0.0.1:8000/health`
