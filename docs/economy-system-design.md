# AI City 經濟系統設計文檔

## 概述

本文檔定義了 AI City 的經濟系統，包含職業、產業鏈、物品系統、工具耐久度等機制。

---

## 1. 職業系統

### 1.1 職業列表（13 種）

| # | 職業 | 英文 ID | 層級 | 產業鏈 | 需要工具 |
|---|------|---------|------|--------|----------|
| 1 | 農夫 | farmer | L1 | 食物鏈 | 鋤頭 |
| 2 | 磨坊主 | miller | L2 | 食物鏈 | - |
| 3 | 屠夫 | butcher | L2 | 食物鏈 | 屠刀 |
| 4 | 麵包師 | baker | L3 | 食物鏈 | - |
| 5 | 礦工 | miner | L1 | 器具鏈 | 鶴嘴鋤 |
| 6 | 伐木工 | lumberjack | L1 | 器具鏈 | 斧頭 |
| 7 | 鐵匠 | blacksmith | L2 | 器具鏈 | 錘子 |
| 8 | 木匠 | carpenter | L2 | 器具鏈 | 鋸子 |
| 9 | 牧羊人 | shepherd | L1 | 服飾鏈 | 剪刀 |
| 10 | 織工 | weaver | L2 | 服飾鏈 | - |
| 11 | 皮革匠 | tanner | L2 | 服飾鏈 | 刮刀 |
| 12 | 裁縫 | tailor | L3 | 服飾鏈 | 剪刀 |
| 13 | 商人 | merchant | 特殊 | 貿易 | - |

### 1.2 職業工作時間

| 職業 | 工作時間 | 說明 |
|------|----------|------|
| 農夫 | 05:00-14:00 | 早起務農 |
| 礦工 | 06:00-15:00 | 礦坑作業 |
| 伐木工 | 06:00-15:00 | 森林作業 |
| 牧羊人 | 05:00-14:00 | 放牧 |
| 磨坊主 | 07:00-16:00 | 配合農夫 |
| 屠夫 | 06:00-15:00 | 早市供應 |
| 麵包師 | 04:00-13:00 | 凌晨烤麵包 |
| 鐵匠 | 08:00-17:00 | 正常工時 |
| 木匠 | 08:00-17:00 | 正常工時 |
| 織工 | 08:00-17:00 | 正常工時 |
| 皮革匠 | 08:00-17:00 | 正常工時 |
| 裁縫 | 09:00-18:00 | 稍晚開工 |
| 商人 | 08:00-18:00 | 市集時間 |

---

## 2. 產業鏈系統

### 2.1 產業鏈結構圖

```
【食物鏈】🍖

     農夫 ─────────────────────────┐
       │                          │
       ▼                          ▼
    磨坊主                       屠夫
       │                          │
       ▼                          │
    麵包師 ←──────────────────────┘
       │
       ▼
   [村民消費]


【器具鏈】⛏️

    礦工          伐木工
      │              │
      ▼              ▼
    鐵匠 ─────────→ 木匠
      │              │
      ▼              ▼
   [村民消費]    [村民消費]


【服飾鏈】👔

           牧羊人
          ╱      ╲
         ▼        ▼
       織工    皮革匠
         ╲        ╱
          ▼      ▼
           裁縫
             │
             ▼
        [村民消費]


【貿易】🏪

    [外部世界]
         │
         ▼
       商人 ←→ 各職業（進出口）
```

### 2.2 供應鏈定義

