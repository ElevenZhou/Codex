from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AuctionPlayer:
    agent_id: str
    credits: int
    score: int
    values: List[int]


class MiniAuctionEngine:
    """
    Mini Auction（MVP）：
    - 固定若干轮，每轮拍卖一个物品
    - 每人对每个物品有私有估值 values[i]
    - 动作：bid（结构化），chat 仅记录
    """

    def __init__(self, seed: int, players: List[str], rounds: int = 5, starting_credits: int = 25):
        if len(players) < 2:
            raise ValueError("need_at_least_two_players")
        self._rng = random.Random(seed)
        self._rounds = rounds
        self._players: List[AuctionPlayer] = []
        for p in players:
            values = [self._rng.randrange(1, 16) for _ in range(rounds)]
            self._players.append(AuctionPlayer(agent_id=p, credits=starting_credits, score=0, values=values))

        self._round = 0
        self._done = False
        self._winner: Optional[str] = None
        self._bids: Dict[str, int] = {}

    def _by_id(self, agent_id: str) -> AuctionPlayer:
        for p in self._players:
            if p.agent_id == agent_id:
                return p
        raise ValueError("unknown_agent")

    def observation(self, agent_id: str) -> Dict[str, Any]:
        me = self._by_id(agent_id)
        return {
            "type": "mini_auction_obs",
            "round": self._round,
            "rounds": self._rounds,
            "me": {
                "credits": me.credits,
                "score": me.score,
                "private_value": None if self._round >= self._rounds else me.values[self._round],
            },
            "public": {
                "scores": {p.agent_id: p.score for p in self._players},
                "credits": {p.agent_id: p.credits for p in self._players},
            },
            "submitted_bids": list(self._bids.keys()),
        }

    def legal_actions(self, agent_id: str) -> List[Dict[str, Any]]:
        me = self._by_id(agent_id)
        max_bid = max(0, me.credits)
        return [{"type": "bid", "amount": a} for a in range(0, max_bid + 1)]

    def apply(
        self, agent_id: str, action: Dict[str, Any], chat: Optional[str]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        if self._done:
            return False, "match_done", None
        if self._round >= self._rounds:
            self._finish()
            return False, "match_done", None
        if agent_id in self._bids:
            return False, "already_bid", None

        if action.get("type") != "bid":
            return False, "unknown_action", None
        amount = action.get("amount")
        if not isinstance(amount, int):
            return False, "amount_not_int", None
        me = self._by_id(agent_id)
        if amount < 0 or amount > me.credits:
            return False, "invalid_amount", None

        self._bids[agent_id] = amount
        delta: Dict[str, Any] = {"bid": {"agent_id": agent_id, "amount": amount}}

        if len(self._bids) == len(self._players):
            delta["settle"] = self._settle_round()
        return True, None, delta

    def _settle_round(self) -> Dict[str, Any]:
        ranked = sorted(self._bids.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        winner_id, price = ranked[0]
        winner = self._by_id(winner_id)
        value = winner.values[self._round]

        winner.credits -= price
        winner.score += value - price

        settle = {
            "round": self._round,
            "winner": winner_id,
            "price": price,
            "winner_value": value,
            "scores": {p.agent_id: p.score for p in self._players},
            "credits": {p.agent_id: p.credits for p in self._players},
        }

        self._round += 1
        self._bids = {}

        if self._round >= self._rounds:
            self._finish()
        return settle

    def _finish(self) -> None:
        self._done = True
        ranked = sorted(self._players, key=lambda p: (p.score, p.agent_id), reverse=True)
        self._winner = ranked[0].agent_id if ranked else None

    def status(self, force: bool = False) -> Dict[str, Any]:
        if self._done:
            return {"done": True, "winner": self._winner}
        if force:
            self._finish()
            return {"done": True, "winner": self._winner}
        return {"done": False}

