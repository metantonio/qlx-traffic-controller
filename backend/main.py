from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging
from backend.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrafficController")

app = FastAPI(title="AI Control Tower API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for connection in self.active_connections:
            await connection.send_text(text)

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Control Tower is running securely."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Dashboard WS message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Dashboard disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