```python
SUPPLY_CHAIN = {
    # 食物鏈
    "miller": ["farmer"],               # 磨坊主 ← 農夫（穀物）
    "butcher": ["farmer"],              # 屠夫 ← 農夫（牲畜）
    "baker": ["miller"],                # 麵包師 ← 磨坊主（麵粉）
    
    # 器具鏈
    "blacksmith": ["miner"],            # 鐵匠 ← 礦工（鐵礦）
    "carpenter": ["lumberjack", "blacksmith"],  # 木匠 ← 伐木工（木材）+ 鐵匠（鐵釘）
    
    # 服飾鏈
    "weaver": ["shepherd"],             # 織工 ← 牧羊人（羊毛）
    "tanner": ["shepherd"],             # 皮革匠 ← 牧羊人（羊皮）
    "tailor": ["weaver", "tanner"],     # 裁縫 ← 織工（布料）+ 皮革匠（皮革）
}
```

### 2.3 村民消費終點

```python
CONSUMER_SHOPS = {
    "food": ["baker", "butcher"],       # 食物 → 麵包師、屠夫
    "tools": ["blacksmith"],            # 工具 → 鐵匠
    "furniture": ["carpenter"],         # 家具 → 木匠
    "clothing": ["tailor"],             # 衣服 → 裁縫
    "misc": ["merchant"],               # 其他 → 商人
}
```

---

## 3. 物品系統

### 3.1 物品分類

#### 原料（L1 職業產出）

| 物品 | 英文 ID | 圖示 | 來源 |
|------|---------|------|------|
| 穀物 | grain | 🌾 | 農夫 |
| 牲畜 | livestock | 🐄 | 農夫 |
| 鐵礦 | ore | 🪨 | 礦工 |
| 木材 | wood | 🪵 | 伐木工 |
| 羊毛 | wool | 🧶 | 牧羊人 |
| 羊皮 | hide | 🐑 | 牧羊人 |

#### 半成品（L2 職業產出）

| 物品 | 英文 ID | 圖示 | 來源 |
|------|---------|------|------|
| 麵粉 | flour | 🌫️ | 磨坊主 |
| 生肉 | meat_raw | 🥩 | 屠夫 |
| 鐵錠 | iron | 🔩 | 鐵匠 |
| 木板 | plank | 📏 | 木匠 |
| 布料 | cloth | 🧵 | 織工 |
| 皮革 | leather | 🟤 | 皮革匠 |

#### 成品（消費品）

| 物品 | 英文 ID | 圖示 | 來源 | 用途 |
|------|---------|------|------|------|
| 麵包 | bread | 🍞 | 麵包師 | 食物 |
| 肉品 | meat | 🍖 | 屠夫 | 食物 |
| 衣服 | clothes | 👕 | 裁縫 | 穿著 |
| 家具 | furniture | 🪑 | 木匠 | 家用 |

#### 工具

| 工具 | 英文 ID | 圖示 | 耐久度 | 使用者 |
|------|---------|------|--------|--------|
| 鋤頭 | hoe | ⛏️ | 100 | 農夫 |
| 鶴嘴鋤 | pickaxe | ⛏️ | 80 | 礦工 |
| 斧頭 | axe | 🪓 | 90 | 伐木工 |
| 剪刀 | shears | ✂️ | 120 | 牧羊人、裁縫 |
| 屠刀 | cleaver | 🔪 | 100 | 屠夫 |
| 錘子 | hammer | 🔨 | 100 | 鐵匠 |
| 鋸子 | saw | 🪚 | 70 | 木匠 |
| 刮刀 | scraper | 🔪 | 80 | 皮革匠 |

### 3.2 物品資料結構

