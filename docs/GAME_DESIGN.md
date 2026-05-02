# AI 中古世紀村莊模擬遊戲 - 設計文檔

## 📋 遊戲概述

| 項目 | 描述 |
|------|------|
| **類型** | 模擬市民 (Life Simulation) |
| **風格** | 中古世紀像素風 |
| **核心主題** | 社交互動 |
| **AI 驅動** | NPC 行為由 GPT API 決策 |
| **遊戲節奏** | 即時制 |
| **玩家角色** | 村莊中的一位村民 |

---

## 🗺️ 世界設定

### 村莊規模
- **地圖大小**: 96x96 格 (Tile-based)
- **建築物數量**: 28 棟（14 棟固定職業建築 + 14 棟民宅，每個 NPC 各一棟）
- **村民人數**: 14 個 NPC（每職業一人）+ 玩家

### 建築物配置

#### 固定職業建築（14 棟，每職業一棟）
| 建築 | 功能 | 相關職業 |
|------|------|----------|
| 農舍 (farm) | 種田生產穀物 | 農夫 |
| 磨坊 (mill) | 將穀物磨成麵粉 | 磨坊主 |
| 麵包坊 (bakery) | 烤麵包 | 麵包師 |
| 屠夫鋪 (butcher_shop) | 宰殺羊隻產出生肉與羊皮 | 屠夫 |
| 牧場 (pasture) | 養羊、剪羊毛 | 牧羊人 |
| 礦場 (mine) | 挖鐵礦 | 礦工 |
| 伐木場 (lumber_camp) | 砍木材 | 伐木工 |
| 鐵匠舖 (blacksmith) | 煉鐵錠、賣工具 | 鐵匠 |
| 木工坊 (carpentry) | 製作家具 | 木匠 |
| 織工坊 (weaver_shop) | 將羊毛織成布料 | 織工 |
| 製革坊 (tannery) | 將羊皮鞣成皮革 | 皮革匠 |
| 裁縫店 (tailor_shop) | 製作衣服 | 裁縫 |
| 酒館 (tavern) | 社交中心、賣啤酒、聽八卦 | 酒保 |
| 廣場 (plaza) | 社交、商人駐點、集會 | 商人 |

#### 民宅（14 棟，每個 NPC 一棟）
- 每個 NPC 都會自動分配一棟住所，內含床、灶台等基本家具

#### 🔮 未來功能（規劃中）
- **教堂** + 神父職業：祈禱、婚禮、葬禮等社交活動

### 地形元素
- **可通行**: 道路、草地、地板、門
- **不可通行**: 水、牆壁、建築外牆
- **裝飾**: 樹木、花叢、柵欄、告示牌

---

## 👥 村民系統

### 村民屬性

```javascript
Villager = {
  // 基本資料
  id: "villager_001",
  name: "艾德蒙",
  occupation: "blacksmith",  // 14 種職業之一

  // 位置
  x: 45,
  y: 32,

  // 狀態數值 (0-100)
  stats: {
    energy: 80,      // 體力
    satiety: 70,     // 飽足度
    social: 50,      // 社交需求
    happiness: 65    // 心情度
  },

  // 金錢
  money: 50,

  // 性格特質（7 維度各抽一個，共 4 個有效特質）
  personality: ["extrovert", "friendly", "trusting", "early_bird"],

  // 喜好系統（生成時隨機分配）
  preferences: {
    hobbies: ["釣魚", "下棋"],
    favorite_foods: ["麵包"],
    dislikes: ["吵雜"]
  },

  // 記憶系統（對話結束後 AI 生成的摘要）
  memories: [
    { with: "瑪莉", summary: "在廣場聊到天氣，雙方情緒愉快" }
  ],

  // 關係（dict by villager_id）
  relationships: {
    "villager_002": { affection: 35, familiarity: 50 }
  },

  // 背包（5 格，每格物品或工具）
  inventory: [
    { item_id: "hammer", durability: 75 },
    { item_id: "iron", quantity: 3 },
    null, null, null
  ],

  // 當前狀態
  state: "idle",   // idle, walking, working, sleeping, talking, waiting_social
  action_history: [...]  // 最近行為與成功/失敗結果
}
```

