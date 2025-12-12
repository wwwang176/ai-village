"""
供應鏈關係定義
"""

from typing import List, Optional


# ============================================================
# 供應鏈定義
# ============================================================

# 各職業的供應商（誰提供原料）
SUPPLY_CHAIN = {
    # 食物鏈
    "miller": ["farmer"],               # 磨坊主 ← 農夫（穀物）
    # butcher 透過羊系統購羊，不需要供應商
    "baker": ["miller"],                # 麵包師 ← 磨坊主（麵粉）
    
    # 器具鏈
    "blacksmith": ["miner"],            # 鐵匠 ← 礦工（鐵礦）
    "carpenter": ["lumberjack", "blacksmith"],  # 木匠 ← 伐木工（木材）+ 鐵匠（鐵錠）
    
    # 服飾鏈
    "weaver": ["shepherd"],             # 織工 ← 牧羊人（羊毛）
    "tanner": ["butcher"],              # 皮革匠 ← 屠夫（羊皮）
    "tailor": ["weaver", "tanner"],     # 裁縫 ← 織工（布料）+ 皮革匠（皮革）
}


# 各職業需要的原料
REQUIRED_MATERIALS = {
    "miller": ["grain"],                # 磨坊主需要穀物
    # butcher 透過羊系統購買和宰殺羊，不需要原料
    "baker": ["flour"],                 # 麵包師需要麵粉
    "blacksmith": ["ore"],              # 鐵匠需要鐵礦
    "carpenter": ["wood", "iron"],      # 木匠需要木材+鐵錠
    "weaver": ["wool"],                 # 織工需要羊毛
    "tanner": ["hide"],                 # 皮革匠需要羊皮
    "tailor": ["cloth", "leather"],     # 裁縫需要布料+皮革
}


# 原料 → 生產者對應表
MATERIAL_PRODUCERS = {
    "grain": "farmer",          # 穀物 ← 農夫
    # livestock 透過羊系統處理，不是物品
    "ore": "miner",             # 鐵礦 ← 礦工
    "wood": "lumberjack",       # 木材 ← 伐木工
    "wool": "shepherd",         # 羊毛 ← 牧羊人
    "hide": "butcher",          # 羊皮 ← 屠夫（宰殺羊獲得）
    "flour": "miller",          # 麵粉 ← 磨坊主
    "meat_raw": "butcher",      # 生肉 ← 屠夫
    "iron": "blacksmith",       # 鐵錠 ← 鐵匠
    "plank": "carpenter",       # 木板 ← 木匠
    "cloth": "weaver",          # 布料 ← 織工
    "leather": "tanner",        # 皮革 ← 皮革匠
}


# 消費終點（村民可以購買的店家）
CONSUMER_SHOPS = {
    "food": ["baker", "butcher"],       # 食物 → 麵包師、屠夫
    "tools": ["blacksmith"],            # 工具 → 鐵匠
    "furniture": ["carpenter"],         # 家具 → 木匠
    "clothing": ["tailor"],             # 衣服 → 裁縫
    "misc": ["merchant"],               # 其他 → 商人
}


# 生產配方中各原料需要的數量（每次消耗）
MATERIAL_QUANTITIES = {
    "grain": 1,
    "flour": 1,
    "ore": 1,
    "wood": 1,
    "wool": 1,
    "hide": 1,
    "iron": 1,
    "cloth": 1,
    "leather": 1
}

# 補貨倍數（庫存=0時，補充 消耗量 × 此倍數）
RESTOCK_MULTIPLIER = 3


# 食物賣家對應表（食物 → 生產者職業）
FOOD_SELLERS = [
    ("bread", "baker"),       # 麵包 → 麵包師
    ("meat_raw", "butcher"),  # 生肉 → 屠夫
]


def get_supplier_occupation(material: str) -> Optional[str]:
    """查詢誰生產這個原料"""
    return MATERIAL_PRODUCERS.get(material)


def get_suppliers_for_occupation(occupation: str) -> List[str]:
    """取得某職業的供應商列表"""
    return SUPPLY_CHAIN.get(occupation, [])


def get_required_materials_for_occupation(occupation: str) -> List[str]:
    """取得某職業需要的原料"""
    return REQUIRED_MATERIALS.get(occupation, [])


def get_shops_for_need(need_type: str) -> List[str]:
    """取得滿足某需求的店家"""
    return CONSUMER_SHOPS.get(need_type, [])


# ============================================================
# 商人收購系統
# ============================================================

# 商人收購的物品及價格（所有原料都可收購，商人賺 20% 出口利潤）
MERCHANT_BUY_PRICES = {
    # L1 原料
    "grain": 2,         # 穀物
    "ore": 3,           # 礦石
    "wood": 2,          # 木材
    "wool": 2,          # 羊毛
    # L2 半成品
    "flour": 5,         # 麵粉
    "iron": 8,          # 鐵錠
    "cloth": 7,         # 布料
    "leather": 10,      # 皮革
    "hide": 4,          # 獸皮
    "meat_raw": 5,      # 生肉
    "plank": 6,         # 木板
    # L3 成品
    "bread": 4,         # 麵包
    "meat": 6,          # 熟肉
    "furniture": 18,    # 家具
    "clothes": 23,      # 衣服
}

# 過剩門檻（分層設計）- 達到門檻時會賣給商人
EXCESS_THRESHOLDS = {
    # L1 原料：容易大量生產
    "grain": 20, "ore": 20, "wood": 20, "wool": 20,
    # L2 半成品：受供應鏈限制
    "flour": 10, "iron": 10, "cloth": 10, "leather": 10,
    "hide": 10, "meat_raw": 10, "plank": 10,
    # L3 成品：生產慢，應積極賣出
    "bread": 15,      # 基本需求，保留較多
    "meat": 10,       # 食物
    "furniture": 1,   # 高價值，立即賣
    "clothes": 1,     # 高價值，立即賣
}