```python
# 物品定義
ITEMS = {
    # 原料
    "grain": {"name": "穀物", "icon": "🌾", "category": "material", "stack_max": 10},
    "livestock": {"name": "牲畜", "icon": "🐄", "category": "material", "stack_max": 5},
    "ore": {"name": "鐵礦", "icon": "🪨", "category": "material", "stack_max": 10},
    "wood": {"name": "木材", "icon": "🪵", "category": "material", "stack_max": 10},
    "wool": {"name": "羊毛", "icon": "🧶", "category": "material", "stack_max": 10},
    "hide": {"name": "羊皮", "icon": "🐑", "category": "material", "stack_max": 10},
    
    # 半成品
    "flour": {"name": "麵粉", "icon": "🌫️", "category": "material", "stack_max": 10},
    "meat_raw": {"name": "生肉", "icon": "🥩", "category": "material", "stack_max": 10},
    "iron": {"name": "鐵錠", "icon": "🔩", "category": "material", "stack_max": 10},
    "plank": {"name": "木板", "icon": "📏", "category": "material", "stack_max": 10},
    "cloth": {"name": "布料", "icon": "🧵", "category": "material", "stack_max": 10},
    "leather": {"name": "皮革", "icon": "🟤", "category": "material", "stack_max": 10},
    
    # 成品
    "bread": {"name": "麵包", "icon": "🍞", "category": "food", "stack_max": 10, "hunger_restore": 30},
    "meat": {"name": "肉品", "icon": "🍖", "category": "food", "stack_max": 10, "hunger_restore": 50},
    "clothes": {"name": "衣服", "icon": "👕", "category": "clothing", "stack_max": 5},
    "furniture": {"name": "家具", "icon": "🪑", "category": "goods", "stack_max": 3},
    
    # 工具
    "hoe": {"name": "鋤頭", "icon": "⛏️", "category": "tool", "stack_max": 1, "durability_max": 100},
    "pickaxe": {"name": "鶴嘴鋤", "icon": "⛏️", "category": "tool", "stack_max": 1, "durability_max": 80},
    "axe": {"name": "斧頭", "icon": "🪓", "category": "tool", "stack_max": 1, "durability_max": 90},
    "shears": {"name": "剪刀", "icon": "✂️", "category": "tool", "stack_max": 1, "durability_max": 120},
    "cleaver": {"name": "屠刀", "icon": "🔪", "category": "tool", "stack_max": 1, "durability_max": 100},
    "hammer": {"name": "錘子", "icon": "🔨", "category": "tool", "stack_max": 1, "durability_max": 100},
    "saw": {"name": "鋸子", "icon": "🪚", "category": "tool", "stack_max": 1, "durability_max": 70},
    "scraper": {"name": "刮刀", "icon": "🔪", "category": "tool", "stack_max": 1, "durability_max": 80},
}
```

### 3.3 物品堆疊

```python
# 物品堆疊資料結構
item_stack = {
    "item_id": "bread",      # 物品類型
    "quantity": 6,           # 數量 (1-10)
    "durability": None,      # 工具才有耐久度
    "owner_id": "villager_001",  # 擁有者 ID（新增）
}

# 工具堆疊（不可疊放）
tool_stack = {
    "item_id": "hoe",
    "quantity": 1,           # 工具永遠是 1
    "durability": 75,        # 當前耐久度
    "owner_id": "villager_001",  # 擁有者 ID
}
```

### 3.4 物品擁有權

| owner_id 值 | 意義 |
|-------------|------|
| `"villager_001"` | 屬於該村民，只有他能撿起 |
| `None` | 無主物品，任何人可撿 |

```python
def can_pickup(villager, item):
    """村民能否撿起物品"""
    # 無主物品，任何人可撿
    if item["owner_id"] is None:
        return True
    
    # 物品屬於該村民
    if item["owner_id"] == villager["id"]:
        return True
    
    # 其他人不能撿
    return False
```

### 3.5 堆疊規則

- 每格只能放**同一種**物品
- 普通物品最多疊放 **10** 個
- 工具**不可疊放**（每個有獨立耐久度）
- 顯示格式：`圖示 + 數量`（如 🍞6）
- 工具顯示：`圖示 + 耐久度%`（如 ⛏️75%）
- 有擁有者的物品顯示：`圖示 + 數量 [擁有者]`（如 🌾8 [農夫]）

---

## 4. 背包系統

### 4.1 村民背包

每個村民有 **3 格**背包空間。

