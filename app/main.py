import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.telemetry import init_db
from app.routers import chat, health, metrics

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Pre-warm ChromaDB — eliminates cold start on first request
    from app.core.rag import _get_collection, cross_encoder
    _get_collection()
    # Touch the cross encoder so it loads into memory now
    _ = cross_encoder.predict([["warmup query", "warmup document"]])
    print("ChromaDB + CrossEncoder pre-loaded. Ready.")
    yield


app = FastAPI(title="Badho AI Career Coach", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(metrics.router)
app.include_router(health.router)

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")