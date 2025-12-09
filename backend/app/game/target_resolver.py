"""
目標解析器 - 根據行為決定村民的目標位置
"""

import random
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState


class TargetResolver:
    """目標位置解析器"""
    
    def __init__(self, game_state: "GameState"):
        self.game_state = game_state
    
    def resolve(
        self, 
        villager: dict, 
        action: str
    ) -> Optional[Tuple[int, int]]:
        """
        根據 action 決定目標位置
        
        Args:
            villager: 村民資料
            action: AI 決定的行為
            
        Returns:
            目標座標 (x, y) 或 None
        """
        action_targets = {
            "go_work": lambda v: self._get_work_target(v),
            "go_home": lambda v: self._get_home_target(v),
            "go_market": lambda v: self._get_building_target("market"),
            "go_blacksmith": lambda v: self._get_building_target("blacksmith"),
            "eat": lambda v: self._get_eat_target(v),
            "rest": lambda v: self._get_home_target(v),
            "sleep": lambda v: self._get_home_target(v),
            "socialize": lambda v: self._get_social_target(v),
            "wander": lambda v: self._get_wander_target(v),
        }
        
        resolver = action_targets.get(action)
        if resolver:
            return resolver(villager)
        
        # 未知行為，隨機閒逛
        return self._get_wander_target(villager)
    
    def _get_work_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得工作地點"""
        workplace_id = villager.get("workplace")
        if workplace_id:
            building = self.game_state.get_building_by_id(workplace_id)
            if building:
                return self.game_state.get_building_door(building)
        return self._get_building_target("market")
    
    def _get_home_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得住所"""
        residence_id = villager.get("residence")
        if residence_id:
            building = self.game_state.get_building_by_id(residence_id)
            if building:
                return self.game_state.get_building_door(building)
        house = self.game_state.get_random_building_of_type("house")
        if house:
            return self.game_state.get_building_door(house)
        return None
    
    def _get_building_target(self, building_type: str) -> Optional[Tuple[int, int]]:
        """取得特定類型建築物"""
        building = self.game_state.get_building_by_type(building_type)
        if building:
            return self.game_state.get_building_door(building)
        return None
    
    def _get_eat_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得吃東西的地點（酒館或家）"""
        target = self._get_building_target("tavern")
        if target:
            return target
        return self._get_home_target(villager)
    
    def _get_social_target(self, villager: dict) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        """取得社交目標 - 找附近的村民聊天
        回傳: (座標, 目標村民ID) 或 (座標, None)
        """
        current_x = villager["x"]
        current_y = villager["y"]
        
        excluded_states = ["talking", "waiting_social"]
        
        candidates = []
        for other in self.game_state.villagers.values():
            if other["id"] == villager["id"]:
                continue
            if other.get("state") in excluded_states:
                continue
            
            dx = other["x"] - current_x
            dy = other["y"] - current_y
            dist = (dx**2 + dy**2) ** 0.5
            
            if dist < 20:
                rel = villager.get("relationships", {}).get(other["id"], {})
                familiarity = rel.get("familiarity", 0)
                affection = rel.get("affection", 0)
                priority = familiarity + affection - dist
                candidates.append((other, dist, priority))
        
        if candidates:
            candidates.sort(key=lambda x: x[2], reverse=True)
            target_villager = candidates[0][0]
            return ((target_villager["x"], target_villager["y"]), target_villager["id"])
        
        return (self._get_building_target("market"), None)
    
    def _get_wander_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """隨機閒逛目標"""
        current_x = int(villager["x"])
        current_y = int(villager["y"])
        
        for _ in range(10):
            dx = random.randint(-8, 8)
            dy = random.randint(-8, 8)
            target_x = max(1, min(self.game_state.map_data["width"] - 2, current_x + dx))
            target_y = max(1, min(self.game_state.map_data["height"] - 2, current_y + dy))
            
            if self.game_state.pathfinder and self.game_state.pathfinder.is_walkable(target_x, target_y):
                return (target_x, target_y)
        
        return None
