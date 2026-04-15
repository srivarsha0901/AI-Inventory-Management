# AI Inventory Management (FreshTrack)

AI-powered grocery inventory platform with:
- Inventory onboarding (manual/CSV/photo OCR)
- POS billing and sales tracking
- Low-stock alerts and reorder suggestions
- Forecasting with ML-based demand prediction

## Project Structure

- `frontend/` - React + Vite app
- `backend/` - Flask API + MongoDB integration
- `inventory-ai/` - ML training/prediction scripts

## Prerequisites

- Python 3.10+ recommended
- Node.js 18+ recommended
- MongoDB running locally (default: `mongodb://localhost:27017/freshtrack`)

## 1) Clone

```bash
git clone https://github.com/srivarsha0901/AI-Inventory-Management.git
cd AI-Inventory-Management
```

## 2) Backend Setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env
python app.py
```

Backend runs on `http://127.0.0.1:5000`.

## 3) Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## 4) ML Setup (for Forecasting)

Open another terminal:

```bash
cd inventory-ai
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Important model note

The trained model file `inventory-ai/models/best_model.pkl` is not committed to git.

To enable forecasting:
- generate/train the model using scripts in `inventory-ai/ml/`, or
- place your compatible `best_model.pkl` into `inventory-ai/models/`.

Without this model, forecasting endpoints can fail while the rest of the app still works.

## 5) Environment Variables

Use `.env.example` at repo root as reference:

- `MONGO_URI`
- `MONGO_DB_NAME`
- `JWT_SECRET_KEY`
- `ML_MODEL_PATH` (optional)
- `CORS_ALLOW_ORIGINS`

## Quick Test Flow

1. Register manager account
2. Upload inventory CSV
3. Upload sales history CSV (optional but recommended)
4. Go to Forecast and run predictions
5. Use POS Billing and verify stock updates + alerts