```python
villager = {
    "id": "villager_001",
    "name": "王大明",
    "occupation": "farmer",
    
    # 背包：3 格
    "inventory": [
        {"item_id": "hoe", "quantity": 1, "durability": 75},      # 格子 0
        {"item_id": "grain", "quantity": 8, "durability": None},  # 格子 1
        None,  # 格子 2：空的
    ],
    
    # 金錢
    "money": 50,
}
```

### 4.2 背包操作

| 操作 | 說明 |
|------|------|
| 撿起 | 地上物品 → 背包（需有空格或可疊加）|
| 放下 | 背包物品 → 地上（該格需空或同類物品）|
| 使用 | 消耗物品（食物）或消耗耐久度（工具）|
| 交易 | 物品 ↔ 金錢 |

### 4.3 背包顯示

```
王大明的背包：
┌─────┬─────┬─────┐
│⛏️75%│🌾 8 │     │
└─────┴─────┴─────┘
金錢：$50
```

---

## 5. 地上物品

### 5.1 資料結構

```python
# 世界物品列表
world_items = [
    {
        "id": "item_001",
        "item_id": "bread",
        "quantity": 5,
        "x": 15,
        "y": 22,
        "durability": None,
    },
]
```

### 5.2 地上物品規則

- 每個地圖格子最多放 **1 種**物品
- 同種物品最多疊放 **10** 個
- 村民可以撿起/放下物品
- 物品不會自動消失

### 5.3 地上物品顯示

```
地圖：
┌────┬────┬────┐
│ 🌾 │ 🍞 │    │
│ 10 │  5 │    │
└────┴────┴────┘
```

---

## 6. 工具耐久度

### 6.1 耐久度機制

- 每次工作消耗耐久度：**-5**
- 耐久度歸零：**工具直接消失**（從背包移除）
- 沒有工具：無法工作（需先去鐵匠購買）
- 工具不可修理，損壞後需購買新的

### 6.2 職業與工具對應

```python
OCCUPATION_TOOLS = {
    "farmer": "hoe",           # 農夫 → 鋤頭
    "miner": "pickaxe",        # 礦工 → 鶴嘴鋤
    "lumberjack": "axe",       # 伐木工 → 斧頭
    "shepherd": "shears",      # 牧羊人 → 剪刀
    "butcher": "cleaver",      # 屠夫 → 屠刀
    "blacksmith": "hammer",    # 鐵匠 → 錘子
    "carpenter": "saw",        # 木匠 → 鋸子
    "tanner": "scraper",       # 皮革匠 → 刮刀
    "tailor": "shears",        # 裁縫 → 剪刀
    "miller": None,            # 磨坊主 → 不需要
    "baker": None,             # 麵包師 → 不需要
    "weaver": None,            # 織工 → 不需要
    "merchant": None,          # 商人 → 不需要
}
```

### 6.3 工作流程

```
1. 檢查背包是否有工具
   ├─ 沒有 → 前往鐵匠購買 → 返回工作
   └─ 有 → 繼續

2. 執行工作
   ├─ 工具耐久度 -5
   ├─ 產出物品 → 放入背包
   └─ 若耐久度 ≤ 0 → 工具消失（從背包移除）

3. 背包滿了？
   ├─ 滿了 → 物品放在工作地點地上
   └─ 沒滿 → 繼續工作

4. 下次工作前
   └─ 若無工具 → 前往鐵匠購買新工具
```

### 6.4 工具損壞範例

```
農夫的鋤頭耐久度：15
  │
  ├─ 工作一次 → 耐久度 10
  ├─ 工作一次 → 耐久度 5
  ├─ 工作一次 → 耐久度 0 → 鋤頭消失！
  │
  └─ 下次工作 → 發現沒工具 → 去鐵匠買新鋤頭
```

---

## 7. 生產配方

### 7.1 各職業生產配方

