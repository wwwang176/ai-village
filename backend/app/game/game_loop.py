"""
遊戲主循環 - 後端遊戲狀態更新與推送
"""

import asyncio
import time
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState
    from .villager_ai import VillagerAI

logger = logging.getLogger("GameLoop")


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
        
        # 4. 檢查社交相遇
        encounters = self.check_social_encounters()
        for encounter in encounters:
            await self.handle_encounter(encounter)
        
        # 5. 廣播狀態更新
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
        task_queue = villager.get("task_queue", [])
        
        if not task_queue:
            villager["state"] = "idle"
            return
        
        # 取得當前任務
        current_task = task_queue[0]
        task_type = current_task.get("type")
        
        # 確保村民狀態正確
        if task_type == "move" and villager.get("state") != "walking":
            villager["state"] = "walking"
        
        # 根據任務類型處理
        if task_type == "move":
            completed = self.process_move_task(villager, current_task, delta_time)
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
    
    def is_blocked_by_villager(self, villager: dict, target_x: float, target_y: float) -> bool:
        """檢查目標位置是否被其他村民阻擋"""
        for other in self.game_state.villagers.values():
            if other["id"] == villager["id"]:
                continue
            dist = ((other["x"] - target_x)**2 + (other["y"] - target_y)**2) ** 0.5
            if dist < 0.6:  # 碰撞半徑
                return True
        return False
    
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
        
        # 檢查下一步是否被其他村民阻擋
        if self.is_blocked_by_villager(villager, next_x, next_y):
            # 被阻擋，增加等待時間
            task["wait_time"] = task.get("wait_time", 0) + delta_time
            
            # 等待超過 5 秒，清空整個任務隊列讓 AI 重新決策
            if task["wait_time"] > 5.0:
                logger.info(f"⏳ {villager['name']}: 等待太久，清空任務重新決策")
                villager["task_queue"] = []  # 清空整個隊列
                villager["state"] = "idle"
                return True
            
            # 等待中，不移動
            villager["state"] = "waiting"
            return False
        
        # 重置等待時間
        task["wait_time"] = 0
        
        # 向下一步移動
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
        
        # 根據 action 解析目標位置
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
        elif action in ["socialize", "go_market", "go_church"]:
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
        """處理村民相遇事件"""
        import random
        import time
        
        villager_a, villager_b = encounter
        
        # 檢查是否最近已經對話過（冷卻 30 秒）
        last_chat_a = villager_a.get("last_chat_time", 0)
        last_chat_b = villager_b.get("last_chat_time", 0)
        current_time = time.time()
        
        if current_time - last_chat_a < 30 or current_time - last_chat_b < 30:
            return
        
        # 30% 機率觸發對話
        if random.random() > 0.3:
            return
        
        # 更新熟悉度
        self.game_state.update_relationship(
            villager_a["id"], 
            villager_b["id"], 
            {"familiarity": 1}
        )
        self.game_state.update_relationship(
            villager_b["id"], 
            villager_a["id"], 
            {"familiarity": 1}
        )
        
        # 生成對話
        dialogue = await self.generate_villager_chat(villager_a, villager_b)
        
        if dialogue:
            # 更新對話冷卻時間
            villager_a["last_chat_time"] = current_time
            villager_b["last_chat_time"] = current_time
            
            # 增加雙方社交值
            villager_a.get("stats", {})["social"] = min(100, villager_a.get("stats", {}).get("social", 50) + 10)
            villager_b.get("stats", {})["social"] = min(100, villager_b.get("stats", {}).get("social", 50) + 10)
            
            # 廣播對話到前端
            await self.manager.broadcast({
                "type": "villager_chat",
                "data": dialogue
            })
            
            logger.info(f"💬 {villager_a['name']} 對 {villager_b['name']} 說：{dialogue.get('text_a', '')[:20]}...")
    
    async def generate_villager_chat(self, villager_a: dict, villager_b: dict) -> dict:
        """生成村民間的對話"""
        import random
        
        # 簡單的對話模板（不用 AI，節省 API 調用）
        greetings = [
            ("早安啊！", "早安！今天精神真好"),
            ("最近怎麼樣？", "還不錯，謝謝關心"),
            ("天氣真好呢", "是啊，很適合出門"),
            ("你聽說了嗎？", "什麼事？"),
            ("工作順利嗎？", "還行，有點累"),
            ("要去哪裡啊？", "隨便走走"),
            ("肚子好餓...", "要不要去酒館？"),
            ("今天市集有什麼好東西", "我剛去過，有新鮮蔬菜"),
        ]
        
        text_a, text_b = random.choice(greetings)
        
        return {
            "villager_a_id": villager_a["id"],
            "villager_a_name": villager_a["name"],
            "villager_b_id": villager_b["id"],
            "villager_b_name": villager_b["name"],
            "text_a": text_a,
            "text_b": text_b
        }
    
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
                        "x": v["x"],
                        "y": v["y"],
                        "state": v.get("state", "idle"),
                        "target": self.get_villager_target(v),
                        "stats": v.get("stats", {}),
                        "tasks": [t.get("type") for t in v.get("task_queue", [])]
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
