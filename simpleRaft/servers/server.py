import asyncio
import logging

import zmq
import zmq.asyncio

from ..boards.memory_board import MemoryBoard
from ..states.state import State


class Server:
    def __init__(self, name, state, log, messageBoard, neighbors):
        self._name = name
        self._state = state
        self._log = log
        self._messageBoard = messageBoard
        self._neighbors = neighbors
        self._clear()
        self._state.set_server(self)
        self._messageBoard.set_owner(self)

    def _clear(self):
        self._total_nodes = 0
        self._commitIndex = 0
        self._currentTerm = 0
        self._lastApplied = 0
        self._lastLogIndex = 0
        self._lastLogTerm = None

    async def send_message(self, message):
        ...

    async def receive_message(self, message):
        ...

    async def post_message(self, message):
        ...

    async def on_message(self, message):
        ...


class ZeroMQServer(Server):
    def __init__(
        self, name, state: State, log=None, messageBoard=None, neighbors=None, port=0
    ):
        if log == None:
            log = []
        if neighbors == None:
            neighbors = []
        if messageBoard == None:
            messageBoard = MemoryBoard()

        super().__init__(name, state, log, messageBoard, neighbors)
        self._port = port
        self._stop = False

    async def subscriber(self):
        logger = logging.getLogger("raft")
        context = zmq.asyncio.Context()
        socket = context.socket(zmq.SUB)
        for n in self._neighbors:
            socket.connect("tcp://%s:%d" % (n._name, n._port))

        while not self._stop:
            try:
                message = await socket.recv()
            except zmq.error.ContextTerminated as e:
                break
            if not message:
                continue
            logger.debug(f"Got message: {message}")
            await self.on_message(message)
        socket.close()

    async def publisher(self):
        logger = logging.getLogger("raft")
        context = zmq.asyncio.Context()
        socket = context.socket(zmq.PUB)
        if self._port == 0:
            self._port = socket.bind_to_random_port("tcp://*")
        else:
            socket.bind("tcp://*:%d" % self._port)
        logger.info(f"publish port: {self._port}")

        while not self._stop:
            message = await self._messageBoard.get_message()
            if not message:
                continue  # sleep wait?
            try:
                await socket.send_string(str(message))
            except Exception as e:
                print(e)
                break
        socket.close()

    async def run(self):
        asyncio.create_task(self.publisher())
        asyncio.create_task(self.subscriber())

    def stop(self):
        self._stop = True

    def add_neighbor(self, neighbor):
        self._neighbors.append(neighbor)

    def remove_neighbor(self, neighbor):
        self._neighbors.remove(neighbor)

    async def send_message(self, message):
        for n in self._neighbors:
            message._receiver = n._name
            await n.post_message(message)

    async def receive_message(self, message):
        n = [n for n in self._neighbors if n._name == message.receiver]
        if len(n) > 0:
            await n[0].post_message(message)

    async def post_message(self, message):
        await self._messageBoard.post_message(message)

    async def on_message(self, message):
        state, response = await self._state.on_message(message)

        self._state = state
