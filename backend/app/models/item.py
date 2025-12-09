"""
物品類別定義
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ItemType:
    """物品類型定義"""
    id: str                    # grain, bread, hoe...
    name: str                  # 穀物, 麵包, 鋤頭...
    icon: str                  # 🌾, 🍞, ⛏️...
    category: str              # material, food, tool
    stack_max: int = 10        # 最大堆疊數
    durability_max: Optional[int] = None  # 工具才有
    price: int = 0             # 價格
    hunger_restore: int = 0    # 食物恢復飢餓值
    
    def is_tool(self) -> bool:
        return self.category == "tool"
    
    def is_food(self) -> bool:
        return self.category == "food"
    
    def is_material(self) -> bool:
        return self.category == "material"


@dataclass
class ItemStack:
    """物品堆疊（背包/地上的一格）"""
    item_type: ItemType        # 物品類型
    quantity: int = 1          # 數量
    durability: Optional[int] = None  # 當前耐久度（工具）
    owner_id: Optional[str] = None    # 擁有者 ID
    x: Optional[int] = None    # 地上位置 X
    y: Optional[int] = None    # 地上位置 Y
    
    def __post_init__(self):
        # 工具自動設定耐久度
        if self.item_type.is_tool() and self.durability is None:
            self.durability = self.item_type.durability_max
    
    def is_tool(self) -> bool:
        return self.item_type.is_tool()
    
    def is_owned_by(self, villager_id: str) -> bool:
        """檢查是否屬於某村民（或無主）"""
        return self.owner_id == villager_id or self.owner_id is None
    
    def can_pickup(self, villager_id: str) -> bool:
        """檢查村民是否可以撿起此物品"""
        return self.is_owned_by(villager_id)
    
    def use_durability(self, amount: int = 5) -> bool:
        """消耗耐久度，返回是否損壞"""
        if self.durability is not None:
            self.durability -= amount
            return self.durability <= 0
        return False
    
    def get_durability_percent(self) -> Optional[int]:
        """取得耐久度百分比"""
        if self.durability is not None and self.item_type.durability_max:
            return int(self.durability / self.item_type.durability_max * 100)
        return None
    
    def can_stack_with(self, other: 'ItemStack') -> bool:
        """檢查是否可以與另一個堆疊合併"""
        if self.item_type.id != other.item_type.id:
            return False
        if self.is_tool():
            return False  # 工具不可堆疊
        return self.quantity + other.quantity <= self.item_type.stack_max
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "item_id": self.item_type.id,
            "name": self.item_type.name,
            "icon": self.item_type.icon,
            "quantity": self.quantity,
            "durability": self.durability,
            "durability_max": self.item_type.durability_max,
            "owner_id": self.owner_id,
            "x": self.x,
            "y": self.y,
        }
