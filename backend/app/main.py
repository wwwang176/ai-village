"""
AI 中古世紀村莊 - 後端 API
使用 WebSocket 進行即時通訊
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import asyncio

from .game.game_state import GameState
from .game.villager_ai import VillagerAI
from .game.game_loop import GameLoop
from .api import villagers, game, ai


# 全域連線管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 WebSocket 連線 (目前 {len(self.active_connections)} 個)")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WebSocket 斷線 (目前 {len(self.active_connections)} 個)")

    async def broadcast(self, message: dict):
        """廣播訊息給所有連線"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to(self, websocket: WebSocket, message: dict):
        """發送訊息給特定連線"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期"""
    # 啟動時初始化
    app.state.game_state = GameState()
    app.state.villager_ai = VillagerAI()
    app.state.manager = manager
    
    # 啟動遊戲主循環
    app.state.game_loop = GameLoop(
        game_state=app.state.game_state,
        villager_ai=app.state.villager_ai,
        connection_manager=manager
    )
    loop_task = asyncio.create_task(app.state.game_loop.run())
    
    print("🏰 遊戲伺服器啟動")
    yield
    
    # 關閉時清理
    app.state.game_loop.stop()
    loop_task.cancel()
    print("🏰 遊戲伺服器關閉")


app = FastAPI(
    title="AI Medieval Village",
    description="AI 驅動的中古世紀村莊模擬遊戲",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發環境允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(villagers.router, prefix="/api/villagers", tags=["villagers"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 連線端點 - 即時遊戲更新"""
    await manager.connect(websocket)
    
    game_state = app.state.game_state
    villager_ai = app.state.villager_ai
    
    # 如果遊戲未初始化，先初始化
    if not game_state.initialized:
        game_state.initialize()
    
    # 發送初始狀態
    await websocket.send_json({
        "type": "init",
        "data": {
            "map": game_state.map_data,
            "player": game_state.player,
            "villagers": game_state.get_villagers_summary(),
            "furniture": list(game_state.furniture.values()),
            "time": game_state.get_time()
        }
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            await handle_ws_message(websocket, message, game_state, villager_ai)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_ws_message(
    websocket: WebSocket, 
    message: dict, 
    game_state: GameState,
    villager_ai: VillagerAI
):
    """處理 WebSocket 訊息"""
    msg_type = message.get("type")
    data = message.get("data", {})
    
    if msg_type == "player_move":
        # 玩家移動
        game_state.update_player_position(data.get("x"), data.get("y"))
        await websocket.send_json({
            "type": "move_confirmed",
            "data": {"x": data.get("x"), "y": data.get("y")}
        })
        
    elif msg_type == "player_interact":
        # 玩家與物件互動
        result = game_state.player_interact(
            data.get("target_id"),
            data.get("action_id")
        )
        await websocket.send_json({
            "type": "interact_result",
            "data": result
        })
        
    elif msg_type == "player_talk":
        # 玩家與村民對話
        villager = game_state.get_villager(data.get("villager_id"))
        if villager:
            dialogue = await villager_ai.generate_dialogue(
                villager=villager,
                player=game_state.player,
                action=data.get("action", "chat"),
                game_state=game_state,
                player_message=data.get("message")
            )
            await websocket.send_json({
                "type": "dialogue",
                "data": dialogue
            })
            
    elif msg_type == "request_state":
        # 請求完整狀態
        await websocket.send_json({
            "type": "state_update",
            "data": game_state.get_visible_state()
        })
        
    elif msg_type == "ping":
        await websocket.send_json({"type": "pong"})


@app.get("/")
async def root():
    return {"message": "AI Medieval Village API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