### 關係系統

```javascript
Relationship = {
  villagerA: "villager_001",
  villagerB: "villager_002",
  
  // 關係數值 (-100 到 100)
  affection: 35,      // 好感度
  trust: 20,          // 信任度
  familiarity: 50,    // 熟悉度
  
  // 關係標籤
  tags: ["neighbor", "friend"],  // 可能的值: family, friend, rival, lover, stranger, neighbor
  
  // 互動歷史摘要 (給 AI 參考)
  summary: "經常在水井相遇打招呼，曾一起在酒館喝酒"
}
```

### 性格特質池（7 維度對立系統）

每個村民從 7 個維度中各抽一個正面或反面特質，共 4 個有效特質。

| 維度 | 正面 | 反面 | 影響 |
|------|------|------|------|
| **social** | `extrovert`（外向）喜歡社交，常去廣場 | `introvert`（內向）偏好獨處，專注工作 | 聊天觸發機率 ×2 / ×0.5 |
| **temper** | `friendly`（友善）樂於助人 | `grumpy`（暴躁）討厭被打擾 | 聊天後好感度 +2 / -1 |
| **trust** | `trusting`（信任）容易相信他人 | `suspicious`（多疑）對陌生人警戒 | 熟悉度提升 ×1.5 / ×0.7 |
| **romance** | `romantic`（浪漫）容易產生好感 | `reserved`（矜持）感情內斂 | 異性好感度 ×1.5 / ×0.7 |
| **courage** | `brave`（勇敢）狀態偏低也敢撐 | `timid`（膽小）狀態稍低就想處理 | 對陌生人搭話機率 ×2 / ×0.3 |
| **outlook** | `optimistic`（樂觀）傾向繼續工作 | `pessimistic`（悲觀）傾向先滿足需求 | 心情變化幅度 |
| **schedule** | `early_bird`（早起鳥）白天積極 | `night_owl`（夜貓子）夜間活躍 | 工作效率 / 體力下降速度（見下表） |

**作息性格效果（schedule 維度）**

| 效果 | 時段 | early_bird | night_owl |
|------|------|------------|-----------|
| 工作效率 | 白天（6:00-18:00） | +5% | -5% |
|          | 晚上（18:00-6:00） | -5% | +5% |
| 體力下降 | 白天 | ×0.8（慢） | ×1.2（快） |
|          | 晚上 | ×1.2（快） | ×0.8（慢） |

---

## 🏠 地圖物件系統

### 物件定義結構

```javascript
MapObject = {
  id: "obj_tavern_bar",
  name: "酒館吧台",
  type: "interactive",        // interactive, decorative, functional
  position: { x: 45, y: 32 },
  size: { width: 2, height: 1 },
  
  // 可執行的動作
  actions: [
    {
      id: "buy_drink",
      name: "買酒",
      duration: 5000,          // 執行時間 (毫秒)
      requirements: {
        money: 5
      },
      effects: {
        social: +10,
        happiness: +5,
        money: -5
      }
    },
    {
      id: "chat_bartender",
      name: "與酒保聊天",
      duration: 8000,
      requirements: {},
      effects: {
        social: +15
      },
      triggersAI: true          // 需要 AI 生成對話
    },
    {
      id: "listen_gossip",
      name: "聽八卦",
      duration: 10000,
      requirements: {},
      effects: {
        social: +5
      },
      mayLearnInfo: true        // 可能獲得情報
    }
  ],
  
  // 社交熱點設定
  socialHotspot: true,          // 其他 NPC 會聚集
  ambiance: "lively"            // 氛圍標籤，影響 AI 對話風格
}
```

### 物件類型清單

#### 功能型物件（滿足需求）
| 物件 | 動作 | 效果 |
|------|------|------|
| 床 | 睡覺 | 恢復體力 |
| 灶台 | 煮生肉 | 將生肉煮成熟肉 |
| 工作建築 | 工作 | 生產物品、賺錢 |

