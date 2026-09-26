from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Ensure the backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import get_current_user, ensure_users_csv_exists
from app.routes import health, machines, agent, simulation, notifications, auth

# Initialize FastAPI
app = FastAPI(
    title="Factory Health Agent API",
    description="ML backend for predicting machine failures and anomalies.",
    version="1.0.0"
)

# Initialize user catalog and demo operator account
ensure_users_csv_exists()

# Configure CORS
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

cors_env = os.environ.get("CORS_ORIGINS", "").strip()
if cors_env:
    origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    if not origins:
        origins = default_origins
else:
    origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public endpoints
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

# Protected application endpoints (require valid authenticated operator session)
app.include_router(machines.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(agent.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(simulation.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(notifications.router, prefix="/api", dependencies=[Depends(get_current_user)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
