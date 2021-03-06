from dataclasses import dataclass

from serde import deserialize, serialize

from .base import BaseMessage


@deserialize
@serialize
@dataclass
class RequestVoteMessage(BaseMessage):

    _type = BaseMessage.MessageType.RequestVote


@deserialize
@serialize
@dataclass
class RequestVoteResponseMessage(BaseMessage):

    _type = BaseMessage.MessageType.RequestVoteResponse
