"""
目標解析器 - 根據行為決定村民的目標位置
"""

import random
import logging
from typing import Optional, Tuple, List, TYPE_CHECKING

logger = logging.getLogger(__name__)

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
            "go_workplace": lambda v: self._get_work_target(v),  # 多輪決策別名
            "go_home": lambda v: self._get_bed_target(v),
            "go_plaza": lambda v: self._get_building_target("plaza"),
            "go_bar": lambda v: self._get_building_target("tavern"),
            "go_blacksmith": lambda v: self._get_villager_by_occupation("blacksmith"),
            "eat": lambda v: self._get_eat_target(v),
            "rest": lambda v: self._get_home_target(v),
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
        return self._get_building_target("plaza")
    
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
    
    def _get_furniture_interact_pos(self, furniture: dict) -> Optional[Tuple[int, int]]:
        """取得家具的互動位置（排除不可行走位置後隨機選擇）"""
        offsets = furniture.get("interact_offsets", [(0, 0)])
        fx, fy = int(furniture["x"]), int(furniture["y"])
        
        # 過濾出可行走的位置
        walkable_positions = []
        for offset in offsets:
            x, y = fx + offset[0], fy + offset[1]
            walkable = self.game_state.pathfinder.is_walkable(x, y) if self.game_state.pathfinder else False
            logger.info(f"🏠 家具互動點檢查: offset={offset}, pos=({x},{y}), walkable={walkable}")
            if walkable:
                walkable_positions.append((x, y))
        
        # 如果有可行走的位置，隨機選一個
        if walkable_positions:
            chosen = random.choice(walkable_positions)
            logger.info(f"🏠 選擇互動點: {chosen} (從 {walkable_positions} 中)")
            return chosen
        
        # 都不可行走，fallback 到家具本身位置
        logger.warning(f"🏠 所有互動點都不可行走，fallback 到家具位置: ({fx}, {fy})")
        return (fx, fy)
    
    def _get_bed_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得床的位置"""
        bed = self.game_state.get_bed_by_residence(villager.get("id"))
        if bed:
            return self._get_furniture_interact_pos(bed)
        return self._get_home_target(villager)
    
    def _get_eat_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得吃東西的地點（家裡灶台）"""
        stove = self.game_state.get_stove_by_residence(villager.get("id"))
        if stove:
            return self._get_furniture_interact_pos(stove)
        return self._get_home_target(villager)
    
    def _get_villager_by_occupation(self, occupation: str) -> Optional[Tuple[int, int]]:
        """取得特定職業的村民位置"""
        for v in self.game_state.villagers.values():
            if v.get("occupation") == occupation:
                return (int(v["x"]), int(v["y"]))
        return None
    
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
        
        return (self._get_building_target("plaza"), None)
    
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
