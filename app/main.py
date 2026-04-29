from fastapi import FastAPI
from app.routers import chat, metrics, health

app = FastAPI()   # ✅ MUST exist

@app.get("/")
def root():
    return {"message": "Badho AI running"}

app.include_router(chat.router)
app.include_router(metrics.router)
app.include_router(health.router)