```python
RECIPES = {
    # L1 職業（原料生產）
    "farmer": {
        "input": [],
        "output": [{"item_id": "grain", "quantity": 2}],
        "tool": "hoe",
        "work_time": 2,
    },
    "farmer_livestock": {
        "input": [],
        "output": [{"item_id": "livestock", "quantity": 1}],
        "tool": "hoe",
        "work_time": 4,
    },
    "miner": {
        "input": [],
        "output": [{"item_id": "ore", "quantity": 2}],
        "tool": "pickaxe",
        "work_time": 3,
    },
    "lumberjack": {
        "input": [],
        "output": [{"item_id": "wood", "quantity": 2}],
        "tool": "axe",
        "work_time": 2,
    },
    "shepherd": {
        "input": [],
        "output": [
            {"item_id": "wool", "quantity": 2},
            {"item_id": "hide", "quantity": 1},
        ],
        "tool": "shears",
        "work_time": 3,
    },
    
    # L2 職業（加工）
    "miller": {
        "input": [{"item_id": "grain", "quantity": 2}],
        "output": [{"item_id": "flour", "quantity": 2}],
        "tool": None,
        "work_time": 2,
    },
    "butcher": {
        "input": [{"item_id": "livestock", "quantity": 1}],
        "output": [{"item_id": "meat_raw", "quantity": 4}],
        "tool": "cleaver",
        "work_time": 2,
    },
    "blacksmith_iron": {
        "input": [{"item_id": "ore", "quantity": 2}],
        "output": [{"item_id": "iron", "quantity": 2}],
        "tool": "hammer",
        "work_time": 3,
    },
    "blacksmith_tool": {
        "input": [{"item_id": "iron", "quantity": 2}],
        "output": [{"item_id": "hoe", "quantity": 1, "durability": 100}],  # 可製作各種工具
        "tool": "hammer",
        "work_time": 4,
    },
    "carpenter": {
        "input": [
            {"item_id": "wood", "quantity": 2},
            {"item_id": "iron", "quantity": 1},
        ],
        "output": [{"item_id": "furniture", "quantity": 1}],
        "tool": "saw",
        "work_time": 4,
    },
    "weaver": {
        "input": [{"item_id": "wool", "quantity": 2}],
        "output": [{"item_id": "cloth", "quantity": 2}],
        "tool": None,
        "work_time": 3,
    },
    "tanner": {
        "input": [{"item_id": "hide", "quantity": 2}],
        "output": [{"item_id": "leather", "quantity": 2}],
        "tool": "scraper",
        "work_time": 3,
    },
    
    # L3 職業（成品）
    "baker": {
        "input": [{"item_id": "flour", "quantity": 2}],
        "output": [{"item_id": "bread", "quantity": 4}],
        "tool": None,
        "work_time": 2,
    },
    "tailor": {
        "input": [
            {"item_id": "cloth", "quantity": 2},
            {"item_id": "leather", "quantity": 1},
        ],
        "output": [{"item_id": "clothes", "quantity": 2}],
        "tool": "shears",
        "work_time": 3,
    },
}
```

---

## 8. 經濟系統

### 8.1 物品價格

```python
PRICES = {
    # 原料
    "grain": 2,
    "livestock": 10,
    "ore": 3,
    "wood": 2,
    "wool": 3,
    "hide": 4,
    
    # 半成品
    "flour": 4,
    "meat_raw": 5,
    "iron": 6,
    "plank": 4,
    "cloth": 6,
    "leather": 8,
    
    # 成品
    "bread": 3,
    "meat": 6,
    "clothes": 15,
    "furniture": 20,
    
    # 工具
    "hoe": 12,
    "pickaxe": 15,
    "axe": 14,
    "shears": 10,
    "cleaver": 12,
    "hammer": 15,
    "saw": 14,
    "scraper": 10,
}
```

### 8.2 物品存放流程

