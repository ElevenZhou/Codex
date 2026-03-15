from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# Make `AgentGame/` importable so we can import `games/` from platform runtime.
AGENTGAME_DIR = Path(__file__).resolve().parents[2]
if str(AGENTGAME_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTGAME_DIR))

from app.runtime import MatchRuntime, create_runtime  # noqa: E402


DATA_DIR = AGENTGAME_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="AgentGame Platform", version="0.1.0")

app.mount("/viewer", StaticFiles(directory=str(AGENTGAME_DIR / "viewer"), html=True), name="viewer")
app.mount("/site", StaticFiles(directory=str(AGENTGAME_DIR / "site"), html=True), name="site")


RUNTIMES: Dict[str, MatchRuntime] = {}


class CreateMatchRequest(BaseModel):
    game_id: Literal["grid-arena", "mini-auction"]
    ruleset_version: str = Field(default="2026-03-15")
    seed: int = Field(default=0, ge=0)
    players: List[str] = Field(min_length=2)
    max_turns: int = Field(default=40, ge=1, le=500)


class CreateMatchResponse(BaseModel):
    match_id: str
    game_id: str
    ruleset_version: str
    seed: int
    players: List[str]
    created_at_ms: int


class ActRequest(BaseModel):
    agent_id: str
    action: Dict[str, Any]
    chat: Optional[str] = Field(default=None, max_length=400)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/matches", response_model=CreateMatchResponse)
def create_match(req: CreateMatchRequest) -> CreateMatchResponse:
    match_id = uuid.uuid4().hex
    runtime = create_runtime(
        match_id=match_id,
        game_id=req.game_id,
        ruleset_version=req.ruleset_version,
        seed=req.seed,
        players=req.players,
        max_turns=req.max_turns,
        data_dir=DATA_DIR,
    )
    RUNTIMES[match_id] = runtime
    return CreateMatchResponse(
        match_id=match_id,
        game_id=req.game_id,
        ruleset_version=req.ruleset_version,
        seed=req.seed,
        players=req.players,
        created_at_ms=runtime.created_at_ms,
    )


@app.get("/v1/matches/{match_id}")
def get_match(match_id: str) -> Dict[str, Any]:
    runtime = RUNTIMES.get(match_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="match_not_found")
    return runtime.public_summary()


@app.get("/v1/matches/{match_id}/observation/{agent_id}")
def get_observation(match_id: str, agent_id: str) -> Dict[str, Any]:
    runtime = RUNTIMES.get(match_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="match_not_found")
    if agent_id not in runtime.players:
        raise HTTPException(status_code=400, detail="unknown_agent")
    return runtime.observation_for(agent_id)


@app.post("/v1/matches/{match_id}/act")
def act(match_id: str, req: ActRequest) -> Dict[str, Any]:
    runtime = RUNTIMES.get(match_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="match_not_found")
    if req.agent_id not in runtime.players:
        raise HTTPException(status_code=400, detail="unknown_agent")
    return runtime.apply_action(agent_id=req.agent_id, action=req.action, chat=req.chat)


@app.get("/v1/matches/{match_id}/replay")
def get_replay(match_id: str) -> Dict[str, Any]:
    runtime = RUNTIMES.get(match_id)
    if runtime:
        return {"match": runtime.public_summary(), "events": runtime.replay_events()}

    replay_path = DATA_DIR / match_id / "replay.jsonl"
    meta_path = DATA_DIR / match_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="match_not_found")

    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    events: List[Dict[str, Any]] = []
    if replay_path.exists():
        with replay_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return {"match": meta, "events": events}


@app.get("/v1/leaderboards/{game_id}")
def leaderboard(game_id: str) -> Dict[str, Any]:
    leaderboard_path = DATA_DIR / "leaderboards.json"
    if not leaderboard_path.exists():
        return {"game_id": game_id, "rows": {}}
    with leaderboard_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return {"game_id": game_id, "rows": raw.get(game_id, {})}


@app.get("/")
def root() -> Dict[str, str]:
    return {"service": "AgentGame Platform", "health": "/health", "viewer": "/viewer/", "site": "/site/"}

