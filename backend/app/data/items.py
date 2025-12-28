"""
物品類型定義
"""

from ..models.item import ItemType


# ============================================================
# 物品類型定義
# ============================================================

ITEM_TYPES = {
    # ========== 原料（L1 職業產出）==========
    "grain": ItemType(
        id="grain", name="穀物", icon="🌾",
        category="material", stack_max=10, price=2
    ),
    "livestock": ItemType(
        id="livestock", name="牲畜", icon="🐄",
        category="material", stack_max=5, price=10
    ),
    "ore": ItemType(
        id="ore", name="鐵礦", icon="🪨",
        category="material", stack_max=10, price=3
    ),
    "wood": ItemType(
        id="wood", name="木材", icon="🪵",
        category="material", stack_max=10, price=2
    ),
    "wool": ItemType(
        id="wool", name="羊毛", icon="☁️",
        category="material", stack_max=10, price=3
    ),
    "hide": ItemType(
        id="hide", name="羊皮", icon="🟫",
        category="material", stack_max=10, price=4
    ),
    
    # ========== 半成品（L2 職業產出）==========
    "flour": ItemType(
        id="flour", name="麵粉", icon="🌫️",
        category="material", stack_max=10, price=4
    ),
    "meat_raw": ItemType(
        id="meat_raw", name="生肉", icon="🥩",
        category="material", stack_max=10, price=5
    ),
    "iron": ItemType(
        id="iron", name="鐵錠", icon="🔩",
        category="material", stack_max=10, price=6
    ),
    "plank": ItemType(
        id="plank", name="木板", icon="📏",
        category="material", stack_max=10, price=4
    ),
    "cloth": ItemType(
        id="cloth", name="布料", icon="🧵",
        category="material", stack_max=10, price=6
    ),
    "leather": ItemType(
        id="leather", name="皮革", icon="🟤",
        category="material", stack_max=10, price=9
    ),
    
    # ========== 成品（消費品）==========
    "bread": ItemType(
        id="bread", name="麵包", icon="🍞",
        category="food", stack_max=10, price=3, satiety_restore=40
    ),
    "meat": ItemType(
        id="meat", name="肉品", icon="🍖",
        category="food", stack_max=10, price=6, satiety_restore=60
    ),
    "clothes": ItemType(
        id="clothes", name="衣服", icon="👕",
        category="clothing", stack_max=5, price=15
    ),
    "furniture": ItemType(
        id="furniture", name="家具", icon="🪑",
        category="goods", stack_max=3, price=20
    ),
    "beer": ItemType(
        id="beer", name="啤酒", icon="🍺",
        category="drink", stack_max=10, price=2, satiety_restore=2
    ),
    
    # ========== 工具 ==========
    "hoe": ItemType(
        id="hoe", name="鋤頭", icon="⛏️",
        category="tool", stack_max=1, durability_max=100, price=12
    ),
    "pickaxe": ItemType(
        id="pickaxe", name="鶴嘴鋤", icon="⛏️",
        category="tool", stack_max=1, durability_max=80, price=15
    ),
    "axe": ItemType(
        id="axe", name="斧頭", icon="🪓",
        category="tool", stack_max=1, durability_max=90, price=14
    ),
    "shears": ItemType(
        id="shears", name="剪刀", icon="✂️",
        category="tool", stack_max=1, durability_max=120, price=10
    ),
    "cleaver": ItemType(
        id="cleaver", name="屠刀", icon="🔪",
        category="tool", stack_max=1, durability_max=100, price=12
    ),
    "hammer": ItemType(
        id="hammer", name="錘子", icon="🔨",
        category="tool", stack_max=1, durability_max=100, price=15
    ),
    "saw": ItemType(
        id="saw", name="鋸子", icon="🪚",
        category="tool", stack_max=1, durability_max=70, price=14
    ),
    "scraper": ItemType(
        id="scraper", name="刮刀", icon="🔪",
        category="tool", stack_max=1, durability_max=80, price=10
    ),
}


def get_item_type(item_id: str) -> ItemType:
    """取得物品類型"""
    if item_id not in ITEM_TYPES:
        raise ValueError(f"Unknown item type: {item_id}")
    return ITEM_TYPES[item_id]
