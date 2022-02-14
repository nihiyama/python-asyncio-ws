import asyncio
from typing import Any
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import WebSocket


class Event:
    def __init__(self, channel, message):
        self.channel = channel
        self.message = message

    def __eq__(self, other):
        return (
            isinstance(other, Event)
            and self.channel == other.channel
            and self.message == other.message
        )

    def __repr__(self):
        return f'Event(channel={self.channel!r}, message={self.message!r})'


class Unsubscribed(Exception):
    pass


class Broadcast:
    def __init__(self, url: str):
        parsed_url = urlparse(url)
        self._subscribers = {}
        if parsed_url.scheme == 'redis':
            from app.redis_broadcast.redis_backend import RedisBackend
            self._backend = RedisBackend(url)
        else:
            raise Exception("Must be set redis url")

    async def __aenter__(self) -> 'Broadcast':
        await self.connect()
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        await self._backend.connect()
        self._listener_task = asyncio.create_task(self._listener())

    async def disconnect(self) -> None:
        if self._listener_task.done():
            self._listener_task.result()
        else:
            self._listener_task.cancel()
        await self._backend.disconnect()

    async def _listener(self) -> None:
        while True:
            event = await self._backend.next_published()
            for queue in list(self._subscribers.get(event.channel, [])):
                await queue.put(event)

    async def publish(self, channel: str, message: Any) -> int:
        return await self._backend.publish(channel, message)
    
    async def unsubscribe(self, channel: str) -> None:
        await self._backend.unsubscribe(channel)

    @asynccontextmanager
    async def subscribe(self, channel: str, ws: WebSocket) -> 'WebsSocketHealthCheckSubscriber':
        queue: asyncio.Queue = asyncio.Queue()

        try:
            if not self._subscribers.get(channel):
                await self._backend.subscribe(channel)
                self._subscribers[channel] = set([queue])
            else:
                self._subscribers[channel].add(queue)

            yield WebsSocketHealthCheckSubscriber(queue, ws)

        finally:
            self._subscribers[channel].remove(queue)
            if not self._subscribers.get(channel):
                del self._subscribers[channel]
                await self._backend.unsubscribe(channel)
            await queue.put(None)


class WebsSocketHealthCheckSubscriber:
    def __init__(self, queue: asyncio.Queue, ws: WebSocket):
        self._ws = ws
        self._queue = queue

    async def __aiter__(self):
        try:
            while True:
                healthcheck_task = asyncio.create_task(self.healthcheck())
                item_task = asyncio.create_task(self.get())
                done, pending = await asyncio.wait(
                    [healthcheck_task, item_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                if item_task in done:
                    yield item_task.result()
                    for task in pending:
                        if not task.cancelled():
                            task.cancel()
                else:
                    for task in pending:
                        if not task.cancelled():
                            task.cancel()
                    break
        except Unsubscribed:
            pass

    async def get(self) -> Event:
        item = await self._queue.get()
        if item is None:
            raise Unsubscribed()
        return item

    async def healthcheck(self) -> None:
        try:
            while True:
                await self._ws.receive_json()
        except BaseException:
            return