#### 社交型物件（觸發互動）
| 物件 | 動作 | 社交效果 |
|------|------|----------|
| 酒館吧台 | 跟酒保買啤酒、和其他人聊天 | 高社交機會（廣場+酒吧內相遇距離放寬至 3 格） |
| 廣場 | 自由聊天 | 對話觸發點（同上） |

---

## 🤖 AI 決策系統

### 決策觸發時機
1. 村民完成當前動作後
2. 村民遇到其他村民時
3. 發生突發事件時
4. 玩家主動與 NPC 對話時

### 實際呼叫方式

決策呼叫使用 OpenAI **chat.completions API + function calling (tools)**，動作集合用 enum 約束 AI 只能從規則層核可的選項中選擇。

```python
# backend/app/game/villager_ai.py - 決策呼叫
response = await self.client.chat.completions.create(
    model="gpt-5.4-nano",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},  # 靜態,內含產業鏈與行為原則
        {"role": "user", "content": destination_prompt}  # 含村民狀態、可用動作、記憶
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "choose_action",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": available_actions},
                    "reason": {"type": "string", "description": "選擇原因（15 字內）"},
                    # 視動作需要可能還有 item / target / buy_target
                },
                "required": ["action", "reason"],
            }
        }
    }],
    tool_choice={"type": "function", "function": {"name": "choose_action"}},
    max_completion_tokens=150
)
result = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
# {"action": "go_buy_food", "reason": "飽足偏低先買麵包"}
```

可選動作清單由規則層決定（見 `_get_available_destination_actions`）：
`go_work / go_buy_material / go_buy_food / go_buy_tool / go_sell / eat / go_cook / go_pickup / go_sleep / go_plaza / go_bar / wander / talk / buy_beer / idle`

### 對話與相遇生成

兩村民相遇時呼叫另一個 chat.completions（無 tools），生成 JSON 形式的對話內容，傳入雙方狀態、性格、心情、記憶與村莊賣家清單。對話結束後再呼叫一次生成總結與好感變化（-3 ~ +3）。詳見 `backend/app/game/conversation.py`。

### API 成本控制策略

| 策略 | 說明 |
|------|------|
| **批次限制** | 每 tick 最多處理 2 個村民決策 |
| **優先級排序** | 玩家附近的村民優先決策 |
| **決策節流** | 同一村民至少間隔 4 秒才能再次請求 |
| **prompt 快取** | system prompt 維持靜態以利 OpenAI prompt cache（命中時 input token 約 1/4 計費） |

---

## 🚶 路徑尋找系統 (A*)

### Tile 地圖結構

```javascript
TileMap = {
  width: 96,
  height: 96,
  tileSize: 16,  // 像素
  
  layers: {
    ground: [...],      // 地面層 (grass, road, water)
    buildings: [...],   // 建築層
    objects: [...],     // 物件層
    collision: [...]    // 碰撞層 (0=可通行, 1=阻擋)
  }
}
```

### A* 實作要點

```javascript
// 路徑請求
function findPath(start, goal, collisionMap) {
  // 使用 A* 演算法
  // 啟發函數: 曼哈頓距離
  // 回傳: [{x, y}, {x, y}, ...] 路徑點陣列
}

// 移動系統
Villager.prototype.moveAlongPath = function(deltaTime) {
  if (this.path.length === 0) return;
  
  const nextTile = this.path[0];
  const speed = 2; // tiles per second
  
  // 移動向下一格
  // 到達後 shift 路徑陣列
  // 路徑清空時觸發 onArrived()
}
```

### 路徑中斷處理

| 情況 | 處理方式 |
|------|----------|
| 路徑被阻擋 | 重新計算路徑 |
| 遇到其他村民 | 觸發社交判定，可能停下 |
| 緊急事件 | 清除路徑，重新 AI 決策 |
| 抵達目的地 | 執行互動動作 |

---

## 🎮 玩家系統

### 玩家與 NPC 的差異

