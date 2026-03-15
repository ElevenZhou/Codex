from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def append_event(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def update_leaderboard(data_dir: Path, game_id: str, winner: str) -> None:
    leaderboard_path = data_dir / "leaderboards.json"
    raw = load_json(leaderboard_path, default={})
    game_rows = raw.get(game_id, {})
    game_rows[winner] = int(game_rows.get(winner, 0)) + 1
    raw[game_id] = game_rows
    save_json(leaderboard_path, raw)

