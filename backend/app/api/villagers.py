"""
村民 API 路由
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class InteractRequest(BaseModel):
    villager_id: str
    action: str  # greet, chat, ask_info, give_gift


@router.get("/")
async def get_all_villagers(request: Request):
    """取得所有村民資料"""
    game_state = request.app.state.game_state
    return {
        "villagers": game_state.get_villagers_summary()
    }


@router.get("/{villager_id}")
async def get_villager(request: Request, villager_id: str):
    """取得單一村民詳細資料"""
    game_state = request.app.state.game_state
    villager = game_state.get_villager(villager_id)
    
    if not villager:
        return {"error": "Villager not found"}
    
    return {"villager": villager}


@router.get("/{villager_id}/relationships")
async def get_villager_relationships(request: Request, villager_id: str):
    """取得村民的關係網絡"""
    game_state = request.app.state.game_state
    villager = game_state.get_villager(villager_id)
    
    if not villager:
        return {"error": "Villager not found"}
    
    return {"relationships": villager.get("relationships", {})}


@router.post("/interact")
async def interact_with_villager(request: Request, data: InteractRequest):
    """與村民互動"""
    game_state = request.app.state.game_state
    villager_ai = request.app.state.villager_ai
    
    villager = game_state.get_villager(data.villager_id)
    if not villager:
        return {"error": "Villager not found"}
    
    player = game_state.player
    
    # 使用 AI 生成對話
    dialogue = await villager_ai.generate_dialogue(
        villager=villager,
        player=player,
        action=data.action,
        game_state=game_state
    )
    
    # 更新關係
    relationship_change = calculate_relationship_change(data.action)
    game_state.update_relationship("player", data.villager_id, relationship_change)
    
    # 記錄互動記憶
    game_state.add_memory(data.villager_id, {
        "event": f"與玩家{get_action_name(data.action)}",
        "sentiment": "positive" if relationship_change["affection"] > 0 else "neutral"
    })
    
    return {
        "success": True,
        "dialogue": dialogue,
        "relationship_change": relationship_change
    }


def calculate_relationship_change(action: str) -> dict:
    """計算關係變化"""
    changes = {
        "greet": {"affection": 1, "familiarity": 2, "trust": 0},
        "chat": {"affection": 2, "familiarity": 5, "trust": 1},
        "ask_info": {"affection": 0, "familiarity": 3, "trust": 0},
        "give_gift": {"affection": 10, "familiarity": 3, "trust": 2},
    }
    return changes.get(action, {"affection": 0, "familiarity": 1, "trust": 0})


def get_action_name(action: str) -> str:
    """取得動作名稱"""
    names = {
        "greet": "打招呼",
        "chat": "聊天",
        "ask_info": "打聽消息",
        "give_gift": "送禮物",
    }
    return names.get(action, action)