| 項目 | NPC | 玩家 |
|------|-----|------|
| 行為決策 | GPT API | 玩家選擇 |
| 移動 | 自動 A* | 點擊移動 或 WASD |
| 互動 | 自動執行 | 選單選擇 |
| 對話 | AI 生成 | 玩家輸入 或 選項 |

### 玩家輸入

```javascript
// 移動
- 點擊地面: 計算 A* 路徑，自動移動
- WASD / 方向鍵: 直接控制移動

// 互動
- 點擊物件/NPC: 顯示動作選單
- 選擇動作: 執行對應行為

// 介面
- ESC: 暫停選單
- I: 背包/狀態
- M: 地圖
- Tab: 村民關係總覽
```

### 動作選單設計

```
┌─────────────────────┐
│   酒館吧台          │
├─────────────────────┤
│ > 買酒 (5金幣)      │
│   與酒保聊天        │
│   聽八卦            │
│   離開              │
└─────────────────────┘
```

---

## 🔄 遊戲循環

### 主循環結構

```javascript
function gameLoop(timestamp) {
  const deltaTime = timestamp - lastTimestamp;
  
  // 1. 更新遊戲時間 (日夜循環)
  updateGameTime(deltaTime);
  
  // 2. 處理玩家輸入
  handlePlayerInput();
  
  // 3. 更新所有村民
  for (const villager of villagers) {
    if (villager.isPlayer) continue;
    
    switch (villager.currentState.action) {
      case 'idle':
        // 觸發 AI 決策 (需節流)
        requestAIDecision(villager);
        break;
      case 'walking':
        // 沿路徑移動
        villager.moveAlongPath(deltaTime);
        break;
      case 'interacting':
        // 更新動作進度
        villager.updateAction(deltaTime);
        break;
    }
    
    // 檢查社交觸發
    checkSocialEncounters(villager);
  }
  
  // 4. 更新玩家
  updatePlayer(deltaTime);
  
  // 5. 處理事件佇列
  processEventQueue();
  
  // 6. 渲染
  render();
  
  requestAnimationFrame(gameLoop);
}
```

### 時間系統

```javascript
TimeSystem = {
  gameSpeed: 60,          // 1 現實秒 = 60 遊戲秒 (可調整)
  currentTime: {
    day: 1,
    hour: 8,
    minute: 0
  },
  
  // 時段定義
  periods: {
    dawn: [5, 7],         // 黎明
    morning: [7, 12],     // 上午
    afternoon: [12, 17],  // 下午
    evening: [17, 20],    // 傍晚
    night: [20, 5]        // 夜晚
  }
}
```

---

## 💾 資料持久化

### 存檔結構

```
/saves
  └── /village_001
      ├── meta.json           # 存檔資訊 (名稱、遊玩時間、截圖)
      ├── map.json            # 地圖資料
      ├── villagers.json      # 村民狀態
      ├── relationships.json  # 關係網絡
      ├── player.json         # 玩家特定資料
      └── events.json         # 事件記錄
```

### 地圖 JSON 範例

```javascript
// map.json
{
  "seed": 12345,              // 隨機種子 (可重現)
  "size": { "width": 96, "height": 96 },
  "buildings": [
    {
      "id": "building_001",
      "type": "tavern",
      "name": "醉酒豬酒館",
      "position": { "x": 30, "y": 20 },
      "size": { "width": 8, "height": 6 },
      "objects": [
        { "type": "bar_counter", "localPos": { "x": 2, "y": 1 } },
        { "type": "table", "localPos": { "x": 5, "y": 3 } }
      ]
    }
    // ... 其他建築
  ],
  "terrain": {
    "ground": [[0,0,1,1,...], ...],     // 0=草地, 1=道路, 2=水
    "collision": [[0,0,0,1,...], ...]   // 0=可通行, 1=阻擋
  }
}
```

---

## 🎨 視覺風格

### 像素規格

| 項目 | 規格 |
|------|------|
| Tile 大小 | 16x16 像素 |
| 角色大小 | 16x24 像素 (含陰影) |
| 調色盤 | 限制 32 色 (中古世紀色調) |
| 視角 | 俯視角 (Top-down) 或 斜45度 |

