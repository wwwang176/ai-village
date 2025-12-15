# AI City 經濟系統設計文檔

## 概述

本文檔定義了 AI City 的經濟系統，包含職業、產業鏈、物品系統、工具耐久度等機制。

---

## 1. 職業系統

### 1.1 職業列表（13 種）

| # | 職業 | 英文 ID | 層級 | 產業鏈 | 需要工具 |
|---|------|---------|------|--------|----------|
| 1 | 👨‍🌾 農夫 | farmer | L1 | 🍖 食物鏈 | ⛏️ 鋤頭 |
| 2 | 🌾 磨坊主 | miller | L2 | 🍖 食物鏈 | - |
| 3 | 🔪 屠夫 | butcher | L2 | 🍖 食物鏈 | 🔪 屠刀 |
| 4 | 🍞 麵包師 | baker | L3 | 🍖 食物鏈 | - |
| 5 | ⛏️ 礦工 | miner | L1 | 🔧 器具鏈 | ⛏️ 鶴嘴鋤 |
| 6 | 🪓 伐木工 | lumberjack | L1 | 🔧 器具鏈 | 🪓 斧頭 |
| 7 | 🔨 鐵匠 | blacksmith | L2 | 🔧 器具鏈 | 🔨 錘子 |
| 8 | 🪚 木匠 | carpenter | L2 | 🔧 器具鏈 | 🪚 鋸子 |
| 9 | 🐑 牧羊人 | shepherd | L1 | 👔 服飾鏈 | ✂️ 剪刀 |
| 10 | 🧵 織工 | weaver | L2 | 👔 服飾鏈 | - |
| 11 | 🟤 皮革匠 | tanner | L2 | 👔 服飾鏈 | 🔪 刮刀 |
| 12 | 👕 裁縫 | tailor | L3 | 👔 服飾鏈 | ✂️ 剪刀 |
| 13 | 🏪 商人 | merchant | 特殊 | 💰 貿易 | - |

### 1.2 工作時間（已移除）

> ⚠️ **已移除固定工作時間限制**
> 
> 村民現在可以隨時工作，工作效率由**性格系統**（early_bird / night_owl）決定。
> 詳見「村民性格系統」章節。

---

## 1.5 村民性格系統

### 性格維度（7 維度 14 種性格）

每個村民在遊戲開始時從 7 個維度中隨機抽 4 個，每個維度抽一個正面或反面性格。

| 維度 | 正面 | 反面 | 影響機制 |
|------|------|------|----------|
| **社交** | extrovert（外向） | introvert（內向） | 聊天觸發機率 ×2/×0.5、社交值下降速度 ×1.5/×0.5 |
| **態度** | friendly（友善） | grumpy（暴躁） | 聊天後好感度 +2/-1 |
| **信任** | trusting（信任） | suspicious（多疑） | 熟悉度提升 ×1.5/×0.7 |
| **感情** | romantic（浪漫） | reserved（矜持） | 異性好感度 ×1.5/×0.7 |
| **勇氣** | brave（勇敢） | timid（膽小） | 對陌生人（熟悉度<30）搭話機率 ×2/×0.3 |
| **心態** | optimistic（樂觀） | pessimistic（悲觀） | 心情變化幅度（待實作） |
| **作息** | early_bird（早起鳥） | night_owl（夜貓子） | 見下表 |

### 作息性格效果詳細

| 效果 | 時段 | early_bird | night_owl |
|------|------|------------|-----------|
| **工作效率** | 白天（6:00-18:00） | +5% | -5% |
| | 晚上（18:00-6:00） | -5% | +5% |
| **體力下降** | 白天（6:00-18:00） | ×0.8（慢） | ×1.2（快） |
| | 晚上（18:00-6:00） | ×1.2（快） | ×0.8（慢） |

### 程式碼定義

```python
# game_state.py
personality_dimensions = {
    "social": ["extrovert", "introvert"],
    "temper": ["friendly", "grumpy"],
    "trust": ["trusting", "suspicious"],
    "romance": ["romantic", "reserved"],
    "courage": ["brave", "timid"],
    "outlook": ["optimistic", "pessimistic"],
    "schedule": ["early_bird", "night_owl"],
}

# 村民生成時抽 4 個維度
selected_dimensions = random.sample(list(personality_dimensions.keys()), 4)
traits = [random.choice(personality_dimensions[dim]) for dim in selected_dimensions]
```