```
【生產完成後】
1. 產出物品放入背包（owner_id = 生產者）
2. 背包滿了 → 回家放在家裡地上（owner_id 仍是生產者）

【物品存放位置】
┌─────────────┬────────────────────────────┐
│ 場景        │ 物品位置                   │
├─────────────┼────────────────────────────┤
│ 生產中      │ 村民背包                   │
│ 背包滿      │ 自己家裡地上               │
│ 交易後      │ 買家可撿取（地上或轉移）   │
│ 買完        │ 買家背包                   │
└─────────────┴────────────────────────────┘
```

### 8.3 交易流程（含擁有權轉移）

```
【步驟一：買家找賣家】

磨坊主需要穀物：
  1. 檢查磨坊有沒有自己的穀物
  2. 沒有 → 去找農夫（走到農夫位置）

【步驟二：對話交易】

  磨坊主：「我需要穀物，賣我 8 個？」
  農夫：「好，8 個穀物 $16」
  
  交易執行：
  - 磨坊主金錢 -$16
  - 農夫金錢 +$16
  - 穀物 owner_id 改為「磨坊主」

【步驟三：物品交接】

  情況 A：穀物在農夫背包
    → 農夫把穀物丟在地上（owner_id = 磨坊主）
    → 磨坊主撿起（如果背包有空）
    → 或之後再來撿
  
  情況 B：穀物在農夫家地上
    → owner_id 直接改為磨坊主
    → 磨坊主去農夫家撿
```

### 8.4 交易函數

```python
def trade(buyer, seller, item_id, quantity):
    """交易：轉移擁有權 + 金錢"""
    price = PRICES[item_id] * quantity
    
    # 檢查買家有足夠的錢
    if buyer["money"] < price:
        return False, "錢不夠"
    
    # 找到賣家的物品（背包或地上）
    items = find_items_by_owner(seller["id"], item_id)
    total = sum(i["quantity"] for i in items)
    if total < quantity:
        return False, "賣家沒有足夠的貨"
    
    # 執行交易
    buyer["money"] -= price
    seller["money"] += price
    
    # 轉移擁有權
    transferred = 0
    for item in items:
        if transferred >= quantity:
            break
        
        take = min(item["quantity"], quantity - transferred)
        item["owner_id"] = buyer["id"]  # 轉移擁有權
        transferred += take
        
        # 如果物品在賣家背包，丟到地上
        if is_in_inventory(seller, item):
            drop_item(seller, item)  # 丟在賣家腳下
    
    return True, "交易成功"
```

### 8.5 交易視覺呈現

```
【交易前】
農夫家：
┌─────────────────────┐
│                     │
│  🌾8 [農夫]         │  ← 磨坊主看得到但不能撿
│      👨‍🌾  👨‍🔧       │  ← 磨坊主來找農夫對話
│                     │
└─────────────────────┘

【交易後 - 擁有權轉移】
農夫家：
┌─────────────────────┐
│                     │
│  🌾8 [磨坊主]       │  ← 現在磨坊主可以撿了！
│      👨‍🌾  👨‍🔧       │
│                     │
└─────────────────────┘

【磨坊主撿起後】
農夫家：              磨坊主背包：
┌─────────────────────┐   ┌─────┬─────┬─────┐
│                     │   │ 🌾8 │     │     │
│      👨‍🌾            │   └─────┴─────┴─────┘
│                     │
└─────────────────────┘
```

### 8.6 金錢流向

```
[L1 生產者] ──賣原料──→ [L2 加工者] ──賣半成品──→ [L3 成品者]
                                                      │
                                                      ▼
                                                  [村民消費]
                                                      │
              ←─────────── 購買工具/商品 ─────────────┘
```

---

## 9. 規則系統與 AI 分工

### 9.1 設計原則

```
┌─────────────────────────────────────────────────────┐
│                 Python 規則系統                      │
│                                                     │
│  決定：做什麼？找誰？買多少？付多少錢？             │
│                                                     │
│  ✅ 快速、確定性、不花 API 費用                     │
└─────────────────────┬───────────────────────────────┘
                      │
                      │ 把「結果」傳給 AI
                      ▼
┌─────────────────────────────────────────────────────┐
│                      AI                             │
│                                                     │
│  決定：怎麼說？語氣？個性反映？                     │
│                                                     │
│  ✅ 對話自然、有個性                               │
└─────────────────────────────────────────────────────┘
```

