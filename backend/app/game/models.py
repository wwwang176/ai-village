"""
遊戲資料模型 - 使用 dataclass 定義核心資料結構
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple


# ==================== 村民相關 ====================

@dataclass
class VillagerStats:
    """村民狀態"""
    energy: int = 100      # 體力 (0-100)
    hunger: int = 0        # 飢餓 (0-100, 越高越餓)
    social: int = 50       # 社交 (0-100)
    happiness: int = 70    # 幸福度 (0-100)
    health: int = 100      # 健康 (0-100)
    
    def to_dict(self) -> dict:
        return {
            "energy": self.energy,
            "hunger": self.hunger,
            "social": self.social,
            "happiness": self.happiness,
            "health": self.health
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VillagerStats":
        return cls(
            energy=data.get("energy", 100),
            hunger=data.get("hunger", 0),
            social=data.get("social", 50),
            happiness=data.get("happiness", 70),
            health=data.get("health", 100)
        )


@dataclass
class Relationship:
    """村民關係"""
    target_id: str
    affection: int = 0       # 好感度 (-100 ~ 100)
    familiarity: int = 0     # 熟悉度 (0-100)
    type: str = "陌生人"      # 關係類型
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "affection": self.affection,
            "familiarity": self.familiarity,
            "type": self.type,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, target_id: str, data: dict) -> "Relationship":
        return cls(
            target_id=target_id,
            affection=data.get("affection", 0),
            familiarity=data.get("familiarity", 0),
            type=data.get("type", "陌生人"),
            tags=data.get("tags", [])
        )


# ==================== 任務相關 ====================

@dataclass
class Task:
    """村民任務"""
    type: str                                    # 任務類型
    duration: float = 0                          # 持續時間（秒）
    elapsed: float = 0                           # 已過時間（秒）
    target: Optional[Tuple[int, int]] = None     # 目標座標
    target_villager_id: Optional[str] = None     # 目標村民 ID
    seller_id: Optional[str] = None              # 賣家 ID
    supplier_id: Optional[str] = None            # 供應商 ID
    merchant_id: Optional[str] = None             # 商人 ID（賣東西用）
    material: Optional[str] = None               # 原料名稱
    item: Optional[str] = None                   # 物品名稱（賣東西用）
    food_item: Optional[str] = None              # 食物名稱
    sheep_id: Optional[str] = None               # 羊 ID
    item_id: Optional[str] = None                # 地上物品 ID（撿起用）
    quantity: int = 1                            # 交易數量
    
    def to_dict(self) -> dict:
        result = {"type": self.type}
        if self.duration:
            result["duration"] = self.duration
        if self.elapsed:
            result["elapsed"] = self.elapsed
        if self.target:
            result["target"] = self.target
        if self.target_villager_id:
            result["target_villager_id"] = self.target_villager_id
        if self.seller_id:
            result["seller_id"] = self.seller_id
        if self.supplier_id:
            result["supplier_id"] = self.supplier_id
        if self.merchant_id:
            result["merchant_id"] = self.merchant_id
        if self.item:
            result["item"] = self.item
        if self.material:
            result["material"] = self.material
        if self.food_item:
            result["food_item"] = self.food_item
        if self.sheep_id:
            result["sheep_id"] = self.sheep_id
        if self.item_id:
            result["item_id"] = self.item_id
        if self.quantity != 1:
            result["quantity"] = self.quantity
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            type=data.get("type", "idle"),
            duration=data.get("duration", 0),
            elapsed=data.get("elapsed", 0),
            target=tuple(data["target"]) if data.get("target") else None,
            target_villager_id=data.get("target_villager_id"),
            seller_id=data.get("seller_id"),
            supplier_id=data.get("supplier_id"),
            merchant_id=data.get("merchant_id"),
            material=data.get("material"),
            item=data.get("item"),
            food_item=data.get("food_item"),
            sheep_id=data.get("sheep_id"),
            item_id=data.get("item_id"),
            quantity=data.get("quantity", 1)
        )


# ==================== 時間相關 ====================

@dataclass
class GameTime:
    """遊戲時間"""
    day: int = 1
    hour: int = 8
    minute: float = 0
    time_scale: int = 60  # 1 現實秒 = 60 遊戲秒
    
    def update(self, delta_time: float):
        """更新時間"""
        game_seconds = delta_time * self.time_scale
        self.minute += game_seconds / 60
        
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1
    
    @property
    def total_hours(self) -> int:
        """計算從第 1 天開始的總小時數"""
        return (self.day - 1) * 24 + self.hour
    
    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "hour": self.hour,
            "minute": int(self.minute)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GameTime":
        return cls(
            day=data.get("day", 1),
            hour=data.get("hour", 8),
            minute=data.get("minute", 0),
            time_scale=data.get("time_scale", 60)
        )


# ==================== 羊相關 ====================

@dataclass
class Sheep:
    """羊"""
    id: str
    x: float
    y: float
    owner_id: Optional[str] = None
    pasture_id: Optional[str] = None
    age_days: float = 0
    is_adult: bool = False
    wool_ready: bool = False
    wool_grow_time: float = 0
    last_move_time: float = 0
    last_breed_check: float = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "owner_id": self.owner_id,
            "pasture_id": self.pasture_id,
            "age_days": self.age_days,
            "is_adult": self.is_adult,
            "wool_ready": self.wool_ready,
            "wool_grow_time": self.wool_grow_time,
            "last_move_time": self.last_move_time,
            "last_breed_check": self.last_breed_check
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Sheep":
        return cls(
            id=data["id"],
            x=data["x"],
            y=data["y"],
            owner_id=data.get("owner_id"),
            pasture_id=data.get("pasture_id"),
            age_days=data.get("age_days", 0),
            is_adult=data.get("is_adult", False),
            wool_ready=data.get("wool_ready", False),
            wool_grow_time=data.get("wool_grow_time", 0),
            last_move_time=data.get("last_move_time", 0),
            last_breed_check=data.get("last_breed_check", 0)
        )


# ==================== 家具/可交互物件 ====================

# 家具互動座標預設值
FURNITURE_INTERACT_OFFSETS = {
    "bed": [(0, 0)],              # 站在床上
    "stove": [(0, 1), (-1, 0), (1, 0)],  # 站在灶台前面或左右
}

@dataclass
class Furniture:
    """家具/可交互地圖物件"""
    id: str
    type: str              # "stove", "bed"
    x: float
    y: float
    building_id: str       # 所屬建築 ID
    interact_offsets: List[Tuple[int, int]] = None  # 互動座標偏移
    in_use: bool = False   # 是否正在使用
    user_id: Optional[str] = None  # 誰在使用
    
    def __post_init__(self):
        if self.interact_offsets is None:
            self.interact_offsets = FURNITURE_INTERACT_OFFSETS.get(self.type, [(0, 0)])
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "building_id": self.building_id,
            "interact_offsets": self.interact_offsets,
            "in_use": self.in_use,
            "user_id": self.user_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Furniture":
        return cls(
            id=data["id"],
            type=data["type"],
            x=data["x"],
            y=data["y"],
            building_id=data["building_id"],
            interact_offsets=data.get("interact_offsets"),
            in_use=data.get("in_use", False),
            user_id=data.get("user_id")
        )


# ==================== 交易相關 ====================

@dataclass
class PendingTrade:
    """待處理的原料交易"""
    material: str
    supplier_id: str
    quantity: int = 2
    
    def to_dict(self) -> dict:
        return {
            "material": self.material,
            "supplier_id": self.supplier_id,
            "quantity": self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PendingTrade":
        return cls(
            material=data["material"],
            supplier_id=data["supplier_id"],
            quantity=data.get("quantity", 2)
        )


@dataclass
class PendingFoodTrade:
    """待處理的食物交易"""
    food_item: str
    seller_id: str
    quantity: int = 2
    
    def to_dict(self) -> dict:
        return {
            "food_item": self.food_item,
            "seller_id": self.seller_id,
            "quantity": self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PendingFoodTrade":
        return cls(
            food_item=data["food_item"],
            seller_id=data["seller_id"],
            quantity=data.get("quantity", 2)
        )


# ==================== 物品相關 ====================

@dataclass
class InventoryItem:
    """背包物品"""
    item_id: str
    quantity: int = 1
    durability: Optional[int] = None  # 工具耐久度
    owner_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = {
            "item_id": self.item_id,
            "quantity": self.quantity
        }
        if self.durability is not None:
            result["durability"] = self.durability
        if self.owner_id:
            result["owner_id"] = self.owner_id
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "InventoryItem":
        return cls(
            item_id=data["item_id"],
            quantity=data.get("quantity", 1),
            durability=data.get("durability"),
            owner_id=data.get("owner_id")
        )