---

## 2. 產業鏈系統

### 2.1 產業鏈結構圖

#### 🍖 食物鏈

```
L1  ┌─────────────┐
    │ 👨‍🌾 農夫     │
    │   farmer    │
    └──────┬──────┘
           │ � grain ×2
           ↓
L2  ┌─────────────┐
    │ 🌾 磨坊主   │
    │   miller    │
    └──────┬──────┘
           │ 🌫️ flour ×2
           ↓
L3  ┌─────────────┐
    │ 🍞 麵包師   │
    │   baker     │
    └──────┬──────┘
           │ 🍞 bread ×2 ($4)
           ↓
    [村民消費]
```

```
L1  ┌─────────────┐
    │ 🐑 牧羊人   │
    │  shepherd   │
    └──────┬──────┘
           │ 🐑 羊 ×1 ($10)
           ↓
L2  ┌─────────────┐
    │ 🔪 屠夫     │
    │   butcher   │
    └──────┬──────┘
           │ 🥩 meat_raw ×2 ($5)
           │ ☁️ hide ×1 ($4)
           ↓
    [村民消費] / [皮革匠]
```

#### ⛏️ 器具鏈

```
L1  ┌─────────────┐          ┌─────────────┐
    │ ⛏️ 礦工     │          │ 🪓 伐木工   │
    │   miner     │          │  lumberjack │
    └──────┬──────┘          └──────┬──────┘
           │ 🪨 ore ×2              │ 🪵 wood ×2
           ↓                        │
L2  ┌─────────────┐                 │
    │ 🔨 鐵匠     │                 │
    │  blacksmith │                 │
    └──────┬──────┘                 │
           │ 🔩 iron ×1 ($8)        │ 🪵 wood ×1
           │                        │
           └───────────┬────────────┘
                       ↓
L2  ┌─────────────────────────────────┐
    │          🪚 木匠                │
    │         carpenter               │
    │   輸入: 🔩 iron ×1 + 🪵 wood ×1 │
    └──────────────┬──────────────────┘
                   │ 🪑 furniture ×1
                   ↓
    [商人收購 $34]
```

#### 👔 服飾鏈

```
L1  ┌─────────────┐          L2  ┌─────────────┐
    │ 🐑 牧羊人   │              │ 🔪 屠夫     │
    │  shepherd   │              │   butcher   │
    └──────┬──────┘              └──────┬──────┘
           │ 🧶 wool ×2                 │ ☁️ hide ×1
           ↓                            ↓
L2  ┌─────────────┐          L2  ┌─────────────┐
    │ 🧵 織工     │              │ 🟤 皮革匠   │
    │   weaver    │              │   tanner    │
    └──────┬──────┘              └──────┬──────┘
           │ 🧵 cloth ×1 ($7)           │ 🟤 leather ×1 ($11)
           │                            │
           └───────────┬────────────────┘
                       ↓
L3  ┌─────────────────────────────────────┐
    │            👕 裁縫                  │
    │            tailor                   │
    │   輸入: 🧵 cloth ×1 + 🟤 leather ×1 │
    └──────────────┬──────────────────────┘
                   │ 👕 clothes ×1
                   ↓
    [商人收購 $33]
```

#### 🏪 貿易系統

```
    ┌─────────────────────┐
    │    [外部世界]        │
    └──────────┬──────────┘
               │
               ↓
    ┌─────────────────────┐
    │     🏪 商人         │
    │     merchant        │
    │  (收購利潤 +20%)    │
    └──────────┬──────────┘
               │
    ┌──────────┼──────────┐
    ↓          ↓          ↓
 [木匠]    [裁縫]    [村民變賣]
  $18       $23       原價
```

### 2.2 供應鏈定義 ✅ 已實作

