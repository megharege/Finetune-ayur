from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import logging

from app.core.config import settings
from app.database import engine, Base, SessionLocal
from app.models import *
from app.seed_data.seeder import seed_database

# Routers
from app.routers import (
    auth,
    intake,
    triage,
    search,
    doctors,
    appointments,
    consultations,
    prescriptions,
    hospital,
    analytics,
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Seed initial verified & Kaggle doctor data
with SessionLocal() as db_session:
    seed_database(db_session)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Doctor-facing verified classical shloka RAG search engine & comprehensive Ayurvedic Hospital Platform.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(intake.router, prefix=settings.API_V1_STR)
app.include_router(triage.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(doctors.router, prefix=settings.API_V1_STR)
app.include_router(appointments.router, prefix=settings.API_V1_STR)
app.include_router(consultations.router, prefix=settings.API_V1_STR)
app.include_router(prescriptions.router, prefix=settings.API_V1_STR)
app.include_router(hospital.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "platform": settings.PROJECT_NAME,
        "version": "2.0.0",
        "classical_texts": 8,
        "verified_chunks": 7549
    }

# --- WebRTC & Chat WebSocket Signalling Hub ---
class TeleconsultConnectionManager:
    def __init__(self):
        # room_id -> list of active WebSockets
        self.active_rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = []
        self.active_rooms[room_id].append(websocket)
        logging.info(f"Client joined teleconsult room: {room_id}")

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_rooms:
            if websocket in self.active_rooms[room_id]:
                self.active_rooms[room_id].remove(websocket)
            if not self.active_rooms[room_id]:
                del self.active_rooms[room_id]

    async def broadcast_to_room(self, message: dict, room_id: str, sender: WebSocket):
        if room_id in self.active_rooms:
            for connection in self.active_rooms[room_id]:
                if connection != sender:
                    await connection.send_json(message)

manager = TeleconsultConnectionManager()

@app.websocket("/ws/teleconsult/{room_id}")
async def teleconsult_websocket(websocket: WebSocket, room_id: str):
    """
    Step 8: Video consult (WebRTC signaling for peer video + live chat + clinical whiteboarding).
    Relays SDP offers, answers, ICE candidates, and real-time chat messages between doctor and patient.
    """
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast signaling payload to the other peer in the room
            await manager.broadcast_to_room(data, room_id, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
