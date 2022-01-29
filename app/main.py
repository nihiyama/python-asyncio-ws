from typing import Any, Dict, Optional
import json

from websockets.legacy import client as ws_client
from fastapi import FastAPI, WebSocket, BackgroundTasks, Body, status

from config import settings

app = FastAPI()

clients = {}

# clients = {
#     "sec-client-key1": {
#         "token": "changeme",
#         "ws": "ws"
#     },
#     "sec-client-key2": {
#         "token": "changeme",
#         "ws": "ws"
#     },
#     "sec-client-key3": {
#         "token": "changeme",
#         "ws": "ws"
#     },
#     "sec-client-key4": {
#         "token": "changeme",
#         "ws": "ws"
#     },
# }

@app.websocket("/events/ws")
async def event_handler(ws: WebSocket):
    await ws.accept()
    key = ws.headers.get("sec-websocket-key")
    clients[key] = {}
    try:
        while True:
            data: Dict[str, Any] = await ws.receive_json()
            if data.get("message") == "hello":
                token: Optional[str] = data.get("token")
                if token is not None and (token == settings.WS_SERVER_TOKEN_1 or token == settings.WS_SERVER_TOKEN_2):
                    req_data = {
                        "message": "hello!",
                    }
                    clients[key] = {
                        "token": token,
                        "ws": ws
                    }
                    json.dumps(req_data)
                    await ws.send_json(req_data)
                else:
                    req_data = {
                        "message": "token invalid error!",
                        "is_err": True
                    }
                    await ws.send_json(req_data)
            elif data.get("message") == "event" and data.get("key") == settings.WS_SERVER_KEY:
                event_id: Optional[int] = data.get("event_id")
                token: Optional[str] = data.get("token")
                if event_id is not None and token is not None:
                    for c in clients:
                        if clients[c]["token"] == token:
                            req_data = {
                                "event_id": event_id,
                                "message": "put your event"
                            }
                            c_ws: WebSocket = clients[c]["ws"]
                            await c_ws.send_json(req_data)
    except Exception as e:
        await ws.close()
        del clients[key]


async def create_event_task(event_id: int, token: str):
    async with ws_client.connect(settings.WS_SERVER_URL) as ws:
        req_data = {
            "token": token,
            "event_id": event_id,
            "message": "event",
            "key": settings.WS_SERVER_KEY
        }
        await ws.send(json.dumps(req_data))


@app.post("/events/", status_code=status.HTTP_202_ACCEPTED)
async def creata_event(
    background_tasks: BackgroundTasks,
    *,
    event_id: int = Body(...),
    token: str = Body(...)
) -> Any:
    background_tasks.add_task(create_event_task, event_id, token)
    return {
        "detail": "Accepted!"
    }