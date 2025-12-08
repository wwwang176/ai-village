"""
遊戲 API 路由
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class NewGameRequest(BaseModel):
    player_name: str = "玩家"
    seed: Optional[int] = None


class GameStateResponse(BaseModel):
    day: int
    hour: int
    minute: int
    player: dict
    villagers_count: int


@router.post("/new")
async def new_game(request: Request, data: NewGameRequest):
    """建立新遊戲"""
    game_state = request.app.state.game_state
    game_state.initialize(player_name=data.player_name, seed=data.seed)
    
    return {
        "success": True,
        "message": "新遊戲已建立",
        "data": {
            "map": game_state.map_data,
            "player": game_state.player,
            "villagers": game_state.get_villagers_summary()
        }
    }


@router.get("/state")
async def get_game_state(request: Request):
    """取得遊戲狀態"""
    game_state = request.app.state.game_state
    return game_state.get_visible_state()


@router.post("/save")
async def save_game(request: Request):
    """儲存遊戲"""
    game_state = request.app.state.game_state
    save_path = game_state.save()
    return {"success": True, "path": save_path}


@router.post("/load")
async def load_game(request: Request, save_id: str):
    """讀取遊戲"""
    game_state = request.app.state.game_state
    success = game_state.load(save_id)
    return {"success": success}


@router.post("/tick")
async def game_tick(request: Request, delta_time: float = 0.1):
    """遊戲時間推進（由前端定期呼叫）"""
    game_state = request.app.state.game_state
    villager_ai = request.app.state.villager_ai
    
    # 更新遊戲時間
    game_state.update_time(delta_time)
    
    # 取得需要 AI 決策的村民
    pending_villagers = game_state.get_villagers_needing_decision()
    
    # 批次處理 AI 決策（限制每次最多處理 2 個）
    decisions = []
    for villager in pending_villagers[:2]:
        decision = await villager_ai.make_decision(villager, game_state)
        decisions.append({
            "villager_id": villager["id"],
            "decision": decision
        })
        game_state.apply_decision(villager["id"], decision)
    
    return {
        "time": game_state.get_time(),
        "decisions": decisions,
        "events": game_state.pop_events()
    }
