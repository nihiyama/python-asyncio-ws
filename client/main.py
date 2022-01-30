import asyncio
import argparse
import json
from typing import Any, Dict
import time
from concurrent.futures import ThreadPoolExecutor

from websockets.legacy import client as ws_client
from websockets import exceptions as ws_exceptions

from client_config import settings

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--token")
args = parser.parse_args()

def not_coro(interval: int, event: Any):
    print(event)
    time.sleep(interval)


async def hello_handler(ws: ws_client.WebSocketClientProtocol):
    req_data = {
        "token": args.token,
        "message": "hello"
    }
    await ws.send(json.dumps(req_data))
    res_data: Dict[str, Any] = json.loads(await ws.recv())
    print(res_data)
    if res_data.get("is_err"):
        raise ws_exceptions.SecurityError(f"token invalid error, {res_data}")


async def get_event_handler(ws: ws_client.WebSocketClientProtocol, executor: ThreadPoolExecutor):
    async for message in ws:
        executor.submit(not_coro, 3, message)
        print(executor._work_queue.qsize())


async def get_event_websocket(executor: ThreadPoolExecutor):
    async for ws in ws_client.connect(settings.WS_SERVER_URL):
        try:
            await hello_handler(ws)
            await get_event_handler(ws, executor)
        except ws_exceptions.ConnectionClosed:
            await asyncio.sleep(3)
            continue
        except Exception as e:
            break
        finally:
            await ws.close()

async def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        await get_event_websocket(executor)
        print(executor._work_queue.qsize())


if __name__ == "__main__":
    asyncio.run(main())