### Canvas 繪製層次

```
Layer 0: 地面 (草地、道路、水)
Layer 1: 地面裝飾 (花、石頭)
Layer 2: 建築底部 / 物件
Layer 3: 角色 (依 Y 軸排序)
Layer 4: 建築頂部 / 樹冠
Layer 5: 天氣效果
Layer 6: UI 層
```

---

## 🏗️ 已實作的子系統

### 經濟與產業鏈
14 種職業組成的食物 / 器具 / 服飾 三條產業鏈，從 L1 原料 → L2 半成品 → L3 成品逐層加工，村民間自由交易。
**詳見 [economy-system-design.md](economy-system-design.md)** — 含完整職業表、配方、價格、商人收購。

### 工具耐久度
- 8 種職業需要工具（農夫鋤頭、礦工鶴嘴鋤、伐木工斧頭、牧羊人剪刀、屠夫屠刀、鐵匠錘子、木匠鋸子、皮革匠刮刀）
- 每次工作消耗 5 點耐久；歸零後工具直接消失
- 沒工具無法工作 → 必須去鐵匠買新的
- 詳見 economy-system-design.md「工具耐久度」段落

### 對話與記憶系統
- 兩村民距離小於 1.5 格（廣場/酒吧內 3 格）會觸發相遇
- 由 AI 生成對話內容，最多 6 輪
- 對話結束後 AI 生成摘要與好感變化（-3 ~ +3），存入 `memories`
- 好感度與熟悉度影響：對話風格、是否搭話、好感變化幅度
- 對話冷卻時間：避免同一對村民反覆觸發

### 商人收購系統
- 商人主動收購所有非工具物品（含原料、半成品、成品）
- 收購價賺 20% 出口利潤；L3 成品有更高溢價（家具 $33、衣服 $35）
- 過剩門檻：庫存達門檻自動列為可賣，或現金 < $12 且飢餓時降低門檻
- 詳見 supply_chain.py 的 `MERCHANT_BUY_PRICES` 與 `EXCESS_THRESHOLDS`

### 天氣系統
4 種天氣：晴天 ☀️、多雲 ⛅、下雨 🌧️、暴風雨 ⛈️。

| 天氣 | 室外體力消耗加成 | 畫面變暗 |
|------|------------------|----------|
| 晴天 | 0 | 0% |
| 多雲 | 0 | 10% |
| 下雨 | +1/tick | 20% |
| 暴風雨 | +2/tick | 40% |

天氣會影響 AI 決策（雨夜傾向待室內），對話內容也會引述天氣作為話題。

---

## 🛠️ 技術架構

### 目前架構 ✅

| 層級 | 技術 | 說明 |
|------|------|------|
| **前端** | JavaScript Canvas + Nginx | 渲染、使用者輸入 |
| **後端** | Python FastAPI | 遊戲邏輯、AI 決策、A* 路徑 |
| **通訊** | WebSocket | 即時雙向通訊 |
| **容器** | Docker Compose | 一鍵部署 |
| **AI** | OpenAI GPT API | NPC 行為決策 |

### 專案結構

