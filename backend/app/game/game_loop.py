"""
遊戲主循環 - 後端遊戲狀態更新與推送
"""

import asyncio
import time
import logging
import random
from typing import TYPE_CHECKING, List, Dict, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .game_state import GameState
    from .villager_ai import VillagerAI

logger = logging.getLogger("GameLoop")


@dataclass
class Conversation:
    """進行中的對話"""
    id: str
    villager_a: dict
    villager_b: dict
    history: List[Dict] = field(default_factory=list)  # [{"speaker": "a", "text": "..."}, ...]
    current_speaker: str = "a"  # "a" or "b"
    started_at: float = 0
    last_message_at: float = 0
    waiting_for_response: bool = False
    max_turns: int = 6  # 最多 6 輪（每人 3 句）
    
    def get_turn_count(self) -> int:
        return len(self.history)
    
    def is_finished(self) -> bool:
        return self.get_turn_count() >= self.max_turns
    
    def add_message(self, speaker: str, text: str, end: bool = False):
        self.history.append({"speaker": speaker, "text": text, "end": end})
        self.current_speaker = "b" if speaker == "a" else "a"
        self.last_message_at = time.time()
    
    def get_history_text(self) -> str:
        """取得對話歷史文字"""
        lines = []
        for msg in self.history[-10:]:  # 最多 10 輪
            name = self.villager_a["name"] if msg["speaker"] == "a" else self.villager_b["name"]
            lines.append(f"{name}: {msg['text']}")
        return "\n".join(lines)


