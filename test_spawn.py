
import asyncio
import websockets
import json

async def test_spawn():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # 1. Send spawn command
        spawn_msg = {
            "action": "spawn",
            "agent_name": "test_verification_agent",
            "task": "Dime qué hora es y lista los archivos en el directorio actual.",
            "allowed_tools": ["shell_execute", "filesystem_read"],
            "provider": "ollama",
            "model": "qwen2.5-coder:7b"
        }
        await websocket.send(json.dumps(spawn_msg))
        print("Sent spawn message")
        
        # 2. Wait for feedback
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)
                print(f"Received: {data.get('type')} - {data.get('message') or data.get('payload')}")
                
                if data.get("type") == "agent_output":
                    print("SUCCESS: Received agent output!")
                    break
            except asyncio.TimeoutError:
                print("Timeout waiting for agent response.")
                break

if __name__ == "__main__":
    asyncio.run(test_spawn())