```python
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
    "tanner": ["butcher"],              # 皮革匠 ← 屠夫（羊皮）⚠️ 改為屠夫
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
| 鐵礦 | ore | 🪨 | 礦工 |
| 木材 | wood | 🪵 | 伐木工 |
| 羊毛 | wool | 🧶 | 牧羊人（剪羊毛）|
| 羊皮 | hide | ☁️ | 屠夫（宰殺羊）|

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
    "hide": {"name": "羊皮", "icon": "☁️", "category": "material", "stack_max": 10},
    
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

### 3.3 物品價格表

經濟平衡設計：L1=$80/分, L2=$100/分, L3=$80/分（麵包師）, L3=$120/分（裁縫）

#### 原料與半成品價格（MATERIAL_PRICES）

| 物品 | ID | 💰 價格 | 層級 | 來源 |
|------|-----|--------|------|------|
| 🌾 穀物 | grain | $2 | L1 | 農夫 |
| 🪨 鐵礦 | ore | $3 | L1 | 礦工 |
| 🪵 木材 | wood | $2 | L1 | 伐木工 |
| 🧶 羊毛 | wool | $2 | L1 | 牧羊人 |
| ☁️ 羊皮 | hide | $4 | L2 | 屠夫 |
| 🌫️ 麵粉 | flour | $3 | L2 | 磨坊主 |
| 🔩 鐵錠 | iron | $8 | L2 | 鐵匠 |
| 🧵 布料 | cloth | $7 | L2 | 織工 |
| 🟤 皮革 | leather | $10 | L2 | 皮革匠 |
| 🥩 生肉 | meat_raw | $5 | L2 | 屠夫 |
| 🍞 麵包 | bread | $4 | L3 | 麵包師 |

#### 商人收購價（MERCHANT_BUY_PRICES）

所有原料都可收購，商人賺 20% 出口利潤。

**過剩條件**：同類物品（背包+地上）>= 該物品門檻，或 現金 < 12 且肚子餓

| 物品 | ID | 💰 收購價 | 層級 | 過剩門檻 |
|------|-----|----------|------|----------|
| 🌾 穀物 | grain | $2 | L1 | ≥ 20 |
| 🪨 礦石 | ore | $3 | L1 | ≥ 20 |
| 🪵 木材 | wood | $2 | L1 | ≥ 20 |
| 🧶 羊毛 | wool | $2 | L1 | ≥ 20 |
| 🌫️ 麵粉 | flour | $3 | L2 | ≥ 10 |
| 🔩 鐵錠 | iron | $8 | L2 | ≥ 10 |
| 🧵 布料 | cloth | $7 | L2 | ≥ 10 |
| 🟤 皮革 | leather | $10 | L2 | ≥ 10 |
| ☁️ 獸皮 | hide | $4 | L2 | ≥ 10 |
| 🥩 生肉 | meat_raw | $5 | L2 | ≥ 10 |
| 📏 木板 | plank | $6 | L2 | ≥ 10 |
| 🍞 麵包 | bread | $4 | L3 | ≥ 15 |
| 🍖 熟肉 | meat | $6 | L3 | ≥ 10 |
| 🪑 家具 | furniture | $34 | L3 | ≥ 1 |
| 👕 衣服 | clothes | $35 | L3 | ≥ 1 |

#### 特殊價格

| 項目 | 💰 價格 | 備註 |
|------|--------|------|
| 🐑 活羊 | $10 | 牧羊人賣給屠夫 |

#### 工具價格

| 工具 | ID | 💰 價格 | 耐久 | 使用職業 |
|------|-----|--------|------|----------|
| ⛏️ 鋤頭 | hoe | $12 | 100 | 農夫 |
| ⛏️ 鶴嘴鋤 | pickaxe | $15 | 80 | 礦工 |
| 🪓 斧頭 | axe | $14 | 90 | 伐木工 |
| ✂️ 剪刀 | shears | $10 | 120 | 牧羊人、裁縫 |
| 🔪 屠刀 | cleaver | $12 | 100 | 屠夫 |
| 🔨 錘子 | hammer | $15 | 100 | 鐵匠 |
| 🪚 鋸子 | saw | $14 | 70 | 木匠 |
| 🔪 刮刀 | scraper | $10 | 80 | 皮革匠 |

### 3.4 物品堆疊

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
        "input": [],  # 透過羊系統，剪羊毛
        "output": [{"item_id": "wool", "quantity": 2}],
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
        "input": [],  # 透過羊系統購買活羊
        "output": [
            {"item_id": "meat_raw", "quantity": 2},
            {"item_id": "hide", "quantity": 1},
        ],
        "tool": "cleaver",
        "work_time": 2,
        "note": "宰殺 1 隻羊 → 獲得生肉 + 羊皮",
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

# 原料 → 生產者對應表 ✅ 已更新
MATERIAL_PRODUCERS = {
    "grain": "farmer",          # 穀物 ← 農夫
    # livestock 透過羊系統處理，不是物品
    "ore": "miner",             # 鐵礦 ← 礦工
    "wood": "lumberjack",       # 木材 ← 伐木工
    "wool": "shepherd",         # 羊毛 ← 牧羊人（剪羊毛）
    "hide": "butcher",          # 羊皮 ← 屠夫（宰殺羊）⚠️ 改為屠夫
    "flour": "miller",          # 麵粉 ← 磨坊主
    "meat_raw": "butcher",      # 生肉 ← 屠夫
    "iron": "blacksmith",       # 鐵錠 ← 鐵匠
    "plank": "carpenter",       # 木板 ← 木匠
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

### Phase 1：基礎物品系統 ✅
- [x] 物品資料結構
- [x] 村民背包系統（5 格）
- [x] 地上物品系統（含 owner_id）
- [x] 物品撿起/放下

### Phase 2：工具系統 ✅
- [x] 工具耐久度（每次工作 -5%）
- [x] 工作需要工具檢查
- [x] 工具損壞邏輯（損壞後自動購買）

### Phase 3：生產系統 ✅
- [x] 生產配方
- [x] 工作產出物品（背包滿則放地上）
- [x] 原料消耗

### Phase 4：交易系統 ✅
- [x] 物品價格
- [x] 買賣交易（自動找供應商）
- [x] 金錢流動

### Phase 5：AI 整合 ✅
- [x] 村民自動購買原料
- [x] 村民自動出售產品（賣給商人）
- [x] 村民消費行為（買食物）
- [x] 動態行為選項（根據庫存/金錢調整可用行為）

### Phase 6：羊系統 ✅
- [x] 羊實體（位置、擁有者、羊毛狀態）
- [x] 牧羊人剪羊毛
- [x] 屠夫向牧羊人購買活羊
- [x] 屠夫宰殺羊（產出 meat_raw + hide）
- [x] 羊繁殖系統

---

## 11. 羊系統 ✅ 已實作

### 11.1 羊實體

```python
sheep = {
    "id": "sheep_001",
    "owner_id": "villager_shepherd",  # 擁有者（牧羊人）
    "x": 45, "y": 30,                 # 位置
    "is_adult": True,                 # 是否成羊
    "wool_grown": True,               # 羊毛是否長好
    "pasture_id": "pasture_01"        # 所屬牧場
}
```

### 11.2 牧羊人工作流程

```
1. 檢查是否有羊毛長好的羊
   ├─ 有 → 走到羊的位置 → 剪羊毛 → 獲得 wool x2
   └─ 沒有 → 無法工作（go_work 返回空任務）