```
/ai-city
├── docker-compose.yml       # Docker 編排
├── .env                     # 環境變數 (API Key)
├── README.md
│
├── /frontend                # 前端 (Nginx 容器)
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   └── /src
│       ├── main.js          # 入口點
│       ├── /api
│       │   └── ApiClient.js # WebSocket 客戶端
│       ├── /core
│       │   ├── Game.js      # 遊戲主類
│       │   ├── InputHandler.js
│       │   └── TimeSystem.js
│       ├── /entities
│       │   ├── Entity.js
│       │   ├── Villager.js
│       │   ├── VillagerManager.js
│       │   └── Player.js
│       ├── /render
│       │   ├── Renderer.js  # 渲染 (含對話泡泡)
│       │   └── Camera.js
│       ├── /world
│       │   └── GameMap.js
│       └── /ui
│           └── UIManager.js
│
├── /backend                 # 後端 (Python 容器)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── /app
│       ├── main.py          # FastAPI 入口
│       ├── /api
│       │   ├── ai.py            # AI 決策路由
│       │   ├── game.py          # 遊戲狀態與 WebSocket
│       │   └── villagers.py     # 村民資訊路由
│       ├── /data
│       │   ├── items.py         # 物品定義（價格/飽足度的 single source of truth）
│       │   ├── occupations.py   # 14 職業定義
│       │   ├── personalities.py # 7 維度性格系統
│       │   ├── supply_chain.py  # 供應鏈與商人收購
│       │   └── weather.py       # 天氣類型
│       ├── /models
│       │   └── item.py          # ItemType / ItemStack
│       └── /game
│           ├── game_state.py    # 遊戲狀態管理
│           ├── game_loop.py     # 遊戲主循環
│           ├── map_generator.py # 地圖隨機生成（後端負責）
│           ├── villager_ai.py   # GPT AI 決策（含對話與相遇生成）
│           ├── conversation.py  # 對話系統
│           ├── inventory.py     # 背包與工具耐久
│           ├── production.py    # 生產與交易執行
│           ├── task_effects.py  # 任務副作用（吃、睡、買等）
│           ├── target_resolver.py # 動作目標座標解析
│           ├── sheep.py         # 羊隻系統
│           └── pathfinding.py   # A* 路徑尋找
│
└── /saves                   # 存檔目錄
```

### 資料流程

```
┌─────────────────────────────────────────────────────────────┐
│                      Python 後端                             │
│  GameLoop → AI 決策 → 路徑計算 → 更新狀態 → WebSocket 廣播  │
└─────────────────────────────────────────────────────────────┘
                              ↓ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                      JavaScript 前端                         │
│  接收狀態 → 位置插值 → Canvas 渲染 → 對話泡泡顯示           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 開發階段規劃

### Phase 1: 基礎建設 ✅
- [x] 遊戲設計文檔
- [x] 專案初始化
- [x] Canvas 渲染系統
- [x] Tile 地圖系統
- [x] 地圖隨機生成
- [x] 基本角色顯示與移動

### Phase 2: 核心系統 ✅
- [x] A* 路徑尋找 (Python 後端)
- [x] 村民狀態系統
- [x] 物件互動系統
- [x] 玩家控制

### Phase 3: AI 整合 ✅
- [x] GPT API 串接
- [x] 行為決策系統
- [x] 對話泡泡顯示
- [ ] 對話生成 (玩家對話)
- [ ] 社交互動判定

### Phase 4: 架構升級 ✅
- [x] Python FastAPI 後端
- [x] Docker Compose 容器化
- [x] WebSocket 即時通訊
- [x] 後端遊戲主循環

### Phase 5: 完善
- [ ] 關係系統完善
- [ ] 記憶系統完善
- [ ] 事件系統
- [ ] UI 完善
- [ ] 存檔/讀檔

### Phase 6: 潤色
- [ ] 像素美術完善
- [ ] 音效/音樂
- [ ] 平衡調整
- [ ] 測試優化

---

## 🔑 環境設定

### 快速啟動

```bash
# 1. 複製環境變數範例
cp .env.example .env

# 2. 編輯 .env，填入 API Key
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-5.4-nano  # 或其他模型

# 3. 啟動 Docker Compose
docker-compose up --build -d

# 4. 開啟瀏覽器
http://localhost:4000
```

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API 金鑰 (必填) |
| `OPENAI_MODEL` | gpt-5.4-nano | 使用的模型 |
| `DEBUG_OPENAI` | true | 是否顯示 API 請求日誌 |

---

## 📝 備註

- 地圖一旦生成就會持久保存，除非玩家手動刪除存檔
- ⚠️ 必須提供 OpenAI API Key 才能啟動（無 fallback、無離線模式）
- 村民行為由 AI 決定，後端計算 A* 路徑
- 前端只負責渲染和使用者輸入
