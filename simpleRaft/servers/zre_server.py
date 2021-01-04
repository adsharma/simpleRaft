import logging

from pyre import Pyre
from serde.msgpack import from_msgpack, to_msgpack
from typing import Union

from ..boards.memory_board import MemoryBoard
from ..messages.base import BaseMessage
from ..states.state import State
from .server import Server


logger = logging.getLogger("raft")


class ZREServer(Server):
    ZRE_GROUP = "raft"

    def __init__(self, name, state: State, node: Pyre, log=None, messageBoard=None):
        if log == None:
            log = []
        if messageBoard == None:
            messageBoard = MemoryBoard()

        super().__init__(name, state, log, messageBoard, [])
        self._node = node

    def add_neighbor(self, neighbor):
        self._neighbors.append(neighbor)

    def remove_neighbor(self, neighbor):
        self._neighbors.remove(neighbor)

    def send_message(self, message: Union[BaseMessage, bytes]):
        if isinstance(message, bytes):
            self._node.shout(self.ZRE_GROUP, b"/raft " + message)
        else:
            message_bytes = to_msgpack(message, ext_dict=BaseMessage.EXT_DICT)
            self._node.shout(self.ZRE_GROUP, b"/raft " + message_bytes)

    def receive_message(self, message_bytes: bytes):
        try:
            message = from_msgpack(
                BaseMessage, message_bytes, ext_dict=BaseMessage.EXT_DICT
            )
        except Exception as e:
            logger.info(e)
            return
        self.on_message(message)
        self.post_message(message)

    def post_message(self, message):
        self._messageBoard.post_message(message)

    def on_message(self, message):
        state, response = self._state.on_message(message)

        self._state = state
