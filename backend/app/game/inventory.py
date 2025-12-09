"""
背包系統 - 管理村民背包、物品增刪、工具購買
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState

logger = logging.getLogger("Inventory")

# 工具列表
TOOLS = ["hoe", "pickaxe", "axe", "shears", "cleaver", "hammer", "saw", "scraper"]

# 職業需要的工具及資訊
OCCUPATION_TOOLS = {
    "farmer": {"id": "hoe", "name": "鋤頭", "price": 12, "durability": 100},
    "miner": {"id": "pickaxe", "name": "鶴嘴鋤", "price": 15, "durability": 80},
    "lumberjack": {"id": "axe", "name": "斧頭", "price": 14, "durability": 90},
    "shepherd": {"id": "shears", "name": "剪刀", "price": 10, "durability": 120},
    "butcher": {"id": "cleaver", "name": "屠刀", "price": 12, "durability": 100},
    "blacksmith": {"id": "hammer", "name": "錘子", "price": 15, "durability": 100},
    "carpenter": {"id": "saw", "name": "鋸子", "price": 14, "durability": 70},
    "tanner": {"id": "scraper", "name": "刮刀", "price": 10, "durability": 80},
    "tailor": {"id": "shears", "name": "剪刀", "price": 10, "durability": 120},
}


class InventorySystem:
    """背包系統管理器"""
    
    def __init__(self, game_state: "GameState"):
        self.game_state = game_state
    
    def count_item(self, inventory: list, item_id: str) -> int:
        """計算背包中某物品的數量"""
        total = 0
        for slot in inventory:
            if slot and slot.get("item_id") == item_id:
                total += slot.get("quantity", 0)
        return total
    
    def remove_item(self, villager: dict, item_id: str, quantity: int):
        """從背包移除物品"""
        inventory = villager.get("inventory", [None, None, None])
        remaining = quantity
        
        for i, slot in enumerate(inventory):
            if remaining <= 0:
                break
            if slot and slot.get("item_id") == item_id:
                slot_qty = slot.get("quantity", 0)
                if slot_qty <= remaining:
                    # 整個格子都移除
                    remaining -= slot_qty
                    villager["inventory"][i] = None
                else:
                    # 部分移除
                    slot["quantity"] = slot_qty - remaining
                    remaining = 0
    
    def add_item(self, villager: dict, item_id: str, quantity: int) -> str:
        """將物品加入村民背包，背包滿則放地上
        
        返回: "背包" 或 "地上"
        """
        inventory = villager.get("inventory", [None, None, None])
        remaining = quantity
        
        # 先嘗試疊加到現有堆疊
        for slot in inventory:
            if remaining <= 0:
                break
            if slot and slot.get("item_id") == item_id:
                current_qty = slot.get("quantity", 0)
                max_stack = 10  # 最大堆疊數
                can_add = max_stack - current_qty
                if can_add > 0:
                    add_qty = min(can_add, remaining)
                    slot["quantity"] = current_qty + add_qty
                    remaining -= add_qty
        
        # 再嘗試放入空格
        for i, slot in enumerate(inventory):
            if remaining <= 0:
                break
            if slot is None:
                add_qty = min(10, remaining)
                villager["inventory"][i] = {
                    "item_id": item_id,
                    "quantity": add_qty,
                    "durability": None,
                    "owner_id": villager["id"]
                }
                remaining -= add_qty
        
        # 還有剩餘，放到地上
        if remaining > 0:
            x = int(villager["x"])
            y = int(villager["y"])
            self.game_state.add_world_item(
                item_id=item_id,
                quantity=remaining,
                x=x,
                y=y,
                owner_id=villager["id"]
            )
            return "地上" if quantity == remaining else "背包+地上"
        
        return "背包"
    
    def buy_tool(self, villager: dict) -> Optional[dict]:
        """為村民購買工具
        
        返回工具資訊（包含 name, price）或 None
        """
        occupation = villager.get("occupation", "")
        tool_info = OCCUPATION_TOOLS.get(occupation)
        
        # 此職業不需要工具
        if not tool_info:
            return None
        
        # 檢查錢是否足夠
        money = villager.get("money", 0)
        if money < tool_info["price"]:
            return None
        
        # 檢查背包是否有空位
        inventory = villager.get("inventory", [None, None, None])
        empty_slot = -1
        for i, slot in enumerate(inventory):
            if slot is None:
                empty_slot = i
                break
        
        if empty_slot == -1:
            return None  # 背包滿了
        
        # 扣錢
        villager["money"] = money - tool_info["price"]
        
        # 加入工具到背包
        villager["inventory"][empty_slot] = {
            "item_id": tool_info["id"],
            "quantity": 1,
            "durability": tool_info["durability"],
            "owner_id": villager["id"]
        }
        
        return {"name": tool_info["name"], "price": tool_info["price"]}
    
    def drop_one_non_tool_item(self, villager: dict) -> Optional[dict]:
        """放下背包中的一格非工具物品到地上
        
        返回被放下的物品資訊，或 None
        """
        inventory = villager.get("inventory", [None, None, None])
        
        # 找到第一個非工具的物品
        for i, slot in enumerate(inventory):
            if slot is None:
                continue
            item_id = slot.get("item_id")
            if item_id not in TOOLS:
                # 放到地上
                x, y = int(villager["x"]), int(villager["y"])
                self.game_state.add_world_item(
                    item_id=item_id,
                    x=x, y=y,
                    quantity=slot.get("quantity", 1),
                    owner_id=villager["id"]  # 標記擁有者
                )
                
                # 從背包移除
                dropped_item = {"item_id": item_id, "quantity": slot.get("quantity", 1)}
                villager["inventory"][i] = None
                return dropped_item
        
        return None
