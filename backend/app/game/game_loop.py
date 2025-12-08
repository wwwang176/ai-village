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
        # 如果正在等待社交，不處理任務
        if villager.get("state") == "waiting_social":
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
        
        # 檢查距離是否足夠
        dx = target_villager["x"] - villager["x"]
        dy = target_villager["y"] - villager["y"]
        dist = (dx**2 + dy**2) ** 0.5
        
        if dist > 5:
            # 距離太遠，對話失敗
            logger.info(f"❌ {villager['name']} 想跟 {target_villager['name']} 聊天，但對方已經離開")
            target_villager["state"] = "idle"
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
            logger.info(f"⚒️ {villager['name']} 工作了")
    
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
        if action in ["eat", "go_tavern"]:
            tasks.append({"type": "eat", "duration": 3})
        elif action in ["rest", "go_home"]:
            tasks.append({"type": "rest", "duration": 15})
        elif action == "sleep":
            tasks.append({"type": "rest", "duration": 20})
        elif action in ["go_market", "go_church"]:
            tasks.append({"type": "socialize", "duration": 4})
        elif action == "go_work":
            tasks.append({"type": "work", "duration": 8})
        elif action == "wander":
            # 隨便走走
            if target:
                tasks.append({"type": "move", "target": target})
        
        return tasks
    
    async def process_ai_decisions(self):
        """處理需要 AI 決策的村民"""
        import random
        pending = self.game_state.get_villagers_needing_decision()
        
        # 隨機選擇，確保每個村民都有機會被處理
        random.shuffle(pending)
        
        for villager in pending[:self.ai_decisions_per_tick]:
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
            logger.info(f"� 任務排程: {[t['type'] for t in tasks]}")
            
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
        """處理所有進行中的對話"""
        # 防止重複處理
        if self.conversation_processing:
            return
        self.conversation_processing = True
        
        try:
            finished_conversations = []
            
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
                
                conv.waiting_for_response = True
                
                # 生成下一句回應
                response = await self.generate_conversation_message(conv, conv.current_speaker)
                
                conv.waiting_for_response = False
                
                if response:
                    conv.add_message(conv.current_speaker, response["text"], response.get("end", False))
                    speaker = conv.villager_a if conv.history[-1]["speaker"] == "a" else conv.villager_b
                    await self.broadcast_chat_message(conv, conv.history[-1]["speaker"], response["text"])
                    
                    logger.info(f"💬 {speaker['name']}: {response['text'][:30]}...")
            
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
        
        prompt = f"""你是中古世紀村莊的村民「{villager['name']}」，正在和「{other['name']}」聊天。

你的資訊：
- 職業：{villager.get('occupation', '村民')}
- 性格：{', '.join(villager.get('personality', ['普通']))}

對方資訊：
- 職業：{other.get('occupation', '村民')}

你們的關係：
- 熟悉度：{familiarity}（0-100，越高越熟）
- 好感度：{affection}（-100到100）

你對 {other['name']} 的記憶：
{memories_text}

目前對話（第 {turn_count + 1} 輪，最多 6 輪）：
{history_text}

請用繁體中文回應，只說一句話（15字以內）。
如果覺得對話可以結束了（已經聊了3輪以上），可以說再見。

回傳 JSON 格式：
{{"text": "你要說的話", "end": false}}

如果要結束對話，設 end 為 true，並說再見。"""

        try:
            response = await self.villager_ai.client.chat.completions.create(
                model="gpt-4o-mini",
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
        
        # 增加社交值
        villager_a.get("stats", {})["social"] = min(100, villager_a.get("stats", {}).get("social", 50) + 15)
        villager_b.get("stats", {})["social"] = min(100, villager_b.get("stats", {}).get("social", 50) + 15)
        
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
                model="gpt-4o-mini",
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
        
        await self.manager.broadcast({
            "type": "villager_chat",
            "data": {
                "conversation_id": conv.id,
                "villager_id": villager["id"],
                "villager_name": villager["name"],
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
                        "occupation": v.get("occupation", "villager"),
                        "state": v.get("state", "idle"),
                        "target": self.get_villager_target(v),
                        "stats": v.get("stats", {}),
                        "tasks": [t.get("type") for t in v.get("task_queue", [])],
                        "memories": v.get("memories", [])[-5:],  # 只傳最近5條
                        "relationships": v.get("relationships", {})
                    }
                    for v in self.game_state.villagers.values()
                ]
            }
        }
        
        await self.manager.broadcast(state)
    
    def stop(self):
        """停止主循環"""
        self.running = False
        print("🔄 遊戲主循環停止")
