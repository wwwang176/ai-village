"""
羊系統 - 管理羊的行為、繁殖、剪毛、買賣
"""

import random
import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState

logger = logging.getLogger("SheepSystem")


class SheepSystem:
    """羊系統管理器"""
    
    def __init__(self, game_state: "GameState"):
        self.game_state = game_state
    
    def update(self, delta_time: float, current_time: float):
        """更新所有羊的狀態"""
        for sheep in list(self.game_state.sheep.values()):
            # 1. 羊在牧場內隨機移動（每 5 秒移動一次）
            if current_time - sheep.get("last_move_time", 0) > 5:
                sheep["last_move_time"] = current_time
                self.move_randomly(sheep)
            
            # 2. 小羊成長（每遊戲天檢查一次）
            if not sheep["is_adult"]:
                # 簡化：每 60 秒遊戲時間 = 1 天
                sheep["age_days"] += delta_time / 60
                if sheep["age_days"] >= 5:
                    sheep["is_adult"] = True
                    logger.info(f"🐑 小羊 {sheep['id']} 長大成成羊了！")
            
            # 3. 成羊長毛（每 3 天可以剪一次）
            if sheep["is_adult"] and not sheep["wool_ready"]:
                # 簡化：每 180 秒遊戲時間 = 可以剪毛
                sheep["wool_grow_time"] = sheep.get("wool_grow_time", 0) + delta_time
                if sheep["wool_grow_time"] >= 180:
                    sheep["wool_ready"] = True
                    sheep["wool_grow_time"] = 0
                    logger.info(f"🧶 羊 {sheep['id']} 的毛長好了，可以剪毛")
            
            # 4. 繁殖檢查（每 30 秒檢查一次）
            if current_time - sheep.get("last_breed_check", 0) > 30:
                sheep["last_breed_check"] = current_time
                self.check_breeding(sheep)
    
    def move_randomly(self, sheep: dict):
        """讓羊在牧場內隨機移動"""
        pasture = self.game_state.get_building_by_id(sheep["pasture_id"])
        if not pasture:
            return
        
        # 隨機移動 1-2 格
        dx = random.randint(-2, 2)
        dy = random.randint(-2, 2)
        
        new_x = sheep["x"] + dx
        new_y = sheep["y"] + dy
        
        # 確保在牧場範圍內
        min_x = pasture["x"] + 1
        max_x = pasture["x"] + pasture["width"] - 2
        min_y = pasture["y"] + 1
        max_y = pasture["y"] + pasture["height"] - 2
        
        sheep["x"] = max(min_x, min(max_x, new_x))
        sheep["y"] = max(min_y, min(max_y, new_y))
    
    def check_breeding(self, sheep: dict):
        """檢查羊是否可以繁殖"""
        if not sheep["is_adult"]:
            return
        
        # 取得同牧場的成羊數量
        pasture_sheep = self.game_state.get_sheep_in_pasture(sheep["pasture_id"])
        adult_sheep = [s for s in pasture_sheep if s["is_adult"]]
        
        # 需要至少 2 隻成羊，且數量未達上限（8隻）
        if len(adult_sheep) >= 2 and len(pasture_sheep) < 8:
            # 10% 機率生小羊
            if random.random() < 0.1:
                new_sheep = self.game_state.add_sheep(
                    pasture_id=sheep["pasture_id"],
                    owner_id=sheep["owner_id"],
                    is_adult=False
                )
                if new_sheep:
                    logger.info(f"🐑 新生了一隻小羊！牧場現有 {len(pasture_sheep) + 1} 隻羊")
    
    # ==================== 牧羊人工作任務 ====================
    
    def create_shepherd_work_tasks(self, villager: dict) -> List[dict]:
        """建立牧羊人的工作任務（剪毛）"""
        tasks = []
        
        # 找到可以剪毛的羊
        sheep_ready = self.game_state.get_sheep_ready_for_shearing(villager["id"])
        
        if not sheep_ready:
            return tasks
        
        # 選擇最近的一隻羊
        sheep = min(sheep_ready, key=lambda s: 
            (s["x"] - villager["x"])**2 + (s["y"] - villager["y"])**2
        )
        
        # 移動到羊的位置
        sheep_pos = (sheep["x"], sheep["y"])
        current = (villager["x"], villager["y"])
        dx = sheep_pos[0] - current[0]
        dy = sheep_pos[1] - current[1]
        dist = (dx**2 + dy**2) ** 0.5
        
        if dist > 1.5:
            tasks.append({"type": "move", "target": sheep_pos})
        
        # 剪毛任務
        tasks.append({
            "type": "shear_sheep",
            "sheep_id": sheep["id"],
            "duration": 5
        })
        
        logger.info(f"🐑 {villager['name']} 準備去剪羊 {sheep['id']} 的毛")
        return tasks
    
    # ==================== 屠夫工作任務 ====================
    
    def create_butcher_work_tasks(self, villager: dict) -> List[dict]:
        """建立屠夫的工作任務（買羊、殺羊）"""
        tasks = []
        
        # 檢查屠夫是否已經擁有羊（買過但還沒殺）
        owned_sheep = self.game_state.get_sheep_by_owner(villager["id"])
        
        # 過濾出成羊
        adult_sheep = [s for s in owned_sheep if s.get("is_adult")]
        
        if adult_sheep:
            # 有成羊，去殺羊（slaughter_sheep 任務會自動處理移動）
            sheep = adult_sheep[0]
            
            tasks.append({
                "type": "slaughter_sheep",
                "sheep_id": sheep["id"],
                "duration": 6
            })
            logger.info(f"🔪 {villager['name']} 準備去宰殺羊 {sheep['id']}")
        else:
            # 沒有羊，去找牧羊人買羊
            logger.info(f"🔪 {villager['name']} 沒有羊，嘗試向牧羊人買羊")
            buy_task = self.create_buy_sheep_task(villager)
            if buy_task:
                tasks.extend(buy_task)
            else:
                logger.info(f"🔪 {villager['name']} 無法買羊（牧羊人沒有足夠的羊）")
        
        return tasks
    
    def create_buy_sheep_task(self, buyer: dict) -> List[dict]:
        """建立購買活羊的任務"""
        tasks = []
        
        # 找牧羊人
        shepherd = None
        for v in self.game_state.villagers.values():
            if v.get("occupation") == "shepherd" and v["id"] != buyer["id"]:
                shepherd = v
                break
        
        if not shepherd:
            logger.info(f"🐑 {buyer['name']} 找不到牧羊人")
            return tasks
        
        # 檢查牧羊人是否有可賣的成羊（至少留 2 隻用於繁殖）
        shepherd_sheep = self.game_state.get_sheep_by_owner(shepherd["id"])
        adult_sheep = [s for s in shepherd_sheep if s["is_adult"]]
        
        logger.info(f"🐑 牧羊人 {shepherd['name']} 擁有 {len(shepherd_sheep)} 隻羊，{len(adult_sheep)} 隻成羊")
        
        if len(adult_sheep) <= 2:
            logger.info(f"🐑 牧羊人 {shepherd['name']} 羊不夠（需 > 2 隻成羊），無法出售")
            return tasks
        
        # 走到牧羊人位置（動態追蹤）
        shepherd_pos = (shepherd["x"], shepherd["y"])
        tasks.append({
            "type": "move_to_villager",
            "target": shepherd_pos,
            "target_villager_id": shepherd["id"]
        })
        
        # 購買活羊任務
        tasks.append({
            "type": "buy_sheep",
            "seller_id": shepherd["id"],
            "duration": 3
        })
        
        logger.info(f"🐑 {buyer['name']} 準備向 {shepherd['name']} 購買活羊")
        return tasks
    
    # ==================== 執行任務 ====================
    
    def execute_shear(self, villager: dict, sheep_id: str, use_tool_func) -> dict:
        """執行剪羊毛
        
        返回: {"success": bool, "quantity": int, "location": str, "reason": str}
        """
        sheep = self.game_state.sheep.get(sheep_id)
        
        if not sheep:
            return {"success": False, "reason": "找不到這隻羊"}
        
        if not sheep["wool_ready"]:
            return {"success": False, "reason": "這隻羊還沒長好毛"}
        
        if sheep["owner_id"] != villager["id"]:
            return {"success": False, "reason": "這不是你的羊"}
        
        # 消耗工具耐久度
        tool_result = use_tool_func(villager)
        if tool_result == "no_tool":
            return {"success": False, "reason": "沒有剪刀"}
        
        # 剪毛成功，羊毛狀態重置
        sheep["wool_ready"] = False
        sheep["wool_grow_time"] = 0
        
        # 產出羊毛（由外部處理加入背包）
        wool_qty = 2
        
        # 牧羊人獲得收入
        villager["money"] = villager.get("money", 0) + 3
        
        return {"success": True, "quantity": wool_qty, "wool_qty": wool_qty}
    
    def execute_buy(self, buyer: dict, seller_id: str) -> dict:
        """執行購買活羊
        
        返回: {"success": bool, "price": int, "seller_name": str, "reason": str}
        """
        seller = self.game_state.get_villager(seller_id)
        if not seller:
            return {"success": False, "reason": "找不到賣家"}
        
        SHEEP_PRICE = 10  # 平衡後：屠夫 L2 → $100/分
        
        # 檢查買家錢夠不夠
        if buyer.get("money", 0) < SHEEP_PRICE:
            return {"success": False, "reason": "錢不夠"}
        
        # 檢查賣家（牧羊人）有沒有羊可賣
        seller_sheep = self.game_state.get_sheep_by_owner(seller_id)
        adult_sheep = [s for s in seller_sheep if s["is_adult"]]
        
        if len(adult_sheep) <= 2:
            return {"success": False, "reason": "賣家羊不夠"}
        
        # 選一隻羊轉移給買家
        sheep_to_sell = adult_sheep[0]
        sheep_to_sell["owner_id"] = buyer["id"]
        
        # 交易金錢
        buyer["money"] -= SHEEP_PRICE
        seller["money"] = seller.get("money", 0) + SHEEP_PRICE
        
        return {
            "success": True,
            "price": SHEEP_PRICE,
            "seller_name": seller["name"],
            "sheep_id": sheep_to_sell["id"]
        }
    
    def execute_slaughter(self, villager: dict, sheep_id: str, use_tool_func) -> dict:
        """執行宰殺羊
        
        返回: {"success": bool, "meat_qty": int, "hide_qty": int, "reason": str}
        """
        sheep = self.game_state.sheep.get(sheep_id)
        
        if not sheep:
            return {"success": False, "reason": "找不到這隻羊"}
        
        if sheep["owner_id"] != villager["id"]:
            return {"success": False, "reason": "這不是你的羊"}
        
        if not sheep["is_adult"]:
            return {"success": False, "reason": "不能殺小羊"}
        
        # 消耗工具耐久度
        tool_result = use_tool_func(villager)
        if tool_result == "no_tool":
            return {"success": False, "reason": "沒有屠刀"}
        
        # 移除羊
        self.game_state.remove_sheep(sheep_id)
        
        # 產出數量（由外部處理加入背包）
        meat_qty = 3
        hide_qty = 1
        
        return {
            "success": True,
            "meat_qty": meat_qty,
            "hide_qty": hide_qty
        }