**簡單說：Python 決定「做什麼」→ AI 決定「怎麼說」**

### 9.2 分工對照表

| 功能 | 處理方式 | 原因 |
|------|---------|------|
| 需要買什麼 | 規則查表 | 快速、確定 |
| 找誰買 | 規則查表 | 快速、確定 |
| 價格計算 | 規則計算 | 精確 |
| 交易執行 | 規則邏輯 | 不能出錯 |
| 物品轉移 | 規則邏輯 | 不能出錯 |
| 對話內容 | AI 生成 | 自然、有個性 |
| 情緒反應 | AI 生成 | 豐富多變 |

### 9.3 原料查詢表

```python
# 各職業需要的原料
REQUIRED_MATERIALS = {
    "miller": ["grain"],                # 磨坊主需要穀物
    "butcher": ["livestock"],           # 屠夫需要牲畜
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
    "livestock": "farmer",      # 牲畜 ← 農夫
    "ore": "miner",             # 鐵礦 ← 礦工
    "wood": "lumberjack",       # 木材 ← 伐木工
    "wool": "shepherd",         # 羊毛 ← 牧羊人
    "hide": "shepherd",         # 羊皮 ← 牧羊人
    "flour": "miller",          # 麵粉 ← 磨坊主
    "meat_raw": "butcher",      # 生肉 ← 屠夫
    "iron": "blacksmith",       # 鐵錠 ← 鐵匠
    "cloth": "weaver",          # 布料 ← 織工
    "leather": "tanner",        # 皮革 ← 皮革匠
}
```

### 9.4 規則系統決策流程

```python
def decide_action(villager, game_state):
    """規則系統決定行為（不用 AI）"""
    
    occupation = villager["occupation"]
    
    # 1. 需要工具但沒有？
    required_tool = OCCUPATION_TOOLS.get(occupation)
    if required_tool and not has_item(villager, required_tool):
        supplier = find_villager_by_occupation("blacksmith", game_state)
        return {
            "action": "buy_tool",
            "item": required_tool,
            "target": supplier["id"] if supplier else None
        }
    
    # 2. 需要原料？
    needed_materials = REQUIRED_MATERIALS.get(occupation, [])
    for material in needed_materials:
        if not has_enough(villager, material):
            producer_occupation = MATERIAL_PRODUCERS[material]
            supplier = find_villager_by_occupation(producer_occupation, game_state)
            return {
                "action": "buy_material",
                "item": material,
                "target": supplier["id"] if supplier else None
            }
    
    # 3. 背包滿了？
    if is_inventory_full(villager):
        return {"action": "store_items"}
    
    # 4. 工作時間？
    if is_work_time(villager, game_state):
        return {"action": "work"}
    
    # 5. 其他...
    return {"action": "idle"}
```

### 9.5 AI 對話生成

```python
def generate_trade_dialogue(buyer, seller, item, quantity, price, phase):
    """AI 生成交易對話"""
    
    item_name = ITEMS[item]["name"]
    
    if phase == "request":
        # 買家開口
        prompt = f"""
【角色】你是 {buyer['name']}（{get_occupation_name(buyer['occupation'])}）
【個性】{buyer['personality']}
【情境】你要向 {seller['name']} 購買 {quantity} 個{item_name}，價格 ${price}
【要求】用一句話開口，符合你的個性。
"""
    
    elif phase == "response":
        # 賣家回應
        prompt = f"""
【角色】你是 {seller['name']}（{get_occupation_name(seller['occupation'])}）
【個性】{seller['personality']}
【情境】{buyer['name']} 向你買了 {quantity} 個{item_name}，你收到 ${price}
【要求】用一句話回應，符合你的個性。
"""
    
    return ai_generate(prompt)
```

