#!/usr/bin/env python3

import asyncio
import unittest

from simpleRaft.boards.memory_board import MemoryBoard
from simpleRaft.messages.append_entries import AppendEntriesMessage
from simpleRaft.messages.request_vote import RequestVoteMessage
from simpleRaft.servers.server import ZeroMQServer as Server
from simpleRaft.states.follower import Follower


class TestFollowerServer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        board = MemoryBoard()
        state = Follower()
        self.oserver = Server(0, state, [], board, [])

        board = MemoryBoard()
        state = Follower()
        self.server = Server(1, state, [], board, [self.oserver])
        asyncio.create_task(self.oserver.run())
        asyncio.create_task(self.server.run())

    def tearDown(self):
        self.oserver.stop()
        self.server.stop()

    async def test_follower_server_on_message(self):
        msg = AppendEntriesMessage(0, 1, 2, {})
        await self.server.on_message(msg)

    async def test_follower_server_on_receive_message_with_lesser_term(self):

        msg = AppendEntriesMessage(0, 1, -1, {})

        await self.server.on_message(msg)

        msg = await self.oserver._messageBoard.get_message()
        self.assertEqual(False, msg.data["response"])

    async def test_follower_server_on_receive_message_with_greater_term(self):

        msg = AppendEntriesMessage(0, 1, 2, {})

        await self.server.on_message(msg)

        self.assertEqual(2, self.server._currentTerm)

    async def test_follower_server_on_receive_message_where_log_does_not_have_prevLogTerm(
        self
    ):
        self.server._log.append({"term": 100, "value": 2000})
        msg = AppendEntriesMessage(
            0,
            1,
            2,
            {
                "prevLogIndex": 0,
                "prevLogTerm": 1,
                "leaderCommit": 1,
                "entries": [{"term": 1, "value": 100}],
            },
        )

        await self.server.on_message(msg)

        msg = await self.oserver._messageBoard.get_message()
        self.assertEqual(False, msg.data["response"])
        self.assertEqual([], self.server._log)

    async def test_follower_server_on_receive_message_where_log_contains_conflicting_entry_at_new_index(
        self
    ):

        self.server._log.append({"term": 1, "value": 0})
        self.server._log.append({"term": 1, "value": 200})
        self.server._log.append({"term": 1, "value": 300})
        self.server._log.append({"term": 2, "value": 400})

        msg = AppendEntriesMessage(
            0,
            1,
            2,
            {
                "prevLogIndex": 0,
                "prevLogTerm": 1,
                "leaderCommit": 1,
                "entries": [{"term": 1, "value": 100}],
            },
        )

        await self.server.on_message(msg)
        self.assertEqual({"term": 1, "value": 100}, self.server._log[1])
        self.assertEqual(
            [{"term": 1, "value": 0}, {"term": 1, "value": 100}], self.server._log
        )

    async def test_follower_server_on_receive_message_where_log_is_empty_and_receives_its_first_value(
        self
    ):

        msg = AppendEntriesMessage(
            0,
            1,
            2,
            {
                "prevLogIndex": 0,
                "prevLogTerm": 100,
                "leaderCommit": 1,
                "entries": [{"term": 1, "value": 100}],
            },
        )

        await self.server.on_message(msg)
        self.assertEqual({"term": 1, "value": 100}, self.server._log[0])

    async def test_follower_server_on_receive_vote_request_message(self):
        msg = RequestVoteMessage(
            0, 1, 2, {"lastLogIndex": 0, "lastLogTerm": 0, "entries": []}
        )

        await self.server.on_message(msg)

        self.assertEqual(0, self.server._state._last_vote)
        msg = await self.oserver._messageBoard.get_message()
        self.assertEqual(True, msg.data["response"])

    async def test_follower_server_on_receive_vote_request_after_sending_a_vote(self):
        msg = RequestVoteMessage(
            0, 1, 2, {"lastLogIndex": 0, "lastLogTerm": 0, "entries": []}
        )

        await self.server.on_message(msg)

        msg = RequestVoteMessage(2, 1, 2, {})
        await self.server.on_message(msg)

        self.assertEqual(0, self.server._state._last_vote)


if __name__ == "__main__":
    unittest.main()
