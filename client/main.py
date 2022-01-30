import asyncio
import argparse
import json
from typing import Any, Dict

from websockets.legacy import client as ws_client
from websockets import exceptions as ws_exceptions

from config import settings

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--token")
args = parser.parse_args()

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


async def get_event_handler(ws: ws_client.WebSocketClientProtocol):
    async for message in ws:
        print(message)


async def main():
    # async with ws_client.connect(settings.WS_SERVER_URL) as ws:
    #     await hello_handler(ws)
    #     await get_event_handler(ws)
    async for ws in ws_client.connect(settings.WS_SERVER_URL):
        try:
            await hello_handler(ws)
            await get_event_handler(ws)
        except ws_exceptions.ConnectionClosed:
            await asyncio.sleep(3)
            continue
        except Exception as e:
            break
        finally:
            await ws.close()

if __name__ == "__main__":
    asyncio.run(main())
