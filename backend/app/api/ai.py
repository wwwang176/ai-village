"""
AI API 路由 - GPT 相關
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class DecisionRequest(BaseModel):
    villager_id: str


class DialogueRequest(BaseModel):
    villager_id: str
    context: str
    player_message: Optional[str] = None


@router.post("/decision")
async def request_ai_decision(request: Request, data: DecisionRequest):
    """請求 AI 為村民做決策"""
    game_state = request.app.state.game_state
    villager_ai = request.app.state.villager_ai
    
    villager = game_state.get_villager(data.villager_id)
    if not villager:
        return {"error": "Villager not found"}
    
    decision = await villager_ai.make_decision(villager, game_state)
    
    return {
        "villager_id": data.villager_id,
        "decision": decision
    }


@router.post("/dialogue")
async def generate_dialogue(request: Request, data: DialogueRequest):
    """生成 AI 對話"""
    game_state = request.app.state.game_state
    villager_ai = request.app.state.villager_ai
    
    villager = game_state.get_villager(data.villager_id)
    if not villager:
        return {"error": "Villager not found"}
    
    dialogue = await villager_ai.generate_dialogue(
        villager=villager,
        player=game_state.player,
        action="chat",
        game_state=game_state,
        player_message=data.player_message
    )
    
    return {
        "villager_id": data.villager_id,
        "dialogue": dialogue
    }


@router.post("/social-encounter")
async def handle_social_encounter(request: Request, villager_a_id: str, villager_b_id: str):
    """處理兩個村民相遇"""
    game_state = request.app.state.game_state
    villager_ai = request.app.state.villager_ai
    
    villager_a = game_state.get_villager(villager_a_id)
    villager_b = game_state.get_villager(villager_b_id)
    
    if not villager_a or not villager_b:
        return {"error": "Villager not found"}
    
    encounter = await villager_ai.generate_encounter(villager_a, villager_b, game_state)
    
    return {
        "will_interact": encounter["will_interact"],
        "dialogue": encounter.get("dialogue", []),
        "relationship_changes": encounter.get("relationship_changes", {})
    }
