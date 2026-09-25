# factory-health-agent

## Project Name
Factory Health & Response Agent

## Description
A hybrid Agentic AI solution combining Predictive Maintenance, Root Cause Analysis, and Factory Energy Optimization for Industry 4.0 & Manufacturing.

## Tech Stack
- Frontend: Next.js, TypeScript, Tailwind CSS, App Router
- Backend: Python, FastAPI, Uvicorn, LangGraph, Scikit-learn, Pandas, Numpy

## Project Structure
```text
factory-health-agent/
├── frontend/       # Next.js frontend application
└── backend/        # FastAPI Python backend application
    ├── app/        # Main application module
    ├── agents/     # Agent logic (LangGraph, etc.)
    ├── ml/         # Machine learning models
    ├── services/   # Business logic and external services
    ├── models/     # Pydantic and database models
    ├── database/   # Database connection and queries
    └── data/       # Data storage
```

## How to start frontend
```bash
cd frontend
npm install
npm run dev
```

## How to start backend
```bash
cd backend
# Activate virtual environment
# Windows:
.\\venv\\Scripts\\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Machine Data Synchronization & Dynamic Onboarding

The backend uses `backend/data/machine_metadata.csv` as the authoritative machine catalog for the factory fleet.

### Adding a New Machine to the Fleet:
1. Add the machine entry to `backend/data/machine_metadata.csv`:
   ```csv
   M_011,Packaging Line 11,Packaging Line,2.5,150,2021-03-15,8500,15,High
   ```
2. Run the synchronization utility to generate missing sensor telemetry, production logs, and maintenance records:
   ```bash
   cd backend/data
   python sync_machine_data.py
   ```
   *(Or run `python generate_dataset.py` to regenerate and validate all datasets).*
3. Retrain the predictive models with the updated fleet telemetry:
   ```bash
   cd backend/ml
   python train_models.py
   ```
4. Refresh the frontend dashboard (`http://localhost:3000`). The new machine will immediately display live telemetry, dynamic ML health predictions (e.g. Healthy / Low Risk), and updated fleet summary counts without any hardcoded frontend values.