2. 剪毛後
   └─ 該羊 wool_grown = False
   └─ 等待一段時間後羊毛重新長好
```

### 11.3 屠夫工作流程

```
1. 檢查是否擁有羊
   ├─ 有 → 走到羊的位置 → 宰殺 → 獲得 meat_raw x2 + hide x1
   └─ 沒有 → 嘗試購買羊

2. 購買羊流程
   ├─ 找牧羊人
   ├─ 檢查牧羊人是否有多餘的羊（> 2 隻成羊）
   ├─ 有 → 走到牧羊人 → 付錢 $15 → 羊的 owner_id 改為屠夫
   └─ 沒有 → 無法工作

3. 宰殺後
   └─ 羊從遊戲中移除
   └─ 屠夫獲得 meat_raw + hide
```

### 11.4 羊繁殖

```python
# 每隔一段時間，牧羊人的羊會繁殖
# 條件：至少有 2 隻成羊
# 結果：新增 1 隻小羊（is_adult=False）
# 小羊成長後變成成羊
```

---

## 12. 商人收購系統 ✅ 已實作

### 12.1 可賣給商人的產品

所有物品都可賣給商人，價格如下：

| 層級 | 物品 | ID | 收購價 |
|------|------|-----|--------|
| L1 | 🌾 穀物 | grain | $2 |
| L1 | 🪨 礦石 | ore | $3 |
| L1 | 🪵 木材 | wood | $2 |
| L1 | 🧶 羊毛 | wool | $2 |
| L2 | 🌫️ 麵粉 | flour | $3 |
| L2 | 🔩 鐵錠 | iron | $8 |
| L2 | 🧵 布料 | cloth | $7 |
| L2 | 🟤 皮革 | leather | $10 |
| L2 | ☁️ 獸皮 | hide | $4 |
| L2 | 🥩 生肉 | meat_raw | $5 |
| L2 | 📏 木板 | plank | $6 |
| L3 | 🍞 麵包 | bread | $4 |
| L3 | 🍖 熟肉 | meat | $6 |
| L3 | 🪑 家具 | furniture | $34 |
| L3 | 👕 衣服 | clothes | $35 |

### 12.2 賣東西流程

```
1. AI 決策時檢查村民背包是否有可賣產品
   ├─ 有 → 系統提示加入 sell_goods 選項（最高優先）
   └─ 沒有 → 不顯示 sell_goods

