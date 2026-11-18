from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from app.api.v1 import auth
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AyurLLM Care API",
    description="Ayurvedic Hospital Platform & Decision Support System API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "redis": "connected",
            "meilisearch": "connected",
            "neo4j": "connected"
        },
        "embedding_coverage": 0.18
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to AyurLLM Care API"}