### 9.6 完整交易流程範例

```
【磨坊主需要穀物】

步驟 1：規則系統決策
┌──────────────────────────────────────┐
│ decide_action(磨坊主)                │
│ → 檢查：沒有 grain                   │
│ → 查表：grain 由 farmer 生產         │
│ → 找到：農夫「王大明」               │
│ → 返回：{                            │
│     action: "buy_material",          │
│     item: "grain",                   │
│     target: "villager_003"           │
│   }                                  │
└──────────────────────────────────────┘

步驟 2：磨坊主走到農夫位置

步驟 3：AI 生成開場白
┌──────────────────────────────────────┐
│ generate_trade_dialogue(             │
│   buyer=磨坊主,                      │
│   seller=農夫,                       │
│   item="grain",                      │
│   quantity=8,                        │
│   price=16,                          │
│   phase="request"                    │
│ )                                    │
│                                      │
│ AI 輸出：                            │
│ 「王大哥，穀物收成了嗎？             │
│   我需要 8 個來磨麵粉。」            │
└──────────────────────────────────────┘

步驟 4：規則系統執行交易
┌──────────────────────────────────────┐
│ trade(buyer=磨坊主, seller=農夫,     │
│       item="grain", quantity=8)      │
│                                      │
│ → 磨坊主金錢 -$16                    │
│ → 農夫金錢 +$16                      │
│ → 穀物 owner_id = 磨坊主             │
└──────────────────────────────────────┘

步驟 5：AI 生成農夫回應
┌──────────────────────────────────────┐
│ AI 輸出：                            │
│ 「今年收成不錯，這批穀物             │
│   品質很好，你拿去吧！」             │
└──────────────────────────────────────┘

步驟 6：磨坊主撿起穀物，離開
```

---

## 10. 實作優先順序

### Phase 1：基礎物品系統
- [ ] 物品資料結構
- [ ] 村民背包系統
- [ ] 地上物品系統
- [ ] 物品撿起/放下

### Phase 2：工具系統
- [ ] 工具耐久度
- [ ] 工作需要工具檢查
- [ ] 工具損壞邏輯

### Phase 3：生產系統
- [ ] 生產配方
- [ ] 工作產出物品
- [ ] 原料消耗

### Phase 4：交易系統
- [ ] 物品價格
- [ ] 買賣交易
- [ ] 金錢流動

### Phase 5：AI 整合
- [ ] 村民自動購買原料
- [ ] 村民自動出售產品
- [ ] 村民消費行為

---

## 11. UI 更新

### Dashboard 背包顯示

```
┌─ 王大明（農夫）─────────────────────┐
│                                     │
│ 背包：                              │
│ ┌───────┬───────┬───────┐          │
│ │ ⛏️    │ 🌾    │       │          │
│ │ 75%   │  8    │       │          │
│ └───────┴───────┴───────┘          │
│                                     │
│ 金錢：$50                           │
└─────────────────────────────────────┘
```

### 地圖物品顯示

```
物品渲染在地圖格子上，格式：
- 圖示 + 數量（如 🍞5）
- 半透明背景
- 不阻擋村民移動
```

---

## 附錄：建築物對應

| 職業 | 建築物 | 英文 ID |
|------|--------|---------|
| 農夫 | 農田 | farm |
| 磨坊主 | 磨坊 | mill |
| 屠夫 | 肉舖 | butcher_shop |
| 麵包師 | 麵包店 | bakery |
| 礦工 | 礦場 | mine |
| 伐木工 | 伐木場 | lumber_camp |
| 鐵匠 | 鐵匠舖 | blacksmith |
| 木匠 | 木工坊 | carpentry |
| 牧羊人 | 牧場 | pasture |
| 織工 | 織坊 | weaver_shop |
| 皮革匠 | 皮革坊 | tannery |
| 裁縫 | 裁縫店 | tailor_shop |
| 商人 | 市集 | market |