2. 村民選擇 sell_goods
   └─ 找到商人 → 走過去 → 賣出 → 金錢增加

3. 賣出邏輯
   └─ 物品從背包移除
   └─ 村民金錢 += 收購價 × 數量
```

### 12.3 動態行為選項

AI 的可用行為根據狀態動態調整：

| 條件 | go_work | sell_goods |
|------|---------|------------|
| 有產品可賣 | ✅ | ✅ **最優先** |
| 有原料 | ✅ | - |
| 沒原料但有錢+供應商有貨 | ✅ | - |
| 沒原料且買不到 | ❌ 隱藏 | - |

---

## 13. UI 更新

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

## 14. 物件導向設計

### 14.1 設計原則

使用 Python `dataclass` 將物品、職業、村民定義為類別，好處：
- ✅ 型別提示、IDE 自動補全
- ✅ 方法封裝、邏輯集中
- ✅ 易於維護和擴展

### 14.2 物品類別

```python
from dataclasses import dataclass
from typing import Optional, List

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


@dataclass
class ItemStack:
    """物品堆疊（背包/地上的一格）"""
    item_type: ItemType        # 物品類型
    quantity: int              # 數量
    durability: Optional[int]  # 當前耐久度（工具）
    owner_id: Optional[str]    # 擁有者 ID
    x: Optional[int] = None    # 地上位置 X
    y: Optional[int] = None    # 地上位置 Y
    
    def is_tool(self) -> bool:
        return self.item_type.category == "tool"
    
    def is_owned_by(self, villager_id: str) -> bool:
        return self.owner_id == villager_id or self.owner_id is None
    
    def use_durability(self, amount: int = 5) -> bool:
        """消耗耐久度，返回是否損壞"""
        if self.durability is not None:
            self.durability -= amount
            return self.durability <= 0
        return False
```

### 14.3 職業類別

```python
@dataclass
class OccupationType:
    """職業類型定義"""
    id: str                    # farmer, miller, baker...
    name: str                  # 農夫, 磨坊主, 麵包師...
    tier: int                  # 層級 1, 2, 3
    chain: str                 # 產業鏈: food, tool, clothing
    building: str              # 工作建築 ID
    
    # 工具需求
    required_tool: Optional[str] = None
    
    # 生產配方
    input_materials: List[tuple] = None   # [(item_id, quantity), ...]
    output_product: str = ""
    output_quantity: int = 0
    work_time: int = 2
    
    # 注意：已移除 work_start/work_end，工作時間由性格系統控制
