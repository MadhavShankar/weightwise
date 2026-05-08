import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow importing from services/ via symlink or direct parent path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_api.routers import auth, onboard, today, logs, history, chat, plans, routines, notifications

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

app = FastAPI(title="WeightWise API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://api.weightwise.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(onboard.router)
app.include_router(today.router)
app.include_router(logs.router)
app.include_router(history.router)
app.include_router(chat.router)
app.include_router(plans.router)
app.include_router(routines.router)
app.include_router(notifications.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
