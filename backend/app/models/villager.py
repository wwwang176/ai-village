"""
村民類別定義
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .item import ItemStack
from .occupation import OccupationType


@dataclass
class Villager:
    """村民"""
    id: str
    name: str
    occupation: OccupationType
    
    # 背包（3 格）
    inventory: List[Optional[ItemStack]] = field(default_factory=lambda: [None, None, None])
    
    # 數值
    money: int = 50
    hunger: int = 0
    energy: int = 100
    social: int = 50
    happiness: int = 70
    health: int = 100
    
    # 位置與狀態
    x: float = 0
    y: float = 0
    state: str = "idle"
    
    # 個人資訊
    gender: str = "male"
    age: int = 25
    personality: str = ""
    
    # 喜好
    preferences: Dict[str, List[str]] = field(default_factory=dict)
    
    # 關係
    relationships: Dict[str, int] = field(default_factory=dict)
    
    # 記憶
    memories: List[Dict] = field(default_factory=list)
    
    # 住所
    home_building: Optional[str] = None
    
    def has_tool(self) -> bool:
        """檢查是否有工作需要的工具"""
        if not self.occupation.required_tool:
            return True
        return self.has_item(self.occupation.required_tool)
    
    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """檢查是否有足夠的物品"""
        total = sum(
            slot.quantity for slot in self.inventory
            if slot and slot.item_type.id == item_id
        )
        return total >= quantity
    
    def get_item_count(self, item_id: str) -> int:
        """取得物品數量"""
        return sum(
            slot.quantity for slot in self.inventory
            if slot and slot.item_type.id == item_id
        )
    
    def get_tool(self) -> Optional[ItemStack]:
        """取得工作工具"""
        tool_id = self.occupation.required_tool
        if not tool_id:
            return None
        for slot in self.inventory:
            if slot and slot.item_type.id == tool_id:
                return slot
        return None
    
    def add_item(self, item_stack: ItemStack) -> bool:
        """添加物品到背包"""
        # 先嘗試疊加到現有堆疊
        if not item_stack.is_tool():
            for i, slot in enumerate(self.inventory):
                if slot and slot.item_type.id == item_stack.item_type.id:
                    if slot.quantity + item_stack.quantity <= slot.item_type.stack_max:
                        slot.quantity += item_stack.quantity
                        return True
        
        # 找空格
        for i, slot in enumerate(self.inventory):
            if slot is None:
                item_stack.owner_id = self.id
                self.inventory[i] = item_stack
                return True
        
        return False  # 背包滿了
    
    def remove_item(self, item_id: str, quantity: int = 1) -> Optional[ItemStack]:
        """從背包移除物品"""
        for i, slot in enumerate(self.inventory):
            if slot and slot.item_type.id == item_id:
                if slot.quantity >= quantity:
                    slot.quantity -= quantity
                    if slot.quantity == 0:
                        removed = self.inventory[i]
                        self.inventory[i] = None
                        return removed
                    return ItemStack(
                        item_type=slot.item_type,
                        quantity=quantity,
                        owner_id=self.id
                    )
        return None
    
    def is_inventory_full(self) -> bool:
        """檢查背包是否滿了"""
        return all(slot is not None for slot in self.inventory)
    
    def get_empty_slot_count(self) -> int:
        """取得空格數量"""
        return sum(1 for slot in self.inventory if slot is None)
    
    def use_tool(self) -> bool:
        """使用工具（消耗耐久度）"""
        tool = self.get_tool()
        if tool:
            is_broken = tool.use_durability()
            if is_broken:
                # 工具損壞，從背包移除
                for i, slot in enumerate(self.inventory):
                    if slot is tool:
                        self.inventory[i] = None
                        return True
            return True
        return False
    
    def to_dict(self) -> dict:
        """轉換為字典（用於前端）"""
        return {
            "id": self.id,
            "name": self.name,
            "occupation": self.occupation.id,
            "occupation_name": self.occupation.name,
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "gender": self.gender,
            "age": self.age,
            "personality": self.personality,
            "money": self.money,
            "stats": {
                "energy": self.energy,
                "hunger": self.hunger,
                "social": self.social,
                "happiness": self.happiness,
                "health": self.health,
            },
            "inventory": [
                slot.to_dict() if slot else None
                for slot in self.inventory
            ],
            "preferences": self.preferences,
            "relationships": self.relationships,
            "home_building": self.home_building,
        }
