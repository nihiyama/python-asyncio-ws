import asyncio
from time import sleep
from typing import Any, Dict, Optional
import json

from broadcaster import Broadcast 
from websockets.legacy import client as ws_client
from fastapi import FastAPI, WebSocket, BackgroundTasks, Body, status

from config import settings

app = FastAPI()

broadcast = Broadcast("redis://redis:6379")


@app.websocket("/events/ws")
async def event_handler(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data: Dict[str, Any] = await ws.receive_json()
            if data.get("message") == "hello":
                token: Optional[str] = data.get("token")
                if token is not None and (token == settings.WS_SERVER_TOKEN_1 or token == settings.WS_SERVER_TOKEN_2):
                    req_data = {
                        "message": "hello!",
                    }
                    await ws.send_json(req_data)
                    print("001")
                    async with broadcast.subscribe(channel=token, ws=ws) as subscriber:
                        # subscriber_task = asyncio.create_task(subscriber)
                        # ws_task = asyncio.create_task(ws)
                        # done, pending = await asyncio.wait(
                        #     {ws_task},
                        #     return_when=asyncio.FIRST_COMPLETED
                        # )
                        # for task in pending:
                        #     task.cancel()
                        print("002")
                        async for event in subscriber:   
                            message: Dict[str, Any] = json.loads(event.message)
                            if message.get("key") == settings.WS_SERVER_KEY:
                                req_data = {
                                    "event_id": message.get("event_id"),
                                    "message": message.get("message")
                                }
                                await ws.send_json(req_data)                   
    except Exception:
        # print(e)
        # if subscriber is not None:
        #     del subscriber
        await ws.close()


async def create_event_task(event_id: int, token: str):
    req_data = {
        "event_id": event_id,
        "message": "your event",
        "key": settings.WS_SERVER_KEY
    }
    try:
        aaa = await broadcast.publish(channel=token, message=json.dumps(req_data))
        print(aaa)
    except Exception as e:
        print("bbb", e)


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

@app.on_event("startup")
async def startup_event():
    await broadcast.connect()
