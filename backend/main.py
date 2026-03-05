from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import logging
import asyncio
from backend.core.config import settings
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table

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

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Kernel subsystems...")
    asyncio.create_task(system_scheduler.start_scheduler())
    
    # Bridge the Kernel Memory Bus to WebSockets
    async def bridge_to_ws(msg: MessagePayload):
        # Format for backward compatibility with the Dashboard components
        await manager.broadcast({
            "type": msg.event_type,
            "source": msg.source_pid or "kernel",
            "payload": msg.data,
            "target": msg.target_pid
        })
    system_memory_bus.subscribe("*", bridge_to_ws)

@app.on_event("shutdown")
async def shutdown_event():
    system_scheduler.stop_scheduler()

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "AgentOS Kernel is running securely."}
    
@app.get("/api/processes")
async def list_processes():
    return {pid: proc.__dict__ for pid, proc in system_process_table.processes.items()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Dashboard WS message: {data}")
            try:
                msg = json.loads(data)
                if msg.get("action") == "spawn":
                    agent_name = msg.get("agent_name", "test_agent")
                    proc = AIProcess(
                        agent_name=agent_name,
                        task_description="Simulated WS Task",
                        limits=ResourceLimits(max_runtime_sec=30)
                    )
                    await system_scheduler.submit(proc, Priority.MEDIUM)
                    await manager.broadcast({"type": "info", "message": f"Spawned {proc.pid}"})
            except Exception as e:
                logger.error(f"Failed to process WS command: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Dashboard disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
