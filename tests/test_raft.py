#!/usr/bin/env python3

import unittest
import uuid

from simpleRaft.messages.append_entries import AppendEntriesMessage
from simpleRaft.servers.server import ZeroMQServer
from simpleRaft.states.candidate import Candidate
from simpleRaft.states.follower import Follower
from simpleRaft.states.leader import Leader

N = 5


class TestRaft(unittest.IsolatedAsyncioTestCase):
    @classmethod
    async def asyncSetUpClass(cls):
        cls.servers = []
        for i in range(N):
            s = ZeroMQServer("S%d" % i, Follower(), port=6666 + i)
            cls.servers.append(s)
        for i in range(N):
            me = cls.servers[i]
            neighbors = [n for n in cls.servers if n != me]
            for n in neighbors:
                me.add_neighbor(n)

        server0 = cls.servers[0]
        server0._state = Candidate()
        for i in range(N):
            if isinstance(cls.servers[i]._state, Leader):
                cls.leader = cls.servers[i]
                break
        else:
            # Manually elect server-0 as the leader
            cls.servers[0]._state = leader = Leader()
            cls.leader = cls.servers[0]
            await leader.set_server(cls.leader)

    @classmethod
    async def asyncTearDownClass(cls):
        pass

    async def asyncSetUp(self):
        await self.asyncSetUpClass()
        for i in range(N):
            self.servers[i]._state.__init__()
            self.servers[i]._messageBoard.__init__()
            self.servers[i]._log.clear()
            self.servers[i]._clear()

    async def _perform_heart_beat(self):
        await self.leader._state._send_heart_beat()
        for i in self.leader._neighbors:
            await i.on_message(await i._messageBoard.get_message())

        for _, i in self.leader._messageBoard._board._queue:
            await self.leader.on_message(i)

    async def test_heart_beat(self):
        await self._perform_heart_beat()
        expected = dict(("S%d" % i, 0) for i in range(1, N))
        self.assertEqual(expected, self.leader._state._nextIndexes)

    async def test_append(self):
        await self._perform_heart_beat()

        msg = AppendEntriesMessage(
            0,
            None,
            1,
            {
                "prevLogIndex": 0,
                "prevLogTerm": 0,
                "leaderCommit": 1,
                "entries": [{"term": 1, "value": 100}],
            },
        )

        await self.leader.send_message(msg)

        for i in self.leader._neighbors:
            await i.on_message(await i._messageBoard.get_message())

        for i in self.leader._neighbors:
            self.assertEqual([{"term": 1, "value": 100}], i._log)

    async def test_dirty(self):
        self.leader._neighbors[0]._log.append({"term": 2, "value": 100})
        self.leader._neighbors[0]._log.append({"term": 2, "value": 200})
        self.leader._neighbors[1]._log.append({"term": 3, "value": 200})
        self.leader._log.append({"term": 1, "value": 100})

        await self._perform_heart_beat()

        msg = AppendEntriesMessage(
            0,
            None,
            1,
            {
                "prevLogIndex": 0,
                "prevLogTerm": 0,
                "leaderCommit": 1,
                "entries": [{"term": 1, "value": 100}],
            },
        )

        await self.leader.send_message(msg)

        for i in self.leader._neighbors:
            await i.on_message(await i._messageBoard.get_message())

        for i in self.leader._neighbors:
            self.assertEqual([{"term": 1, "value": 100}], i._log)


if __name__ == "__main__":
    unittest.main()
