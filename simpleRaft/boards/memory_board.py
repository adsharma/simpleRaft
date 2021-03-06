import asyncio

from .board import Board


class MemoryBoard(Board):
    def __init__(self):
        Board.__init__(self)
        self._board = asyncio.PriorityQueue()

    async def post_message(self, message):
        self._board.put_nowait((message.timestamp, message))

    async def get_message(self):
        try:
            return (await self._board.get())[1]
        except IndexError:
            return None
