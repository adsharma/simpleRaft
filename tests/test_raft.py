#!/usr/bin/env python3

import unittest
import sys

from simpleRaft.messages.append_entries import AppendEntriesMessage
from simpleRaft.servers.server import ZeroMQServer
from simpleRaft.states.candidate import Candidate
from simpleRaft.states.leader import Leader
from simpleRaft.states.follower import Follower

N = 5


class TestRaft(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.servers = []
        for i in range(N):
            s = ZeroMQServer("S%d" % i, Follower(), port=6666 + i)
            self.servers.append(s)
        for i in range(N):
            me = self.servers[i]
            neighbors = [n for n in self.servers if n != me]
            for n in neighbors:
                me.add_neighbor(n)

        server0 = self.servers[0]
        server0._state = Candidate()
        for i in range(N):
            if isinstance(self.servers[i]._state, Leader):
                self.leader = self.servers[i]
                break
        else:
            # Manually elect server-0 as the leader
            self.servers[0]._state = Leader()
            self.leader = self.servers[0]
            self.leader._state.set_server(self.servers[0])

    @classmethod
    def tearDownClass(self):
        pass

    def setUp(self):
        for i in range(N):
            self.servers[i]._state.__init__()
            self.servers[i]._messageBoard.__init__()
            self.servers[i]._log.clear()
            self.servers[i]._clear()

    def _perform_hearbeat(self):
        self.leader._state._send_heart_beat()
        for i in self.leader._neighbors:
            i.on_message(i._messageBoard.get_message())

        for i in self.leader._messageBoard._board:
            self.leader.on_message(i)

    def test_heartbeat(self):
        self._perform_hearbeat()
        expected = dict(('S%d' % i, 0) for i in range(1, N))
        self.assertEqual(expected, self.leader._state._nextIndexes)

    def test_append(self):
        self._perform_hearbeat()

        msg = AppendEntriesMessage(0, None, 1, {
            "prevLogIndex": 0,
            "prevLogTerm": 0,
            "leaderCommit": 1,
            "entries": [{"term": 1, "value": 100}]})

        self.leader.send_message(msg)

        for i in self.leader._neighbors:
            i.on_message(i._messageBoard.get_message())

        for i in self.leader._neighbors:
            self.assertEqual([{"term": 1, "value": 100}], i._log)

    def test_dirty(self):
        self.leader._neighbors[0]._log.append({"term": 2, "value": 100})
        self.leader._neighbors[0]._log.append({"term": 2, "value": 200})
        self.leader._neighbors[1]._log.append({"term": 3, "value": 200})
        self.leader._log.append({"term": 1, "value": 100})

        self._perform_hearbeat()

        msg = AppendEntriesMessage(0, None, 1, {
            "prevLogIndex": 0,
            "prevLogTerm": 0,
            "leaderCommit": 1,
            "entries": [{"term": 1, "value": 100}]})

        self.leader.send_message(msg)

        for i in self.leader._neighbors:
            i.on_message(i._messageBoard.get_message())

        for i in self.leader._neighbors:
            self.assertEqual([{"term": 1, "value": 100}], i._log)


if __name__ == '__main__':
    unittest.main()