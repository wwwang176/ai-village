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
- **地圖大小**: 64x64 或 80x80 格 (Tile-based)
- **建築物數量**: 10 棟
- **村民人數**: 30 人 (含玩家)

### 建築物配置

#### 必要建築 (5 棟，固定生成)
| 建築 | 功能 | 相關職業 |
|------|------|----------|
| 酒館 | 社交中心、買酒、聽八卦 | 酒保 |
| 教堂 | 祈禱、婚禮、葬禮 | 神父 |
| 市集廣場 | 交易、公告、集會 | 商人 |
| 鐵匠舖 | 製造/修理工具 | 鐵匠 |
| 水井 | 公共設施、社交點 | - |

#### 隨機建築 (5 棟，從池中抽選)
- 民宅 (村民住所)
- 麵包坊
- 農舍
- 旅店
- 裁縫店
- 磨坊
- 藥草店

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
  age: 32,
  gender: "male",
  occupation: "blacksmith",  // 職業
  residence: "building_007", // 住所
  
  // 狀態數值 (0-100)
  stats: {
    energy: 80,      // 體力
    hunger: 30,      // 飢餓度
    social: 50,      // 社交需求
    happiness: 65,   // 快樂度
    health: 90       // 健康
  },
  
  // 性格特質 (2-3個)
  personality: ["friendly", "hardworking", "curious"],
  
  // 記憶系統
  memories: [
    { event: "與瑪莉在水井聊天", timestamp: 1234567, sentiment: "positive" },
    { event: "被約翰拒絕借錢", timestamp: 1234000, sentiment: "negative" }
  ],
  
  // 日程傾向
  schedule: {
    wakeUpTime: 6,    // 早上6點起床
    sleepTime: 22,    // 晚上10點睡覺
    workHours: [8, 12, 14, 18]  // 工作時段
  },
  
  // 當前狀態
  currentState: {
    action: "walking",           // idle, walking, interacting, sleeping
    targetPosition: { x: 45, y: 32 },
    path: [],                    // A* 計算的路徑
    currentActivity: null        // 正在進行的活動
  }
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

### 性格特質池

#### 正面特質
- `friendly` - 友善：更常主動社交
- `hardworking` - 勤勞：工作時間更長
- `generous` - 慷慨：願意幫助他人
- `optimistic` - 樂觀：快樂度下降較慢
- `curious` - 好奇：喜歡探索和聊天

#### 負面特質
- `greedy` - 貪婪：重視金錢
- `lazy` - 懶惰：經常休息
- `suspicious` - 多疑：信任他人較慢
- `grumpy` - 暴躁：容易起衝突
- `gossip` - 愛八卦：會傳播消息

#### 中性特質
- `introvert` - 內向：社交需求較低
- `extrovert` - 外向：社交需求較高
- `romantic` - 浪漫：重視愛情關係
- `religious` - 虔誠：常去教堂

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

#### 功能型物件 (滿足需求)
| 物件 | 動作 | 效果 |
|------|------|------|
| 床 | 睡覺 | 恢復體力 |
| 餐桌 | 進食 | 降低飢餓 |
| 水井 | 打水 | 取得水、社交機會 |
| 工作台 | 工作 | 賺錢 |
| 椅子 | 坐下 | 輕微恢復 |
| 爐火 | 取暖 | 冬季恢復健康 |

#### 社交型物件 (觸發互動)
| 物件 | 動作 | 社交效果 |
|------|------|----------|
| 酒館吧台 | 買酒、聊天 | 高社交機會 |
| 教堂長椅 | 祈禱 | 遇見其他村民 |
| 市集攤位 | 買賣 | 對話觸發點 |
| 公共長凳 | 休息 | 隨機搭話 |
| 公告板 | 閱讀 | 獲取資訊 |

---

## 🤖 AI 決策系統

### 決策觸發時機
1. 村民完成當前動作後
2. 村民遇到其他村民時
3. 發生突發事件時
4. 玩家主動與 NPC 對話時

### API 請求格式

