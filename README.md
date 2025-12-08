# 🏰 AI 中古世紀村莊模擬遊戲

一個由 GPT API 驅動 NPC 行為的中古世紀像素風模擬市民遊戲。

## 📋 功能特色

- **AI 驅動的 NPC** - 村民的行為、對話由 GPT API 生成
- **隨機生成村莊** - 每次遊戲都是獨特的地圖
- **社交系統** - 村民之間有關係網絡、記憶系統
- **日夜循環** - 影響村民作息
- **像素風格** - 純 Canvas 繪製

## 🚀 快速開始

### 使用 Docker Compose（推薦）

```bash
# 1. 複製環境變數
cp .env.example .env

# 2. 編輯 .env，填入你的 OpenAI API Key
# OPENAI_API_KEY=sk-your-api-key

# 3. 啟動服務
docker-compose up --build

# 4. 開啟瀏覽器
# http://localhost:3000
```

### 離線模式（不需要後端）

```bash
# 直接用任何靜態伺服器啟動 frontend 資料夾
cd frontend
python -m http.server 3000

# 開啟 http://localhost:3000
```

離線模式下，NPC 使用簡單規則系統，不會呼叫 GPT API。

## 🎮 操作方式

| 按鍵 | 功能 |
|------|------|
| WASD / 方向鍵 | 移動玩家 |
| 滑鼠左鍵點擊地面 | 自動尋路移動 |
| 滑鼠左鍵點擊物件 | 開啟互動選單 |
| 滑鼠左鍵點擊村民 | 開啟對話選單 |
| ESC | 關閉選單 |

## 📁 專案結構

```
ai-city/
├── docker-compose.yml      # Docker 編排檔
├── .env.example            # 環境變數範例
├── GAME_DESIGN.md          # 遊戲設計文檔
│
├── frontend/               # 前端 (JavaScript + Canvas)
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── api/            # API 客戶端
│       ├── core/           # 遊戲核心
│       ├── entities/       # 實體類別
│       ├── render/         # 渲染系統
│       ├── systems/        # 遊戲系統
│       ├── ui/             # UI 管理
│       └── world/          # 地圖系統
│
├── backend/                # 後端 (Python FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # API 入口
│       ├── api/            # API 路由
│       └── game/           # 遊戲邏輯
│           ├── game_state.py
│           └── villager_ai.py
│
└── saves/                  # 遊戲存檔 (持久化)
```

## 🔧 API 端點

### 遊戲 API

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/game/new` | 建立新遊戲 |
| GET | `/api/game/state` | 取得遊戲狀態 |
| POST | `/api/game/save` | 儲存遊戲 |
| POST | `/api/game/load` | 讀取遊戲 |
| POST | `/api/game/tick` | 遊戲時間推進 |

### 村民 API

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/villagers/` | 取得所有村民 |
| GET | `/api/villagers/{id}` | 取得村民詳情 |
| POST | `/api/villagers/interact` | 與村民互動 |

### AI API

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/ai/decision` | 請求 AI 決策 |
| POST | `/api/ai/dialogue` | 生成 AI 對話 |

## ⚙️ 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 金鑰 | (必填) |
| `OPENAI_MODEL` | 使用的模型 | `gpt-3.5-turbo` |

## 📝 開發指南

### 本地開發後端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 本地開發前端

```bash
cd frontend
python -m http.server 3000
```

## 🎯 開發計劃

- [x] Phase 1: 基礎建設
- [x] Phase 2: Docker 容器化
- [x] Phase 3: AI 整合
- [ ] Phase 4: 完善功能
- [ ] Phase 5: 美術潤色

## 📄 授權

MIT License
