from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PlayerState:
    agent_id: str
    x: int
    y: int
    hp: int = 5


class GridArenaEngine:
    """
    回合制格子竞技（MVP）：
    - 7x7 地图
    - 动作：move / attack / wait
    - chat 仅用于回放记录，不影响裁判
    """

    def __init__(self, seed: int, players: List[str], size: int = 7):
        if len(players) < 2:
            raise ValueError("need_at_least_two_players")
        self._rng = random.Random(seed)
        self._size = size
        self._players = [PlayerState(agent_id=p, x=0, y=0) for p in players]

        self._players[0].x, self._players[0].y = 0, 0
        self._players[1].x, self._players[1].y = size - 1, size - 1
        for i in range(2, len(self._players)):
            self._players[i].x = self._rng.randrange(0, size)
            self._players[i].y = self._rng.randrange(0, size)

        self._done = False
        self._winner: Optional[str] = None

    def _by_id(self, agent_id: str) -> PlayerState:
        for p in self._players:
            if p.agent_id == agent_id:
                return p
        raise ValueError("unknown_agent")

    def observation(self, agent_id: str) -> Dict[str, Any]:
        me = self._by_id(agent_id)
        return {
            "type": "grid_arena_obs",
            "size": self._size,
            "me": {"x": me.x, "y": me.y, "hp": me.hp},
            "players": [{"agent_id": p.agent_id, "x": p.x, "y": p.y, "hp": p.hp} for p in self._players],
        }

    def legal_actions(self, agent_id: str) -> List[Dict[str, Any]]:
        _ = self._by_id(agent_id)
        return (
            [{"type": "move", "dir": d} for d in ["N", "S", "E", "W"]]
            + [{"type": "attack"}, {"type": "wait"}]
        )

    def apply(
        self, agent_id: str, action: Dict[str, Any], chat: Optional[str]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        if self._done:
            return False, "match_done", None
        me = self._by_id(agent_id)
        action_type = action.get("type")

        if action_type == "move":
            direction = action.get("dir")
            dx, dy = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}.get(direction, (None, None))
            if dx is None:
                return False, "invalid_dir", None
            nx, ny = me.x + dx, me.y + dy
            if not (0 <= nx < self._size and 0 <= ny < self._size):
                return False, "out_of_bounds", None
            me.x, me.y = nx, ny
            return True, None, {"moved_to": {"x": nx, "y": ny}}

        if action_type == "attack":
            targets = []
            for p in self._players:
                if p.agent_id == me.agent_id or p.hp <= 0:
                    continue
                if abs(p.x - me.x) + abs(p.y - me.y) == 1:
                    p.hp -= 1
                    targets.append(p.agent_id)
            if not targets:
                return True, None, {"attack": "miss"}
            self._maybe_finish()
            return True, None, {"attack_hit": targets}

        if action_type == "wait":
            return True, None, {"waited": True}

        return False, "unknown_action", None

    def _maybe_finish(self) -> None:
        alive = [p for p in self._players if p.hp > 0]
        if len(alive) == 1:
            self._done = True
            self._winner = alive[0].agent_id

    def status(self, force: bool = False) -> Dict[str, Any]:
        if not self._done:
            self._maybe_finish()
        if self._done:
            return {"done": True, "winner": self._winner}
        if force:
            best = sorted(self._players, key=lambda p: (p.hp, p.agent_id), reverse=True)[0]
            return {"done": True, "winner": best.agent_id}
        return {"done": False}