class GameLoop:
    def __init__(self, game_state, villager_ai, connection_manager):
        self.game_state: "GameState" = game_state
        self.villager_ai: "VillagerAI" = villager_ai
        self.manager = connection_manager
        
        self.running = False
        self.tick_rate = 10  # 每秒 tick 次數
        self.tick_interval = 1.0 / self.tick_rate
        
        # AI 決策限制
        self.ai_decisions_per_tick = 2  # 每 tick 最多處理幾個 AI 決策
        self.last_ai_tick = 0
        self.ai_tick_interval = 1.0  # AI 決策間隔（秒）
        
        # 狀態廣播間隔
        self.broadcast_interval = 0.1  # 每 0.1 秒廣播一次狀態
        self.last_broadcast = 0
        
        # 對話系統
        self.active_conversations: Dict[str, Conversation] = {}
        self.conversation_id_counter = 0
        self.last_conversation_tick = 0
        self.conversation_tick_interval = 1.5  # 對話回應間隔（秒）
        self.conversation_processing = False  # 防止重複處理
        
        # AI 並行控制（限制同時請求數，避免超過 API 速率限制）
        self.ai_semaphore = asyncio.Semaphore(8)  # 最多 8 個同時 AI 請求
    
    async def run(self):
        """主循環"""
        self.running = True
        last_time = time.time()
        
        print("🔄 遊戲主循環啟動")
        
        while self.running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time
            
            # 只在有連線時處理
            if self.manager.active_connections:
                # 確保遊戲已初始化
                if not self.game_state.initialized:
                    self.game_state.initialize()
                
                # 更新遊戲狀態
                await self.tick(delta_time, current_time)
            
            # 控制 tick 頻率
            elapsed = time.time() - current_time
            sleep_time = max(0, self.tick_interval - elapsed)
            await asyncio.sleep(sleep_time)
    
    async def tick(self, delta_time: float, current_time: float):
        """單次遊戲更新"""
        
        # 1. 更新遊戲時間
        self.game_state.update_time(delta_time)
        
        # 2. 更新村民狀態
        self.update_villagers(delta_time)
        
        # 3. 處理 AI 決策（背景執行，不阻塞主循環）
        if current_time - self.last_ai_tick >= self.ai_tick_interval:
            self.last_ai_tick = current_time
            # 不 await，讓 AI 決策在背景執行
            asyncio.create_task(self.process_ai_decisions())
        
        # 4. 檢查社交相遇（開始新對話）- 背景執行不阻塞
        encounters = self.check_social_encounters()
        for encounter in encounters:
            asyncio.create_task(self.handle_encounter(encounter))
        
        # 5. 處理進行中的對話 - 背景執行不阻塞
        if current_time - self.last_conversation_tick >= self.conversation_tick_interval:
            self.last_conversation_tick = current_time
            asyncio.create_task(self.process_conversations())
        
        # 6. 廣播狀態更新
        if current_time - self.last_broadcast >= self.broadcast_interval:
            self.last_broadcast = current_time
            await self.broadcast_state()
    
    def update_villagers(self, delta_time: float):
        """更新所有村民位置和狀態"""
        for villager in self.game_state.villagers.values():
            # 更新狀態數值
            self.update_villager_stats(villager, delta_time)
            
            # 處理任務隊列
            self.process_task_queue(villager, delta_time)
            
            # 調試：每 5 秒記錄一次任務狀態
            import time
            if not hasattr(self, '_debug_log_time'):
                self._debug_log_time = {}
            vid = villager['id']
            if time.time() - self._debug_log_time.get(vid, 0) > 5:
                self._debug_log_time[vid] = time.time()
                tq = villager.get('task_queue', [])
                if tq:
                    logger.debug(f"🔍 {villager['name']} 任務: {[t.get('type') for t in tq]}, 狀態: {villager.get('state')}")
    
    def update_villager_stats(self, villager: dict, delta_time: float):
        """更新村民狀態數值"""
        stats = villager.get("stats", {})
        
        # 飢餓緩慢增加
        stats["hunger"] = min(100, stats.get("hunger", 0) + delta_time * 0.5)
        
        # 體力緩慢下降（非睡眠時）
        if villager.get("state") != "sleeping":
            stats["energy"] = max(0, stats.get("energy", 100) - delta_time * 0.1)
        
        # 社交需求下降
        stats["social"] = max(0, stats.get("social", 50) - delta_time * 0.1)
    
    def process_task_queue(self, villager: dict, delta_time: float):
        """處理村民的任務隊列"""
        # 如果正在對話，不處理任務
        if villager.get("state") == "talking":
            return
        
        # 如果正在等待社交，檢查是否超時（10秒）
        if villager.get("state") == "waiting_social":
            wait_start = villager.get("waiting_since", 0)
            if time.time() - wait_start > 10:
                logger.info(f"⏰ {villager['name']} 等太久了，不等了")
                villager["state"] = "idle"
                villager.pop("waiting_for", None)
                villager.pop("waiting_since", None)
            else:
                return
        
        task_queue = villager.get("task_queue", [])
        
        if not task_queue:
            villager["state"] = "idle"
            return
        
        # 取得當前任務
        current_task = task_queue[0]
        task_type = current_task.get("type")
        
        # 確保村民狀態正確
        if task_type in ["move", "move_to_villager"] and villager.get("state") != "walking":
            villager["state"] = "walking"
        
        # 根據任務類型處理
        if task_type == "move":
            completed = self.process_move_task(villager, current_task, delta_time)
        elif task_type == "move_to_villager":
            completed = self.process_move_to_villager_task(villager, current_task, delta_time)
        elif task_type == "initiate_chat":
            completed = self.process_initiate_chat_task(villager, current_task)
        else:
            completed = self.process_action_task(villager, current_task, delta_time)
        
        # 如果任務完成，移除並處理下一個
        if completed:
            task_queue.pop(0)
            
            if task_queue:
                # 還有下一個任務
                next_task = task_queue[0]
                if next_task["type"] == "move":
                    villager["state"] = "walking"
                else:
                    villager["state"] = next_task["type"]
            else:
                # 所有任務完成
                villager["state"] = "idle"
    
    def process_move_task(self, villager: dict, task: dict, delta_time: float) -> bool:
        """處理移動任務，返回是否完成"""
        target = task.get("target")
        if not target:
            logger.warning(f"⚠️ {villager['name']}: 沒有目標")
            return True  # 沒有目標，視為完成
        
        current = (villager["x"], villager["y"])
        target_x, target_y = target[0], target[1]
        
        # 檢查是否已到達
        dx = target_x - current[0]
        dy = target_y - current[1]
        dist = (dx**2 + dy**2) ** 0.5
        
        if dist < 0.5:
            # 到達目標
            villager["x"] = float(target_x)
            villager["y"] = float(target_y)
            return True
        
        # 計算下一步（A* 取第一步）
        start = (int(current[0]), int(current[1]))
        goal = (int(target_x), int(target_y))
        
        # 如果已經在目標格子內，直接向精確目標移動
        if start == goal:
            next_x, next_y = target_x, target_y
        else:
            path = self.game_state.find_path(start, goal)
            
            if path and len(path) > 1:
                next_step = path[1]
                next_x, next_y = next_step[0], next_step[1]
            elif path and len(path) == 1:
                # 起點就是終點格子，直接向目標移動
                next_x, next_y = target_x, target_y
            else:
                # 找不到路徑，清空整個任務隊列
                logger.warning(f"⚠️ {villager['name']}: 找不到路徑 from {start} to {goal}，清空任務")
                villager["task_queue"] = []
                villager["state"] = "idle"
                return True
        
        # 向下一步移動（允許村民重疊）
        dx = next_x - villager["x"]
        dy = next_y - villager["y"]
        dist = (dx**2 + dy**2) ** 0.5
        
        if dist > 0.01:
            speed = 5.0
            move_dist = min(speed * delta_time, dist)
            villager["x"] += (dx / dist) * move_dist
            villager["y"] += (dy / dist) * move_dist
        else:
            # 已經非常接近下一步，直接設定位置
            villager["x"] = float(next_x)
            villager["y"] = float(next_y)
        
        return False
    
    def process_action_task(self, villager: dict, task: dict, delta_time: float) -> bool:
        """處理動作任務，返回是否完成"""
        task_type = task.get("type")
        duration = task.get("duration", 0)
        elapsed = task.get("elapsed", 0)
        
        # 更新經過時間
        elapsed += delta_time
        task["elapsed"] = elapsed
        
        # 檢查是否完成
        if elapsed >= duration:
            # 執行效果
            self.apply_task_effect(villager, task)
            return True
        
        return False
    
    def process_move_to_villager_task(self, villager: dict, task: dict, delta_time: float) -> bool:
        """處理移動到村民的任務（動態追蹤目標村民位置）"""
        target_villager_id = task.get("target_villager_id")
        
        if not target_villager_id:
            logger.warning(f"⚠️ {villager['name']}: 沒有目標村民")
            return True
        
        # 取得目標村民
        target_villager = self.game_state.villagers.get(target_villager_id)
        if not target_villager:
            logger.warning(f"⚠️ {villager['name']}: 找不到目標村民 {target_villager_id}")
            return True
        
        # 動態更新目標位置
        task["target"] = (target_villager["x"], target_villager["y"])
        
        # 計算距離
        dx = target_villager["x"] - villager["x"]
        dy = target_villager["y"] - villager["y"]
        dist = (dx**2 + dy**2) ** 0.5
        
        # 距離 < 8 格時，通知目標村民等待
        if dist < 8 and target_villager.get("state") not in ["talking", "waiting_social"]:
            target_villager["state"] = "waiting_social"
            target_villager["waiting_for"] = villager["id"]
            target_villager["waiting_since"] = time.time()
            logger.info(f"👋 {target_villager['name']} 看到 {villager['name']} 走過來，停下等待")
        
        # 距離 < 3 格時，任務完成（準備開始對話）
        if dist < 3:
            logger.info(f"✅ {villager['name']} 走到 {target_villager['name']} 身邊")
            return True
        
        # 檢查是否超時（20秒）
        elapsed = task.get("elapsed", 0) + delta_time
        task["elapsed"] = elapsed
        if elapsed > 20:
            logger.info(f"⏳ {villager['name']} 追不上 {target_villager['name']}，放棄")
            # 清除目標村民的等待狀態
            if target_villager.get("waiting_for") == villager["id"]:
                target_villager["state"] = "idle"
                target_villager.pop("waiting_for", None)
                target_villager.pop("waiting_since", None)
            return True
        
        # 使用一般移動邏輯
        return self.process_move_task(villager, task, delta_time)
    
    def process_initiate_chat_task(self, villager: dict, task: dict) -> bool:
        """處理發起對話的任務"""
        target_villager_id = task.get("target_villager_id")
        
        if not target_villager_id:
            return True
        
        target_villager = self.game_state.villagers.get(target_villager_id)
        if not target_villager:
            return True
        
        # 清除等待狀態
        if target_villager.get("waiting_for") == villager["id"]:
            target_villager.pop("waiting_for", None)
            target_villager.pop("waiting_since", None)
        
        # 檢查距離是否足夠
        dx = target_villager["x"] - villager["x"]
        dy = target_villager["y"] - villager["y"]
        dist = (dx**2 + dy**2) ** 0.5
        
        if dist > 5:
            # 距離太遠，對話失敗
            logger.info(f"❌ {villager['name']} 想跟 {target_villager['name']} 聊天，但對方已經離開")
            target_villager["state"] = "idle"
            target_villager.pop("waiting_since", None)
            return True
        
        # 直接發起對話（100% 成功）
        asyncio.create_task(self.start_direct_conversation(villager, target_villager))
        
        return True
    
    async def start_direct_conversation(self, villager_a: dict, villager_b: dict):
        """直接發起對話（主動社交，100% 觸發）"""
        # 檢查是否已在對話中
        for conv in self.active_conversations.values():
            if (conv.villager_a["id"] in [villager_a["id"], villager_b["id"]] or
                conv.villager_b["id"] in [villager_a["id"], villager_b["id"]]):
                return
        
        current_time = time.time()
        
        # 建立對話
        self.conversation_id_counter += 1
        conv_id = f"conv_{self.conversation_id_counter}"
        
        conversation = Conversation(
            id=conv_id,
            villager_a=villager_a,
            villager_b=villager_b,
            started_at=current_time,
            last_message_at=current_time
        )
        
        self.active_conversations[conv_id] = conversation
        
        # 更新狀態
        villager_a["last_chat_time"] = current_time
        villager_b["last_chat_time"] = current_time
        villager_a["state"] = "talking"
        villager_b["state"] = "talking"
        
        # 生成第一句話
        first_message = await self.generate_conversation_message(conversation, "a")
        
        if first_message:
            conversation.add_message("a", first_message["text"], first_message.get("end", False))
            await self.broadcast_chat_message(conversation, "a", first_message["text"])
            
            logger.info(f"💬 主動對話開始: {villager_a['name']} 對 {villager_b['name']} 說：{first_message['text'][:30]}...")
    
    def apply_task_effect(self, villager: dict, task: dict):
        """執行任務效果"""
        task_type = task.get("type")
        stats = villager.get("stats", {})
        
        if task_type == "eat":
            old_hunger = stats.get("hunger", 0)
            stats["hunger"] = max(0, old_hunger - 40)
            logger.info(f"🍖 {villager['name']} 吃飽了 (飢餓: {old_hunger:.0f} → {stats['hunger']:.0f})")
            
        elif task_type == "rest":
            old_energy = stats.get("energy", 100)
            stats["energy"] = 90  # 休息後恢復到 90%
            logger.info(f"💤 {villager['name']} 休息了 (體力: {old_energy:.0f} → {stats['energy']:.0f})")
            
        elif task_type == "socialize":
            old_social = stats.get("social", 50)
            stats["social"] = min(100, old_social + 25)
            logger.info(f"💬 {villager['name']} 社交了 (社交: {old_social:.0f} → {stats['social']:.0f})")
            
        elif task_type == "work":
            stats["energy"] = max(0, stats.get("energy", 100) - 10)
            
            # 檢查並消耗工具耐久度
            tool_result = self.use_villager_tool(villager)
            if tool_result == "no_tool":
                logger.info(f"⚒️ {villager['name']} 沒有工具，無法工作")
                return
            
            # 執行生產
            production_result = self.produce_items(villager)
            
            if production_result["success"]:
                product = production_result["product"]
                quantity = production_result["quantity"]
                location = production_result["location"]
                
                if tool_result == "broken":
                    logger.info(f"⚒️ {villager['name']} 生產了 {product} x{quantity}（{location}），工具損壞！")
                else:
                    logger.info(f"⚒️ {villager['name']} 生產了 {product} x{quantity}（{location}），工具耐久度: {tool_result}%")
            else:
                reason = production_result.get("reason", "未知原因")
                if tool_result == "broken":
                    logger.info(f"⚒️ {villager['name']} 無法生產：{reason}，工具損壞！")
                elif tool_result != "no_need":
                    logger.info(f"⚒️ {villager['name']} 無法生產：{reason}（工具耐久度: {tool_result}%）")
                else:
                    logger.info(f"⚒️ {villager['name']} 無法生產：{reason}")
        
        elif task_type == "buy_tool":
            # 購買工具
            tool_info = self.buy_tool_for_villager(villager)
            if tool_info:
                logger.info(f"🔨 {villager['name']} 購買了 {tool_info['name']}！(花費 ${tool_info['price']})")
            else:
                logger.info(f"🔨 {villager['name']} 無法購買工具（錢不夠或不需要）")
        
        elif task_type == "buy_material":
            # 購買原料
            trade_info = self.execute_material_trade(villager, task)
            if trade_info["success"]:
                logger.info(f"💰 {villager['name']} 向 {trade_info['seller_name']} 購買了 {trade_info['material']} x{trade_info['quantity']}（花費 ${trade_info['price']}）")
            else:
                logger.info(f"💰 {villager['name']} 購買失敗：{trade_info['reason']}")
        
        elif task_type == "buy_food":
            # 購買食物並吃掉
            food_result = self.execute_food_purchase(villager, task)
            if food_result["success"]:
                logger.info(f"🍽️ {villager['name']} 向 {food_result['seller_name']} 購買並吃了 {food_result['food_name']}（花費 ${food_result['price']}，飽足度 +{food_result['hunger_restore']}）")
            else:
                # 購買失敗，直接在酒館吃
                stats["hunger"] = max(0, stats.get("hunger", 50) - 40)
                logger.info(f"🍽️ {villager['name']} 購買失敗：{food_result['reason']}，在酒館吃了東西")
        
        elif task_type == "drop_one_item":
            # 放下背包中的一格物品（非工具）
            dropped = self.drop_one_non_tool_item(villager)
            if dropped:
                logger.info(f"📦 {villager['name']} 在家門口放下了 {dropped['item_id']} x{dropped['quantity']}")
            else:
                logger.info(f"📦 {villager['name']} 沒有可以放下的物品")
    
    def use_villager_tool(self, villager: dict) -> str:
        """使用村民的工具（消耗耐久度）
        
        返回:
            - "no_tool": 沒有需要的工具
            - "broken": 工具損壞
            - 數字字串: 剩餘耐久度百分比
            - "no_need": 此職業不需要工具
        """
        # 職業需要的工具
        occupation_tools = {
            "farmer": "hoe",
            "miner": "pickaxe",
            "lumberjack": "axe",
            "shepherd": "shears",
            "butcher": "cleaver",
            "blacksmith": "hammer",
            "carpenter": "saw",
            "tanner": "scraper",
            "tailor": "shears",
        }
        
        occupation = villager.get("occupation", "")
        required_tool = occupation_tools.get(occupation)
        
        # 此職業不需要工具
        if not required_tool:
            return "no_need"
        
        # 檢查背包是否有工具
        inventory = villager.get("inventory", [None, None, None])
        tool_slot = None
        tool_index = -1
        
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == required_tool:
                tool_slot = slot
                tool_index = i
                break
        
        # 沒有工具
        if not tool_slot:
            return "no_tool"
        
        # 消耗耐久度（每次工作消耗 5 點）
        durability = tool_slot.get("durability", 100)
        durability -= 5
        
        if durability <= 0:
            # 工具損壞，從背包移除
            villager["inventory"][tool_index] = None
            return "broken"
        
        # 更新耐久度
        tool_slot["durability"] = durability
        return str(durability)
    
    def villager_has_tool(self, villager: dict) -> bool:
        """檢查村民是否有工作需要的工具"""
        occupation_tools = {
            "farmer": "hoe",
            "miner": "pickaxe",
            "lumberjack": "axe",
            "shepherd": "shears",
            "butcher": "cleaver",
            "blacksmith": "hammer",
            "carpenter": "saw",
            "tanner": "scraper",
            "tailor": "shears",
        }
        
        occupation = villager.get("occupation", "")
        required_tool = occupation_tools.get(occupation)
        
        # 此職業不需要工具
        if not required_tool:
            return True
        
        # 檢查背包
        inventory = villager.get("inventory", [None, None, None])
        for slot in inventory:
            if slot and slot.get("item_id") == required_tool:
                if slot.get("durability", 0) > 0:
                    return True
        
        return False
    
    def produce_items(self, villager: dict) -> dict:
        """執行生產，根據職業產出物品
        
        返回:
            {"success": True/False, "product": "物品名", "quantity": 數量, "location": "背包/地上", "reason": "失敗原因"}
        """
        # 生產配方定義
        # 某些職業有多種產品，會隨機選擇一種生產
        import random
        
        PRODUCTION_RECIPES = {
            # L1 職業：不需要原料
            "farmer": [
                {"output": "grain", "output_name": "穀物", "quantity": 2, "inputs": []},
            ],
            "miner": [
                {"output": "ore", "output_name": "鐵礦", "quantity": 2, "inputs": []},
            ],
            "lumberjack": [
                {"output": "wood", "output_name": "木材", "quantity": 2, "inputs": []},
            ],
            "shepherd": [
                {"output": "wool", "output_name": "羊毛", "quantity": 2, "inputs": []},
                {"output": "hide", "output_name": "羊皮", "quantity": 2, "inputs": []},  # 牧羊人也生產羊皮
            ],
            
            # L2 職業：需要原料
            "miller": [
                {"output": "flour", "output_name": "麵粉", "quantity": 2, "inputs": [("grain", 2)]},
            ],
            "butcher": [
                {"output": "meat_raw", "output_name": "生肉", "quantity": 2, "inputs": []},  # 簡化：屠夫直接生產生肉
            ],
            "blacksmith": [
                {"output": "iron", "output_name": "鐵錠", "quantity": 2, "inputs": [("ore", 2)]},
            ],
            "weaver": [
                {"output": "cloth", "output_name": "布料", "quantity": 2, "inputs": [("wool", 2)]},
            ],
            "tanner": [
                {"output": "leather", "output_name": "皮革", "quantity": 2, "inputs": [("hide", 2)]},
            ],
            
            # L3 職業：需要半成品
            "baker": [
                {"output": "bread", "output_name": "麵包", "quantity": 4, "inputs": [("flour", 2)]},
            ],
            "carpenter": [
                {"output": "furniture", "output_name": "家具", "quantity": 1, "inputs": [("wood", 2), ("iron", 1)]},
            ],
            "tailor": [
                {"output": "clothes", "output_name": "衣服", "quantity": 2, "inputs": [("cloth", 2), ("leather", 1)]},
            ],
            
            # 特殊職業
            "merchant": None,  # 商人不生產
        }
        
        occupation = villager.get("occupation", "")
        recipes = PRODUCTION_RECIPES.get(occupation)
        
        # 此職業不生產
        if not recipes:
            return {"success": False, "reason": "此職業不生產物品"}
        
        inventory = villager.get("inventory", [None, None, None])
        
        # 找出所有可以生產的配方（原料足夠）
        viable_recipes = []
        failed_reasons = []
        
        for recipe in recipes:
            can_produce = True
            for input_item, input_qty in recipe["inputs"]:
                owned_qty = self.count_item_in_inventory(inventory, input_item)
                if owned_qty < input_qty:
                    can_produce = False
                    failed_reasons.append(f"缺少原料 {input_item}（需要 {input_qty}，擁有 {owned_qty}）")
                    break
            
            if can_produce:
                viable_recipes.append(recipe)
        
        # 沒有可生產的配方
        if not viable_recipes:
            return {"success": False, "reason": failed_reasons[0] if failed_reasons else "沒有可生產的配方"}
        
        # 隨機選擇一個可生產的配方
        recipe = random.choice(viable_recipes)
        
        # 消耗原料
        for input_item, input_qty in recipe["inputs"]:
            self.remove_item_from_inventory(villager, input_item, input_qty)
        
        # 產出物品
        output_item = recipe["output"]
        output_qty = recipe["quantity"]
        
        # 嘗試放入背包
        location = self.add_item_to_villager(villager, output_item, output_qty)
        
        return {
            "success": True,
            "product": recipe["output_name"],
            "quantity": output_qty,
            "location": location
        }
    
    def count_item_in_inventory(self, inventory: list, item_id: str) -> int:
        """計算背包中某物品的數量"""
        total = 0
        for slot in inventory:
            if slot and slot.get("item_id") == item_id:
                total += slot.get("quantity", 0)
        return total
    
    def remove_item_from_inventory(self, villager: dict, item_id: str, quantity: int):
        """從背包移除物品"""
        inventory = villager.get("inventory", [None, None, None])
        remaining = quantity
        
        for i, slot in enumerate(inventory):
            if remaining <= 0:
                break
            if slot and slot.get("item_id") == item_id:
                slot_qty = slot.get("quantity", 0)
                if slot_qty <= remaining:
                    # 整個格子都移除
                    remaining -= slot_qty
                    villager["inventory"][i] = None
                else:
                    # 部分移除
                    slot["quantity"] = slot_qty - remaining
                    remaining = 0
    
    def add_item_to_villager(self, villager: dict, item_id: str, quantity: int) -> str:
        """將物品加入村民背包，背包滿則放地上
        
        返回: "背包" 或 "地上"
        """
        inventory = villager.get("inventory", [None, None, None])
        remaining = quantity
        
        # 先嘗試疊加到現有堆疊
        for slot in inventory:
            if remaining <= 0:
                break
            if slot and slot.get("item_id") == item_id:
                current_qty = slot.get("quantity", 0)
                max_stack = 10  # 最大堆疊數
                can_add = max_stack - current_qty
                if can_add > 0:
                    add_qty = min(can_add, remaining)
                    slot["quantity"] = current_qty + add_qty
                    remaining -= add_qty
        
        # 再嘗試放入空格
        for i, slot in enumerate(inventory):
            if remaining <= 0:
                break
            if slot is None:
                add_qty = min(10, remaining)
                villager["inventory"][i] = {
                    "item_id": item_id,
                    "quantity": add_qty,
                    "durability": None,
                    "owner_id": villager["id"]
                }
                remaining -= add_qty
        
        # 還有剩餘，放到地上
        if remaining > 0:
            x = int(villager["x"])
            y = int(villager["y"])
            self.game_state.add_world_item(
                item_id=item_id,
                quantity=remaining,
                x=x,
                y=y,
                owner_id=villager["id"]
            )
            return "地上" if quantity == remaining else "背包+地上"
        
        return "背包"
    
    def buy_tool_for_villager(self, villager: dict) -> Optional[dict]:
        """為村民購買工具
        
        返回工具資訊（包含 name, price）或 None
        """
        # 職業需要的工具及資訊
        occupation_tools = {
            "farmer": {"id": "hoe", "name": "鋤頭", "price": 12, "durability": 100},
            "miner": {"id": "pickaxe", "name": "鶴嘴鋤", "price": 15, "durability": 80},
            "lumberjack": {"id": "axe", "name": "斧頭", "price": 14, "durability": 90},
            "shepherd": {"id": "shears", "name": "剪刀", "price": 10, "durability": 120},
            "butcher": {"id": "cleaver", "name": "屠刀", "price": 12, "durability": 100},
            "blacksmith": {"id": "hammer", "name": "錘子", "price": 15, "durability": 100},
            "carpenter": {"id": "saw", "name": "鋸子", "price": 14, "durability": 70},
            "tanner": {"id": "scraper", "name": "刮刀", "price": 10, "durability": 80},
            "tailor": {"id": "shears", "name": "剪刀", "price": 10, "durability": 120},
        }
        
        occupation = villager.get("occupation", "")
        tool_info = occupation_tools.get(occupation)
        
        # 此職業不需要工具
        if not tool_info:
            return None
        
        # 檢查錢是否足夠
        money = villager.get("money", 0)
        if money < tool_info["price"]:
            return None
        
        # 檢查背包是否有空位
        inventory = villager.get("inventory", [None, None, None])
        empty_slot = -1
        for i, slot in enumerate(inventory):
            if slot is None:
                empty_slot = i
                break
        
        if empty_slot == -1:
            return None  # 背包滿了
        
        # 扣錢
        villager["money"] = money - tool_info["price"]
        
        # 加入工具到背包
        villager["inventory"][empty_slot] = {
            "item_id": tool_info["id"],
            "quantity": 1,
            "durability": tool_info["durability"],
            "owner_id": villager["id"]
        }
        
        return {"name": tool_info["name"], "price": tool_info["price"]}
    
    def drop_one_non_tool_item(self, villager: dict) -> Optional[dict]:
        """放下背包中的一格非工具物品到地上
        
        返回被放下的物品資訊，或 None
        """
        inventory = villager.get("inventory", [None, None, None])
        
        # 工具列表
        tools = ["hoe", "pickaxe", "axe", "shears", "cleaver", "hammer", "saw", "scraper"]
        
        # 找到第一個非工具的物品
        for i, slot in enumerate(inventory):
            if slot is None:
                continue
            item_id = slot.get("item_id")
            if item_id not in tools:
                # 放到地上
                x, y = int(villager["x"]), int(villager["y"])
                self.game_state.add_world_item(
                    item_id=item_id,
                    x=x, y=y,
                    quantity=slot.get("quantity", 1),
                    owner_id=villager["id"]  # 標記擁有者
                )
                
                # 從背包移除
                dropped_item = {"item_id": item_id, "quantity": slot.get("quantity", 1)}
                villager["inventory"][i] = None
                return dropped_item
        
        return None
    
    def execute_food_purchase(self, buyer: dict, task: dict) -> dict:
        """執行食物購買並消費
        
        返回: {"success": bool, "food_name": str, "price": int, "hunger_restore": int, "seller_name": str, "reason": str}
        """
        seller_id = task.get("seller_id")
        food_item = task.get("food_item")
        quantity = 2
        
        # 食物資訊
        FOOD_INFO = {
            "bread": {"name": "麵包", "price": 3, "hunger_restore": 30},
            "meat_raw": {"name": "生肉", "price": 5, "hunger_restore": 40},
            "meat": {"name": "肉品", "price": 6, "hunger_restore": 50},
        }
        
        food_info = FOOD_INFO.get(food_item, {"name": food_item, "price": 4, "hunger_restore": 30})
        total_price = food_info["price"] * quantity
        
        # 找到賣家
        seller = self.game_state.get_villager(seller_id)
        if not seller:
            return {"success": False, "reason": "找不到賣家"}
        
        seller_name = seller.get("name", "未知")
        
        # 檢查買家金錢
        buyer_money = buyer.get("money", 0)
        if buyer_money < total_price:
            return {"success": False, "reason": f"錢不夠（需要 ${total_price}）", "seller_name": seller_name}
        
        # 檢查賣家庫存
        seller_inventory = seller.get("inventory", [None, None, None])
        seller_slot_index = -1
        
        for i, slot in enumerate(seller_inventory):
            if slot and slot.get("item_id") == food_item:
                if slot.get("quantity", 0) >= quantity:
                    seller_slot_index = i
                    break
        
        if seller_slot_index == -1:
            return {"success": False, "reason": f"賣家沒有足夠的 {food_info['name']}", "seller_name": seller_name}
        
        # 執行交易
        buyer["money"] = buyer_money - total_price
        seller["money"] = seller.get("money", 0) + total_price
        
        # 從賣家移除食物
        seller_slot = seller_inventory[seller_slot_index]
        if seller_slot["quantity"] <= quantity:
            seller["inventory"][seller_slot_index] = None
        else:
            seller_slot["quantity"] -= quantity
        
        # 買家吃掉食物，恢復飽足度
        stats = buyer.get("stats", {})
        hunger_restore = food_info["hunger_restore"] * quantity
        stats["hunger"] = max(0, stats.get("hunger", 50) - hunger_restore)
        
        # 清除待處理交易
        if "pending_food_trade" in buyer:
            del buyer["pending_food_trade"]
        
        return {
            "success": True,
            "food_name": food_info["name"],
            "price": total_price,
            "hunger_restore": hunger_restore,
            "seller_name": seller_name
        }
    
    def execute_material_trade(self, buyer: dict, task: dict) -> dict:
        """執行原料交易
        
        返回: {"success": bool, "material": str, "quantity": int, "price": int, "seller_name": str, "reason": str}
        """
        supplier_id = task.get("supplier_id")
        material = task.get("material")
        quantity = 2  # 固定購買 2 個
        
        # 原料價格表
        MATERIAL_PRICES = {
            "grain": 3, "livestock": 8, "flour": 6, "ore": 5,
            "wood": 4, "wool": 4, "hide": 5, "iron": 10,
            "cloth": 8, "leather": 8, "meat_raw": 6, "bread": 4
        }
        
        price_per_unit = MATERIAL_PRICES.get(material, 5)
        total_price = price_per_unit * quantity
        
        # 找到賣家
        seller = self.game_state.get_villager(supplier_id)
        if not seller:
            return {"success": False, "reason": "找不到賣家"}
        
        seller_name = seller.get("name", "未知")
        
        # 檢查買家金錢
        buyer_money = buyer.get("money", 0)
        if buyer_money < total_price:
            return {"success": False, "reason": f"錢不夠（需要 ${total_price}，擁有 ${buyer_money}）", "seller_name": seller_name}
        
        # 檢查賣家庫存
        seller_inventory = seller.get("inventory", [None, None, None])
        seller_slot_index = -1
        seller_qty = 0
        
        for i, slot in enumerate(seller_inventory):
            if slot and slot.get("item_id") == material:
                seller_qty = slot.get("quantity", 0)
                if seller_qty >= quantity:
                    seller_slot_index = i
                    break
        
        if seller_slot_index == -1:
            return {"success": False, "reason": f"賣家沒有足夠的 {material}", "seller_name": seller_name}
        
        # 執行交易
        # 1. 買家扣錢
        buyer["money"] = buyer_money - total_price
        
        # 2. 賣家收錢
        seller["money"] = seller.get("money", 0) + total_price
        
        # 3. 從賣家移除物品
        seller_slot = seller_inventory[seller_slot_index]
        if seller_slot["quantity"] <= quantity:
            seller["inventory"][seller_slot_index] = None
        else:
            seller_slot["quantity"] -= quantity
        
        # 4. 加入買家背包
        self.add_item_to_villager(buyer, material, quantity)
        
        # 清除待處理交易
        if "pending_trade" in buyer:
            del buyer["pending_trade"]
        
        return {
            "success": True,
            "material": material,
            "quantity": quantity,
            "price": total_price,
            "seller_name": seller_name
        }
    
    def check_missing_material(self, villager: dict) -> Optional[str]:
        """檢查村民是否缺少生產所需的原料，返回第一個缺少的原料名"""
        from ..data.supply_chain import REQUIRED_MATERIALS
        
        occupation = villager.get("occupation", "")
        required_materials = REQUIRED_MATERIALS.get(occupation, [])
        
        if not required_materials:
            return None  # L1 職業不需要原料
        
        inventory = villager.get("inventory", [None, None, None])
        
        # 生產配方中各原料需要的數量
        MATERIAL_QUANTITIES = {
            "grain": 2, "livestock": 1, "flour": 2, "ore": 2,
            "wood": 2, "wool": 2, "hide": 2, "iron": 1,
            "cloth": 2, "leather": 1
        }
        
        for material in required_materials:
            required_qty = MATERIAL_QUANTITIES.get(material, 1)
            owned_qty = self.count_item_in_inventory(inventory, material)
            if owned_qty < required_qty:
                return material
        
        return None
    
    def create_buy_material_task(self, villager: dict, material: str) -> Optional[list]:
        """創建購買原料的任務
        
        返回任務列表或 None（找不到供應商）
        """
        from ..data.supply_chain import MATERIAL_PRODUCERS
        
        # 找出誰生產這個原料
        supplier_occupation = MATERIAL_PRODUCERS.get(material)
        if not supplier_occupation:
            return None
        
        # 找到供應商村民
        supplier = self.find_supplier_villager(supplier_occupation, material)
        if not supplier:
            logger.info(f"🔍 {villager['name']} 找不到 {material} 的供應商")
            return None
        
        # 記錄交易資訊
        villager["pending_trade"] = {
            "material": material,
            "supplier_id": supplier["id"],
            "quantity": 2  # 每次購買 2 個
        }
        
        logger.info(f"🛒 {villager['name']} 準備向 {supplier['name']} 購買 {material}")
        
        # 創建移動到供應商並交易的任務
        return [
            {"type": "move_to_villager", "target": (supplier["x"], supplier["y"]), "target_villager_id": supplier["id"]},
            {"type": "buy_material", "supplier_id": supplier["id"], "material": material, "duration": 2}
        ]
    
    def create_buy_food_task(self, villager: dict) -> Optional[list]:
        """創建購買食物的任務
        
        返回任務列表或 None（找不到賣食物的）
        """
        # 食物類型和對應的生產者
        food_sellers = [
            ("bread", "baker"),      # 麵包 → 麵包師
            ("meat_raw", "butcher"), # 生肉 → 屠夫
        ]
        
        # 尋找有食物賣的村民
        for food_item, seller_occupation in food_sellers:
            seller = self.find_food_seller(seller_occupation, food_item)
            if seller:
                # 記錄交易資訊
                villager["pending_food_trade"] = {
                    "food_item": food_item,
                    "seller_id": seller["id"],
                    "quantity": 2
                }
                
                logger.info(f"🍽️ {villager['name']} 準備向 {seller['name']} 購買 {food_item}")
                
                return [
                    {"type": "move_to_villager", "target": (seller["x"], seller["y"]), "target_villager_id": seller["id"]},
                    {"type": "buy_food", "seller_id": seller["id"], "food_item": food_item, "duration": 2}
                ]
        
        return None
    
    def find_food_seller(self, occupation: str, food_item: str) -> Optional[dict]:
        """找到有食物賣的村民"""
        candidates = []
        
        for v in self.game_state.villagers.values():
            if v.get("occupation") != occupation:
                continue
            
            # 檢查是否有食物庫存
            inventory = v.get("inventory", [None, None, None])
            for slot in inventory:
                if slot and slot.get("item_id") == food_item:
                    if slot.get("quantity", 0) >= 2:
                        candidates.append((v, slot.get("quantity", 0)))
                        break
        
        if not candidates:
            return None
        
        # 返回庫存最多的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def find_supplier_villager(self, supplier_occupation: str, material: str) -> Optional[dict]:
        """找到擁有某原料的供應商村民"""
        candidates = []
        
        for v in self.game_state.villagers.values():
            if v.get("occupation") != supplier_occupation:
                continue
            
            # 檢查是否有庫存
            inventory = v.get("inventory", [None, None, None])
            for slot in inventory:
                if slot and slot.get("item_id") == material:
                    if slot.get("quantity", 0) >= 2:
                        candidates.append((v, slot.get("quantity", 0)))
                        break
        
        if not candidates:
            return None
        
        # 返回庫存最多的供應商
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def create_task_queue(self, villager: dict, action: str) -> list:
        """將 AI 決策轉換為任務排程"""
        tasks = []
        
        # 社交行為特殊處理
        if action == "socialize":
            target, target_villager_id = self.game_state._get_social_target(villager)
            if target and target_villager_id:
                # 主動社交：記錄目標村民 ID，使用特殊任務類型
                villager["social_target_id"] = target_villager_id
                tasks.append({
                    "type": "move_to_villager", 
                    "target": target,
                    "target_villager_id": target_villager_id
                })
                tasks.append({"type": "initiate_chat", "target_villager_id": target_villager_id})
                logger.info(f"💬 {villager['name']} 準備去找 {target_villager_id} 聊天")
                return tasks
            elif target:
                # 沒找到人，去市集
                tasks.append({"type": "move", "target": target})
                tasks.append({"type": "socialize", "duration": 4})
                return tasks
        
        # 其他行為
        target = self.game_state.resolve_action_target(villager, action)
        
        # 計算與目標的距離
        if target:
            current = (villager["x"], villager["y"])
            dx = target[0] - current[0]
            dy = target[1] - current[1]
            dist = (dx**2 + dy**2) ** 0.5
            
            # 如果距離太遠，需要先移動
            if dist > 1.5:
                tasks.append({"type": "move", "target": target})
        
        # 根據 action 類型添加動作任務
        if action == "eat":
            tasks.append({"type": "eat", "duration": 3})
        elif action in ["rest", "go_home"]:
            tasks.append({"type": "rest", "duration": 15})
        elif action == "sleep":
            tasks.append({"type": "rest", "duration": 20})
        elif action == "go_market":
            tasks.append({"type": "socialize", "duration": 4})
        elif action == "go_work":
            # 檢查是否有工具
            if not self.villager_has_tool(villager):
                # 沒有工具，去鐵匠購買
                # 但先檢查背包是否滿了
                inventory = villager.get("inventory", [None, None, None])
                has_empty_slot = any(slot is None for slot in inventory)
                
                if not has_empty_slot:
                    # 背包滿了，先回家放一格物品
                    logger.info(f"🎒 {villager['name']} 背包滿了，先回家放東西")
                    home = self.game_state.get_building_by_id(villager.get("residence"))
                    if home:
                        home_target = (home["doorX"], home["doorY"] + 1)
                        tasks.append({"type": "move", "target": home_target})
                        tasks.append({"type": "drop_one_item", "duration": 1})
                
                logger.info(f"🔧 {villager['name']} 沒有工具，改去鐵匠購買")
                blacksmith = self.game_state.get_building_by_type("blacksmith")
                if blacksmith:
                    blacksmith_target = (blacksmith["doorX"], blacksmith["doorY"] + 1)
                    tasks.append({"type": "move", "target": blacksmith_target})
                    tasks.append({"type": "buy_tool", "duration": 2})
                return tasks
            
            # 檢查是否有原料（L2/L3 職業）
            missing_material = self.check_missing_material(villager)
            if missing_material:
                # 缺原料，去找供應商購買
                supplier_task = self.create_buy_material_task(villager, missing_material)
                if supplier_task:
                    tasks.extend(supplier_task)
                    return tasks
                else:
                    # 找不到供應商，直接去工作（會失敗但消耗時間）
                    logger.info(f"🔧 {villager['name']} 缺少 {missing_material}，但找不到供應商")
            
            # 有工具有原料，去工作
            # 先移動到工作地點
            work_target = self.game_state.resolve_action_target(villager, "go_work")
            if work_target:
                current = (villager["x"], villager["y"])
                dx = work_target[0] - current[0]
                dy = work_target[1] - current[1]
                dist = (dx**2 + dy**2) ** 0.5
                if dist > 1.5:
                    tasks.append({"type": "move", "target": work_target})
            tasks.append({"type": "work", "duration": 8})
        elif action == "buy_food":
            # 購買食物
            food_task = self.create_buy_food_task(villager)
            if food_task:
                tasks.extend(food_task)
            else:
                # 找不到賣食物的人，直接去酒館
                logger.info(f"🍖 {villager['name']} 找不到賣食物的人，去酒館")
                tavern = self.game_state.get_building_by_type("tavern")
                if tavern:
                    tasks.append({"type": "move", "target": (tavern["doorX"], tavern["doorY"] + 1)})
                tasks.append({"type": "eat", "duration": 3})
        elif action == "wander":
            # 隨便走走
            if target:
                tasks.append({"type": "move", "target": target})
        
        return tasks
    
    async def process_ai_decisions(self):
        """處理需要 AI 決策的村民（並行處理）"""
        import random
        pending = self.game_state.get_villagers_needing_decision()
        
        if not pending:
            return
        
        # 隨機選擇，確保每個村民都有機會被處理
        random.shuffle(pending)
        
        # 並行處理所有需要決策的村民
        async def process_single_decision(villager):
            """處理單個村民的 AI 決策"""
            async with self.ai_semaphore:  # 限制同時請求數
                try:
                    decision = await self.villager_ai.make_decision(
                        villager, 
                        self.game_state
                    )
                    
                    action = decision.get("action", "wander")
                    reason = decision.get("reason", "")
                    
                    # 將 AI 決策轉換為任務排程
                    tasks = self.create_task_queue(villager, action)
                    
                    # 顯示 AI 決策結果
                    logger.info(f"🤖 AI決策: {villager['name']} → {action} (原因: {reason})")
                    logger.info(f"📋 任務排程: {[t['type'] for t in tasks]}")
                    
                    # 添加任務到村民
                    self.game_state.add_tasks(villager["id"], tasks)
                    
                    # 推送決策給前端（包含 reason 用於泡泡顯示）
                    await self.manager.broadcast({
                        "type": "villager_decision",
                        "data": {
                            "villager_id": villager["id"],
                            "decision": {
                                "action": action,
                                "reason": reason,
                                "mood": decision.get("mood")
                            }
                        }
                    })
                except Exception as e:
                    logger.error(f"❌ AI決策失敗 {villager['name']}: {e}")
        
        # 並行執行所有決策（不限制數量，由 semaphore 控制並發）
        await asyncio.gather(*[process_single_decision(v) for v in pending])
    
    def check_social_encounters(self) -> list:
        """檢查村民相遇"""
        encounters = []
        villagers = list(self.game_state.villagers.values())
        encounter_distance = 1.5
        
        for i, a in enumerate(villagers):
            for b in villagers[i+1:]:
                # 跳過忙碌的村民
                if a.get("state") not in ["idle", "walking"]:
                    continue
                if b.get("state") not in ["idle", "walking"]:
                    continue
                
                # 計算距離
                dx = a["x"] - b["x"]
                dy = a["y"] - b["y"]
                dist = (dx**2 + dy**2) ** 0.5
                
                if dist < encounter_distance:
                    encounters.append((a, b))
        
        return encounters
    
    async def handle_encounter(self, encounter: tuple):
        """處理村民相遇事件 - 開始新對話"""
        villager_a, villager_b = encounter
        
        # 檢查是否已在對話中
        for conv in self.active_conversations.values():
            if (conv.villager_a["id"] in [villager_a["id"], villager_b["id"]] or
                conv.villager_b["id"] in [villager_a["id"], villager_b["id"]]):
                return
        
        # 檢查是否最近已經對話過（冷卻 60 秒）
        last_chat_a = villager_a.get("last_chat_time", 0)
        last_chat_b = villager_b.get("last_chat_time", 0)
        current_time = time.time()
        
        if current_time - last_chat_a < 60 or current_time - last_chat_b < 60:
            return
        
        # 30% 機率觸發對話
        if random.random() > 0.3:
            return
        
        # 建立新對話
        self.conversation_id_counter += 1
        conv_id = f"conv_{self.conversation_id_counter}"
        
        conversation = Conversation(
            id=conv_id,
            villager_a=villager_a,
            villager_b=villager_b,
            started_at=current_time,
            last_message_at=current_time
        )
        
        self.active_conversations[conv_id] = conversation
        
        # 更新對話狀態
        villager_a["last_chat_time"] = current_time
        villager_b["last_chat_time"] = current_time
        villager_a["state"] = "talking"
        villager_b["state"] = "talking"
        
        # 生成第一句話（A 先說）
        first_message = await self.generate_conversation_message(conversation, "a")
        
        if first_message:
            conversation.add_message("a", first_message["text"], first_message.get("end", False))
            await self.broadcast_chat_message(conversation, "a", first_message["text"])
            
            logger.info(f"💬 對話開始: {villager_a['name']} 對 {villager_b['name']} 說：{first_message['text'][:30]}...")
    
    async def process_conversations(self):
        """處理所有進行中的對話（並行處理）"""
        # 防止重複處理
        if self.conversation_processing:
            return
        self.conversation_processing = True
        
        try:
            finished_conversations = []
            tasks_to_process = []
            
            for conv_id, conv in list(self.active_conversations.items()):
                # 檢查是否超時（30秒沒回應）
                if time.time() - conv.last_message_at > 30:
                    finished_conversations.append(conv_id)
                    continue
                
                # 檢查是否已結束
                if conv.is_finished():
                    finished_conversations.append(conv_id)
                    continue
                
                # 檢查最後一條訊息是否要結束
                if conv.history and conv.history[-1].get("end", False):
                    finished_conversations.append(conv_id)
                    continue
                
                # 檢查是否正在等待回應（避免重複生成）
                if conv.waiting_for_response:
                    continue
                
                # 收集需要處理的對話
                tasks_to_process.append((conv_id, conv))
            
            # 並行處理所有對話
            async def process_single_conversation(conv_id, conv):
                conv.waiting_for_response = True
                try:
                    async with self.ai_semaphore:
                        response = await self.generate_conversation_message(conv, conv.current_speaker)
                    
                    if response:
                        conv.add_message(conv.current_speaker, response["text"], response.get("end", False))
                        speaker = conv.villager_a if conv.history[-1]["speaker"] == "a" else conv.villager_b
                        await self.broadcast_chat_message(conv, conv.history[-1]["speaker"], response["text"])
                        logger.info(f"💬 {speaker['name']}: {response['text'][:30]}...")
                except Exception as e:
                    logger.error(f"❌ 對話處理失敗: {e}")
                finally:
                    conv.waiting_for_response = False
            
            # 並行執行
            if tasks_to_process:
                await asyncio.gather(*[process_single_conversation(cid, c) for cid, c in tasks_to_process])
            
            # 結束已完成的對話
            for conv_id in finished_conversations:
                await self.finish_conversation(conv_id)
        finally:
            self.conversation_processing = False
    
    async def generate_conversation_message(self, conv: Conversation, speaker: str) -> Optional[dict]:
        """用 AI 生成對話回應"""
        villager = conv.villager_a if speaker == "a" else conv.villager_b
        other = conv.villager_b if speaker == "a" else conv.villager_a
        
        # 取得雙方關係
        rel = villager.get("relationships", {}).get(other["id"], {})
        familiarity = rel.get("familiarity", 0)
        affection = rel.get("affection", 0)
        
        # 取得記憶
        memories = villager.get("memories", [])
        recent_memories = [m for m in memories[-5:] if m.get("with") == other["name"]]
        memories_text = "\n".join([f"- {m.get('summary', '')}" for m in recent_memories]) or "無"
        
        # 建立 prompt
        history_text = conv.get_history_text() or "（對話剛開始）"
        turn_count = conv.get_turn_count()
        
        # 取得時間和狀態
        time = self.game_state.get_time()
        my_stats = villager.get("stats", {})
        other_stats = other.get("stats", {})
        
        # 心情描述
        def get_mood(stats):
            if stats.get("energy", 100) < 30:
                return "很累"
            if stats.get("hunger", 0) > 70:
                return "很餓"
            if stats.get("social", 50) < 20:
                return "寂寞"
            if stats.get("happiness", 50) > 70:
                return "開心"
            return "普通"
        
        my_mood = get_mood(my_stats)
        
        # 取得喜好
        my_prefs = villager.get("preferences", {})
        other_prefs = other.get("preferences", {})
        
        prompt = f"""你是中古世紀村莊的村民「{villager['name']}」，正在和「{other['name']}」聊天。

【你的資訊】
- 年齡：{villager.get('age', 25)} 歲
- 職業：{villager.get('occupation', '村民')}
- 性格：{', '.join(villager.get('personality', ['普通']))}
- 興趣：{', '.join(my_prefs.get('hobbies', ['無']))}
- 喜歡的食物：{', '.join(my_prefs.get('favorite_foods', ['無']))}
- 討厭：{', '.join(my_prefs.get('dislikes', ['無']))}
- 目前心情：{my_mood}
- 體力：{my_stats.get('energy', 100):.0f}%
- 社交需求：{my_stats.get('social', 50):.0f}%（越低越想聊天）

【對方資訊】
- 名字：{other['name']}
- 年齡：{other.get('age', 25)} 歲  
- 職業：{other.get('occupation', '村民')}
- 性格：{', '.join(other.get('personality', ['普通']))}
- 興趣：{', '.join(other_prefs.get('hobbies', ['不清楚']))}

【你們的關係】
- 關係類型：{rel.get('type', '陌生人')}
- 熟悉度：{familiarity}（0=陌生人，100=老朋友）
- 好感度：{affection}（負=討厭，正=喜歡）

【你對 {other['name']} 的記憶】
{memories_text}

【現在時間】第 {time['day']} 天 {time['hour']:02d}:{time['minute']:02d}

【目前對話】（第 {turn_count + 1} 輪，最多 6 輪）
{history_text}

請根據你的性格、心情和對對方的了解，用繁體中文回應。
- 可以聊工作、天氣、村裡八卦、個人煩惱等
- 如果很熟，可以更親密；如果不熟，可以更客套
- 只說一句話（20字以內）
- 如果已經聊了3輪以上，可以說再見結束對話

回傳 JSON 格式：
{{"text": "你要說的話", "end": false}}

結束對話時設 end 為 true。"""

        try:
            response = await self.villager_ai.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.8
            )
            
            content = response.choices[0].message.content.strip()
            
            # 解析 JSON
            import json
            # 嘗試提取 JSON
            if "{" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                result = json.loads(json_str)
                return result
            else:
                return {"text": content[:50], "end": False}
                
        except Exception as e:
            logger.error(f"生成對話失敗: {e}")
            return {"text": "嗯...", "end": True}
    
    async def finish_conversation(self, conv_id: str):
        """結束對話，生成總結並存入記憶"""
        if conv_id not in self.active_conversations:
            return
        
        conv = self.active_conversations[conv_id]
        villager_a = conv.villager_a
        villager_b = conv.villager_b
        
        # 恢復村民狀態
        if villager_a.get("state") == "talking":
            villager_a["state"] = "idle"
        if villager_b.get("state") == "talking":
            villager_b["state"] = "idle"
        
        # 更新關係
        self.game_state.update_relationship(villager_a["id"], villager_b["id"], {"familiarity": 2, "affection": 1})
        self.game_state.update_relationship(villager_b["id"], villager_a["id"], {"familiarity": 2, "affection": 1})
        
        # 增加社交值（對話完成 +25）
        villager_a.get("stats", {})["social"] = min(100, villager_a.get("stats", {}).get("social", 50) + 25)
        villager_b.get("stats", {})["social"] = min(100, villager_b.get("stats", {}).get("social", 50) + 25)
        logger.info(f"💬 {villager_a['name']} 和 {villager_b['name']} 社交值 +25")
        
        # 生成對話總結並存入記憶
        if len(conv.history) >= 2:
            summary = await self.generate_conversation_summary(conv)
            if summary:
                # 存入雙方記憶
                self.add_conversation_memory(villager_a, villager_b["name"], summary)
                self.add_conversation_memory(villager_b, villager_a["name"], summary)
        
        # 廣播對話結束
        await self.manager.broadcast({
            "type": "conversation_end",
            "data": {
                "conversation_id": conv_id,
                "villager_a_id": villager_a["id"],
                "villager_b_id": villager_b["id"]
            }
        })
        
        logger.info(f"💬 對話結束: {villager_a['name']} 和 {villager_b['name']}")
        
        # 移除對話
        del self.active_conversations[conv_id]
    
    async def generate_conversation_summary(self, conv: Conversation) -> Optional[str]:
        """生成對話總結（最多50字）"""
        history_text = conv.get_history_text()
        
        prompt = f"""請用一句話總結以下對話（最多30字，用繁體中文）：

{history_text}

只回傳總結內容，不要加引號或其他格式。"""

        try:
            response = await self.villager_ai.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content.strip()
            return summary[:50]  # 確保不超過 50 字
            
        except Exception as e:
            logger.error(f"生成總結失敗: {e}")
            return None
    
    def add_conversation_memory(self, villager: dict, other_name: str, summary: str):
        """添加對話記憶（最多保留10條）"""
        if "memories" not in villager:
            villager["memories"] = []
        
        memory = {
            "type": "conversation",
            "with": other_name,
            "summary": summary,
            "day": self.game_state.day,
            "hour": int(self.game_state.hour)
        }
        
        villager["memories"].append(memory)
        
        # 只保留最近 10 條記憶
        if len(villager["memories"]) > 10:
            villager["memories"] = villager["memories"][-10:]
    
    async def broadcast_chat_message(self, conv: Conversation, speaker: str, text: str):
        """廣播單條對話訊息"""
        villager = conv.villager_a if speaker == "a" else conv.villager_b
        target = conv.villager_b if speaker == "a" else conv.villager_a
        
        await self.manager.broadcast({
            "type": "villager_chat",
            "data": {
                "conversation_id": conv.id,
                "villager_id": villager["id"],
                "villager_name": villager["name"],
                "target_name": target["name"],
                "text": text,
                "turn": conv.get_turn_count()
            }
        })
    
    def get_villager_target(self, villager: dict):
        """取得村民的目標位置"""
        task_queue = villager.get("task_queue", [])
        for task in task_queue:
            if task.get("type") == "move":
                return task.get("target")
        return None
    
    async def broadcast_state(self):
        """廣播遊戲狀態"""
        if not self.manager.active_connections:
            return
        
        state = {
            "type": "tick",
            "data": {
                "time": self.game_state.get_time(),
                "villagers": [
                    {
                        "id": v["id"],
                        "name": v["name"],
                        "x": v["x"],
                        "y": v["y"],
                        "age": v.get("age", 25),
                        "occupation": v.get("occupation", "villager"),
                        "personality": v.get("personality", []),
                        "preferences": v.get("preferences", {}),
                        "state": v.get("state", "idle"),
                        "target": self.get_villager_target(v),
                        "stats": v.get("stats", {}),
                        "inventory": v.get("inventory", [None, None, None]),  # 背包
                        "money": v.get("money", 50),                          # 金錢
                        "tasks": [t.get("type") for t in v.get("task_queue", [])],
                        "memories": v.get("memories", [])[-5:],  # 只傳最近5條
                        "relationships": v.get("relationships", {})
                    }
                    for v in self.game_state.villagers.values()
                ],
                "world_items": self.game_state.get_all_world_items()  # 地上物品
            }
        }
        
        await self.manager.broadcast(state)
    
    def stop(self):
        """停止主循環"""
        self.running = False
        print("🔄 遊戲主循環停止")
