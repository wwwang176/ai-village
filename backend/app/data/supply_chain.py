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
    "bartender": ["farmer"],            # 酒保 ← 農夫（穀物）
    
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
    "bartender": ["grain"],             # 酒保需要穀物
    "blacksmith": ["ore"],              # 鐵匠需要鐵礦
    "carpenter": ["wood", "iron"],      # 木匠需要木材+鐵錠
    "weaver": ["wool"],                 # 織工需要羊毛
    "tanner": ["hide"],                 # 皮革匠需要羊皮
    "tailor": ["cloth", "leather"],     # 裁縫需要布料+皮革
}


# 物品 → 生產者對應表（包含原料、半成品、成品）
MATERIAL_PRODUCERS = {
    # L1 原料
    "grain": "farmer",          # 穀物 ← 農夫
    "ore": "miner",             # 鐵礦 ← 礦工
    "wood": "lumberjack",       # 木材 ← 伐木工
    "wool": "shepherd",         # 羊毛 ← 牧羊人
    # L2 半成品
    "hide": "butcher",          # 羊皮 ← 屠夫（宰殺羊獲得）
    "meat_raw": "butcher",      # 生肉 ← 屠夫
    "flour": "miller",          # 麵粉 ← 磨坊主
    "iron": "blacksmith",       # 鐵錠 ← 鐵匠
    "plank": "carpenter",       # 木板 ← 木匠
    "cloth": "weaver",          # 布料 ← 織工
    "leather": "tanner",        # 皮革 ← 皮革匠
    # L3 成品
    "bread": "baker",           # 麵包 ← 麵包師
    "meat": "butcher",          # 熟肉 ← 屠夫
    "furniture": "carpenter",   # 家具 ← 木匠
    "clothes": "tailor",        # 衣服 ← 裁縫
    "beer": "bartender",        # 啤酒 ← 酒保
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
    """查詢誰生產這個物品"""
    return MATERIAL_PRODUCERS.get(material)


def get_occupation_products(occupation: str) -> List[str]:
    """取得某職業生產的所有物品（反轉 MATERIAL_PRODUCERS）"""
    return [item for item, occ in MATERIAL_PRODUCERS.items() if occ == occupation]


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

# 商人收購的物品及價格。
#
# 商業規則：商人收購一律賺 20% 出口利潤（轉賣海外）。本表為「商人付給村民的價格」，
# 跟物品 base price（items.py:ItemType.price）的關係如下：
#   - 原料/半成品：預設等於 base price（如 grain=2、ore=3、flour=3、iron=8）
#   - L2 高價成品：商人額外加碼（如 leather +1、meat +1），鼓勵村民出售
#   - L3 終端成品：商人給予大幅溢價（家具 33、衣服 35），這是高價成品的設計溢價
#
# ⚠️ 修改物品 base price（items.py）時，請順手檢查本表是否需要同步更新，
# 否則會出現像 0b10526 那次的「啤酒漲價但商人收購價沒同步」的 bug。
MERCHANT_BUY_PRICES = {
    # L1 原料（與 base price 一致）
    "grain": 2,         # 穀物
    "ore": 3,           # 礦石
    "wood": 2,          # 木材
    "wool": 2,          # 羊毛
    # L2 半成品（部分有商人加碼）
    "flour": 3,         # 麵粉
    "iron": 8,          # 鐵錠
    "cloth": 7,         # 布料
    "leather": 11,      # 皮革（base 10 + 商人加碼 1）
    "hide": 4,          # 獸皮
    "meat_raw": 5,      # 生肉
    "plank": 6,         # 木板
    # L3 成品
    "bread": 3,         # 麵包
    "meat": 6,          # 熟肉（base 5 + 商人加碼 1）
    "beer": 3,          # 啤酒
    "furniture": 33,    # 家具（base 20，商人大幅溢價）
    "clothes": 35,      # 衣服（base 15，商人大幅溢價）
}

# 過剩門檻（分層設計）- 達到門檻時會賣給商人
EXCESS_THRESHOLDS = {
    # L1 原料：容易大量生產
    "grain": 40, "ore": 20, "wood": 20, "wool": 20,
    # L2 半成品：受供應鏈限制
    "flour": 20, "iron": 10, "cloth": 10, "leather": 10,
    "hide": 10, "meat_raw": 30, "plank": 10,
    # L3 成品：生產慢，應積極賣出
    "bread": 50,      # 基本需求，保留較多
    "meat": 10,       # 食物
    "beer": 20,       # 啤酒
    "furniture": 1,   # 高價值，立即賣
    "clothes": 1,     # 高價值，立即賣
}
