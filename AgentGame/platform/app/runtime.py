from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.storage import append_event, save_json, update_leaderboard

from games.grid_arena.engine import GridArenaEngine
from games.mini_auction.engine import MiniAuctionEngine


@dataclass(frozen=True)
class MatchConfig:
    match_id: str
    game_id: str
    ruleset_version: str
    seed: int
    players: List[str]
    max_turns: int


class MatchRuntime:
    def __init__(self, config: MatchConfig, engine: Any, data_dir: Path):
        self.match_id = config.match_id
        self.game_id = config.game_id
        self.ruleset_version = config.ruleset_version
        self.seed = config.seed
        self.players = list(config.players)
        self.max_turns = config.max_turns
        self.created_at_ms = int(time.time() * 1000)

        self._engine = engine
        self._turn = 0
        self._done = False
        self._winner: Optional[str] = None

        self._match_dir = data_dir / self.match_id
        self._match_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            self._match_dir / "meta.json",
            {
                "match_id": self.match_id,
                "game_id": self.game_id,
                "ruleset_version": self.ruleset_version,
                "seed": self.seed,
                "players": self.players,
                "max_turns": self.max_turns,
                "created_at_ms": self.created_at_ms,
            },
        )
        append_event(self._match_dir / "replay.jsonl", {"type": "match_created", "t": self.created_at_ms})

    def public_summary(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "game_id": self.game_id,
            "ruleset_version": self.ruleset_version,
            "seed": self.seed,
            "players": self.players,
            "turn": self._turn,
            "done": self._done,
            "winner": self._winner,
            "max_turns": self.max_turns,
        }

    def observation_for(self, agent_id: str) -> Dict[str, Any]:
        return {
            "version": "v1",
            "match": self.public_summary(),
            "agent_id": agent_id,
            "observation": self._engine.observation(agent_id=agent_id),
            "legal_actions": self._engine.legal_actions(agent_id=agent_id),
        }

    def replay_events(self) -> List[Dict[str, Any]]:
        replay_path = self._match_dir / "replay.jsonl"
        if not replay_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with replay_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def apply_action(self, agent_id: str, action: Dict[str, Any], chat: Optional[str]) -> Dict[str, Any]:
        if self._done:
            return {"ok": False, "error": "match_done", "match": self.public_summary()}

        t = int(time.time() * 1000)
        event: Dict[str, Any] = {
            "type": "act",
            "t": t,
            "turn": self._turn,
            "agent_id": agent_id,
            "action": action,
        }
        if chat:
            event["chat"] = chat

        ok, error, delta = self._engine.apply(agent_id=agent_id, action=action, chat=chat)
        event["ok"] = ok
        if error:
            event["error"] = error
        if delta is not None:
            event["delta"] = delta
        append_event(self._match_dir / "replay.jsonl", event)

        if ok:
            self._turn += 1

        status = self._engine.status(force=False)
        if status.get("done") and not self._done:
            self._done = True
            self._winner = status.get("winner")
            append_event(
                self._match_dir / "replay.jsonl",
                {"type": "match_done", "t": int(time.time() * 1000), "winner": self._winner},
            )
            if self._winner:
                update_leaderboard(self._match_dir.parent, game_id=self.game_id, winner=self._winner)

        if self._turn >= self.max_turns and not self._done:
            self._done = True
            status = self._engine.status(force=True)
            self._winner = status.get("winner")
            append_event(
                self._match_dir / "replay.jsonl",
                {"type": "match_timeout", "t": int(time.time() * 1000), "winner": self._winner},
            )
            if self._winner:
                update_leaderboard(self._match_dir.parent, game_id=self.game_id, winner=self._winner)

        return {"ok": ok, "error": error, "match": self.public_summary(), "delta": delta}


def create_runtime(
    match_id: str,
    game_id: str,
    ruleset_version: str,
    seed: int,
    players: List[str],
    max_turns: int,
    data_dir: Path,
) -> MatchRuntime:
    config = MatchConfig(
        match_id=match_id,
        game_id=game_id,
        ruleset_version=ruleset_version,
        seed=seed,
        players=players,
        max_turns=max_turns,
    )
    if game_id == "grid-arena":
        engine = GridArenaEngine(seed=seed, players=players)
    elif game_id == "mini-auction":
        engine = MiniAuctionEngine(seed=seed, players=players)
    else:
        raise ValueError("unknown_game")
    return MatchRuntime(config=config, engine=engine, data_dir=data_dir)