```

### 14.4 職業定義範例

```python
OCCUPATIONS = {
    # === 食物鏈 L1 ===
    "farmer": OccupationType(
        id="farmer", name="農夫", tier=1, chain="food",
        building="farm",
        required_tool="hoe",
        input_materials=[],
        output_product="grain", output_quantity=2, work_time=2,
    ),
    
    # === 食物鏈 L2 ===
    "miller": OccupationType(
        id="miller", name="磨坊主", tier=2, chain="food",
        building="mill",
        required_tool=None,
        input_materials=[("grain", 1)],
        output_product="flour", output_quantity=2, work_time=2,
    ),
    
    # === 食物鏈 L3 ===
    "baker": OccupationType(
        id="baker", name="麵包師", tier=3, chain="food",
        building="bakery",
        required_tool=None,
        input_materials=[("flour", 1)],
        output_product="bread", output_quantity=2, work_time=2,
    ),
    
    # ... 其他職業
}
```

### 14.5 物品定義範例

```python
ITEM_TYPES = {
    # === 原料 ===
    "grain": ItemType(
        id="grain", name="穀物", icon="🌾",
        category="material", stack_max=10, price=2
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
        id="wool", name="羊毛", icon="🧶",
        category="material", stack_max=10, price=3
    ),
    
    # === 工具 ===
    "hoe": ItemType(
        id="hoe", name="鋤頭", icon="⛏️",
        category="tool", stack_max=1, durability_max=100, price=12
    ),
    "pickaxe": ItemType(
        id="pickaxe", name="鶴嘴鋤", icon="⛏️",
        category="tool", stack_max=1, durability_max=80, price=15
    ),
    
    # === 食物 ===
    "bread": ItemType(
        id="bread", name="麵包", icon="🍞",
        category="food", stack_max=10, price=3, hunger_restore=30
    ),
    "meat": ItemType(
        id="meat", name="肉品", icon="🍖",
        category="food", stack_max=10, price=6, hunger_restore=50
    ),
}
```

### 14.6 村民類別

```python
@dataclass
class Villager:
    """村民"""
    id: str
    name: str
    occupation: OccupationType
    
    # 背包（3 格）
    inventory: List[Optional[ItemStack]] = None
    
    # 數值
    money: int = 50
    hunger: int = 0
    energy: int = 100
    
    # 位置與狀態
    x: float = 0
    y: float = 0
    state: str = "idle"
    
    def __post_init__(self):
        if self.inventory is None:
            self.inventory = [None, None, None]
    
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
        for i, slot in enumerate(self.inventory):
            if slot and slot.item_type.id == item_stack.item_type.id:
                if slot.quantity + item_stack.quantity <= slot.item_type.stack_max:
                    slot.quantity += item_stack.quantity
                    return True
        
        # 找空格
        for i, slot in enumerate(self.inventory):
            if slot is None:
                self.inventory[i] = item_stack
                return True
        
        return False  # 背包滿了
```

### 14.7 檔案結構

```
backend/app/
├── models/
│   ├── __init__.py
│   ├── item.py          # ItemType, ItemStack
│   ├── occupation.py    # OccupationType
│   └── villager.py      # Villager
│
├── data/
│   ├── __init__.py
│   ├── items.py         # ITEM_TYPES 定義
│   ├── occupations.py   # OCCUPATIONS 定義
│   └── supply_chain.py  # 供應鏈關係
│
└── game/
    ├── economy.py       # 經濟系統邏輯
    └── ...
```

---

## 附錄：建築物對應

| 職業 | 建築物 | 英文 ID |
|------|--------|---------|
| 👨‍🌾 農夫 | 🌾 農田 | farm |
| 🌾 磨坊主 | 🏭 磨坊 | mill |
| 🔪 屠夫 | 🥩 肉舖 | butcher_shop |
| 🍞 麵包師 | 🥖 麵包店 | bakery |
| ⛏️ 礦工 | ⛰️ 礦場 | mine |
| 🪓 伐木工 | 🌲 伐木場 | lumber_camp |
| 🔨 鐵匠 | 🔥 鐵匠舖 | blacksmith |
| 🪚 木匠 | 🪵 木工坊 | carpentry |
| 🐑 牧羊人 | 🏕️ 牧場 | pasture |
| 🧵 織工 | 🧶 織坊 | weaver_shop |
| 🟤 皮革匠 | 🏠 皮革坊 | tannery |
| 👕 裁縫 | ✂️ 裁縫店 | tailor_shop |
| 🏪 商人 | 🛒 市集 | market |