```javascript
// 行為決策請求
{
  "type": "behavior_decision",
  "villager": {
    "name": "艾德蒙",
    "personality": ["friendly", "hardworking"],
    "currentStats": {
      "energy": 60,
      "hunger": 40,
      "social": 30
    },
    "recentMemories": [
      "早上在水井遇到瑪莉，聊了天氣"
    ]
  },
  "currentTime": "14:30",
  "currentLocation": "鐵匠舖",
  "availableActions": [
    { "id": "continue_work", "description": "繼續打鐵" },
    { "id": "go_tavern", "description": "去酒館休息" },
    { "id": "go_home", "description": "回家吃東西" },
    { "id": "visit_church", "description": "去教堂祈禱" }
  ],
  "nearbyVillagers": ["約翰 (朋友)", "瑪莉 (鄰居)"]
}

// API 回應格式
{
  "chosenAction": "go_tavern",
  "reason": "工作了一整個早上，想去酒館放鬆一下，也許能遇到朋友",
  "mood": "tired_but_content"
}
```

### 社交互動請求

```javascript
// 兩人相遇時的對話請求
{
  "type": "social_interaction",
  "location": "水井",
  "ambiance": "peaceful_morning",
  "participants": [
    {
      "name": "艾德蒙",
      "personality": ["friendly"],
      "relationshipWith_other": { "affection": 35, "tags": ["friend"] },
      "currentMood": "content"
    },
    {
      "name": "瑪莉",
      "personality": ["curious", "gossip"],
      "relationshipWith_other": { "affection": 40, "tags": ["friend"] },
      "currentMood": "excited"
    }
  ],
  "recentVillageEvents": ["昨天有旅行商人來訪"]
}

// API 回應格式
{
  "willInteract": true,
  "initiator": "瑪莉",
  "dialogue": [
    { "speaker": "瑪莉", "text": "艾德蒙！你聽說了嗎？昨天那個商人帶來了東方的香料！" },
    { "speaker": "艾德蒙", "text": "真的嗎？價格如何？" },
    { "speaker": "瑪莉", "text": "貴得很！不過聽說老約翰買了一些..." }
  ],
  "relationshipChange": {
    "affection": +2,
    "familiarity": +1
  },
  "newMemory": "在水井與瑪莉聊到旅行商人的事"
}
```

### API 成本控制策略

| 策略 | 說明 |
|------|------|
| **批次限制** | 每秒最多 2-3 次 API 呼叫 |
| **優先級排序** | 玩家附近的村民優先決策 |
| **本地化簡單行為** | 睡覺、吃飯、例行工作不需 API |
| **視野外簡化** | 玩家視野外的村民用規則系統 |
| **快取回應** | 相似情境可重用之前的決策 |
| **決策節流** | 同一村民至少間隔 5 秒才能再次請求 |

---

## 🚶 路徑尋找系統 (A*)

### Tile 地圖結構

```javascript
TileMap = {
  width: 64,
  height: 64,
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
  "size": { "width": 64, "height": 64 },
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
│       │   ├── GameMap.js
│       │   └── MapGenerator.js
│       └── /ui
│           └── UIManager.js
│
├── /backend                 # 後端 (Python 容器)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── /app
│       ├── main.py          # FastAPI 入口
│       ├── /api
│       │   └── routes.py    # HTTP API
│       └── /game
│           ├── game_state.py    # 遊戲狀態管理
│           ├── game_loop.py     # 遊戲主循環
│           ├── villager_ai.py   # GPT AI 決策
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
OPENAI_MODEL=gpt-4.1-nano  # 或其他模型

# 3. 啟動 Docker Compose
docker-compose up --build -d

# 4. 開啟瀏覽器
http://localhost:3000
```

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API 金鑰 (必填) |
| `OPENAI_MODEL` | gpt-3.5-turbo | 使用的模型 |
| `DEBUG_OPENAI` | true | 是否顯示 API 請求日誌 |

---

## 📝 備註

- 地圖一旦生成就會持久保存，除非玩家手動刪除存檔
- 無 API Key 時會使用規則系統（離線模式）
- 村民行為由 AI 決定，後端計算 A* 路徑
- 前端只負責渲染和使用者輸入
