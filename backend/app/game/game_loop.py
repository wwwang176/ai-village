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

from .sheep import SheepSystem
from .inventory import InventorySystem
from .conversation import ConversationSystem, Conversation
from .production import ProductionSystem
from .models import Task
from .task_effects import TaskContext, TaskEffectExecutor
from .action_handlers import ActionContext, ActionHandlerExecutor

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
        
        # 對話系統
        self.last_conversation_tick = 0
        self.conversation_tick_interval = 1.5  # 對話回應間隔（秒）
        
        # AI 並行控制（限制同時請求數，避免超過 API 速率限制）
        self.ai_semaphore = asyncio.Semaphore(8)  # 最多 8 個同時 AI 請求
        
        # 子系統
        self.sheep_system = SheepSystem(game_state)
        self.inventory_system = InventorySystem(game_state)
        self.conversation_system = ConversationSystem(game_state, villager_ai, connection_manager)
        self.production_system = ProductionSystem(game_state, self.inventory_system)
        
        # 任務效果執行器
        task_context = TaskContext(
            production=self.production_system,
            inventory=self.inventory_system,
            sheep=self.sheep_system,
            manager=connection_manager
        )
        self.task_executor = TaskEffectExecutor(task_context)
        
        # 行為處理器執行器
        action_context = ActionContext(
            game_state=game_state,
            production=self.production_system,
            inventory=self.inventory_system,
            sheep=self.sheep_system
        )
        self.action_executor = ActionHandlerExecutor(action_context)
    
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
        
        # 1. 更新遊戲時間（所有村民休息時加速 2 倍）
        time_scale = self._get_time_scale()
        self.game_state.update_time(delta_time * time_scale)
        
        # 1.5. 更新天氣
        self.game_state.update_weather()
        
        # 1.6. 記錄歷史數據（每遊戲小時）
        self.game_state.record_history_snapshot()
        
        # 2. 更新村民狀態
        self.update_villagers(delta_time)
        
        # 2.5. 更新羊群狀態
        self.sheep_system.update(delta_time, current_time)
        
        # 3. 處理 AI 決策（背景執行，不阻塞主循環）
        if current_time - self.last_ai_tick >= self.ai_tick_interval:
            self.last_ai_tick = current_time
            # 不 await，讓 AI 決策在背景執行
            asyncio.create_task(self.process_ai_decisions())
        
        # 4. 檢查社交相遇（開始新對話）- 背景執行不阻塞
        encounters = self.conversation_system.check_social_encounters()
        for encounter in encounters:
            asyncio.create_task(self.conversation_system.handle_encounter(encounter, self.ai_semaphore))
        
        # 5. 處理進行中的對話 - 背景執行不阻塞
        if current_time - self.last_conversation_tick >= self.conversation_tick_interval:
            self.last_conversation_tick = current_time
            asyncio.create_task(self.conversation_system.process_conversations(self.ai_semaphore))
        
        # 6. 廣播狀態更新
        if current_time - self.last_broadcast >= self.broadcast_interval:
            self.last_broadcast = current_time
            await self.broadcast_state()
    
    def _get_time_scale(self) -> float:
        """計算時間倍率（所有村民休息時加速）"""
        villagers = list(self.game_state.villagers.values())
        if not villagers:
            return 1.0
        
        # 檢查是否所有村民都在休息
        all_resting = all(
            v.get("state") in ("rest", "sleep", "idle")
            for v in villagers
        )
        
        return 2.0 if all_resting else 1.0
    
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
        personality = villager.get("personality", [])
        
        # 判斷日夜（6:00-18:00 為白天）
        game_time = self.game_state.get_time()
        hour = game_time.get("hour", 12)
        is_daytime = 6 <= hour < 18
        
        # 飢餓緩慢增加（0.25/秒，約 4.7 分鐘從 0 到 70%）
        stats["hunger"] = min(100, stats.get("hunger", 0) + delta_time * 0.25)
        
        # 體力緩慢下降（非睡眠時）
        if villager.get("state") != "sleeping":
            energy_rate = 0.1
            # early_bird/night_owl 影響體力下降速度
            if "early_bird" in personality:
                energy_rate *= 0.8 if is_daytime else 1.2  # 白天慢、晚上快
            elif "night_owl" in personality:
                energy_rate *= 1.2 if is_daytime else 0.8  # 白天快、晚上慢
            
            # 天氣影響（室外時額外消耗體力）
            weather_info = self.game_state.get_weather_info()
            if weather_info["stamina_drain"] > 0 and self.game_state.is_villager_outdoor(villager):
                energy_rate += weather_info["stamina_drain"] * 0.1  # 每 tick 額外消耗
            
            stats["energy"] = max(0, stats.get("energy", 100) - delta_time * energy_rate)
        
        # 社交需求下降
        social_rate = 0.05  # 降低速率，約 33 分鐘從 100→0
        # extrovert/introvert 影響社交下降速度
        if "extrovert" in personality:
            social_rate *= 1.5  # 外向者社交需求下降更快
        elif "introvert" in personality:
            social_rate *= 0.5  # 內向者社交需求下降更慢
        stats["social"] = max(0, stats.get("social", 50) - delta_time * social_rate)
        
        # 心情變化（根據其他狀態值）
        happiness = stats.get("happiness", 70)
        energy = stats.get("energy", 100)
        hunger = stats.get("hunger", 0)
        social = stats.get("social", 50)
        
        happiness_rate = 0.0
        # 體力影響（線性過渡）
        # 70~100: 0~+0.5, 30~70: 0, 0~30: -0.5~0
        if energy > 70:
            happiness_rate += (energy - 70) / 30 * 0.5  # 70→0, 100→0.5
        elif energy < 30:
            happiness_rate += (energy - 30) / 30 * 0.5  # 0→-0.5, 30→0

        # 飽足度影響（hunger 越高越餓，所以反過來）
        # hunger < 30 (飽足度 > 70%): 0~+0.5, hunger > 70 (飽足度 < 30%): -0.5~0
        if hunger < 30:
            happiness_rate += (30 - hunger) / 30 * 0.5  # 0→0.5, 30→0
        elif hunger > 70:
            happiness_rate += (70 - hunger) / 30 * 0.5  # 70→0, 100→-0.5
            
        # 社交影響（線性過渡）
        # 70~100: 0~+0.5, 30~70: 0, 0~30: -0.5~0
        if social > 70:
            happiness_rate += (social - 70) / 30 * 0.5  # 70→0, 100→0.5
        elif social < 30:
            happiness_rate += (social - 30) / 30 * 0.5  # 0→-0.5, 30→0
        
        stats["happiness"] = max(0, min(100, happiness + happiness_rate * delta_time))
    
    def process_task_queue(self, villager: dict, delta_time: float):
        """處理村民的任務隊列"""
        # 如果正在對話，不處理任務
        if villager.get("state") == "talking":
            # 安全機制：如果 talking 超過 60 秒，強制重置
            last_chat = villager.get("last_chat_time", 0)
            if time.time() - last_chat > 60:
                logger.warning(f"⚠️ {villager['name']} 卡在 talking 狀態超過 60 秒，強制重置")
                villager["state"] = "idle"
                villager["task_queue"] = []
            else:
                return
        
        # 如果正在等待社交，檢查是否超時（10秒）
        if villager.get("state") == "waiting_social":
            wait_start = villager.get("waiting_since", 0)
            if time.time() - wait_start > 10:
                logger.info(f"⏰ {villager['name']} 等太久了，不等了")
                villager["state"] = "idle"
                villager.pop("waiting_for", None)
                villager.pop("waiting_since", None)
                return  # 下一個 tick 再處理任務，避免瞬移
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
        elif task_type == "slaughter_sheep":
            completed = self.process_slaughter_sheep_task(villager, current_task, delta_time)
        elif task_type == "shear_sheep":
            completed = self.process_shear_sheep_task(villager, current_task, delta_time)
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
            success = self.apply_task_effect(villager, task)
            
            # 如果任務失敗，清空後續任務
            if not success:
                logger.info(f"❌ {villager['name']} 任務 {task_type} 失敗，清空後續任務")
                villager["task_queue"] = []
                villager["state"] = "idle"
            
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
    
    def process_slaughter_sheep_task(self, villager: dict, task: dict, delta_time: float) -> bool:
        """處理宰殺羊任務（追羊→抓羊→帶回肉舖→殺）"""
        sheep_id = task.get("sheep_id")
        duration = task.get("duration", 6)
        phase = task.get("phase", "chase")  # chase → bring → slaughter
        
        # 取得目標羊
        sheep = self.game_state.sheep.get(sheep_id)
        if not sheep:
            logger.warning(f"⚠️ {villager['name']}: 找不到羊 {sheep_id}")
            return True
        
        # 階段 1: 追羊
        if phase == "chase":
            dx = sheep["x"] - villager["x"]
            dy = sheep["y"] - villager["y"]
            dist = (dx**2 + dy**2) ** 0.5
            
            if dist > 1.5:
                villager["state"] = "walking"
                task["target"] = (sheep["x"], sheep["y"])
                self.process_move_task(villager, task, delta_time)
                return False
            
            # 抓住羊，進入下一階段
            sheep["following"] = villager["id"]
            task["phase"] = "bring"
            logger.info(f"🐑 {villager['name']} 抓住了羊 {sheep_id}，準備帶回肉舖")
            return False
        
        # 階段 2: 帶羊回肉舖
        if phase == "bring":
            # 取得肉舖位置
            butcher_shop = self.game_state.get_workplace(villager)
            if not butcher_shop:
                logger.warning(f"⚠️ {villager['name']}: 找不到肉舖")
                sheep["following"] = None
                return True
            
            # 目標為建築物內部
            shop_x = butcher_shop["x"] + butcher_shop["width"] // 2
            shop_y = butcher_shop["y"] + butcher_shop["height"] // 2
            
            dx = shop_x - villager["x"]
            dy = shop_y - villager["y"]
            dist = (dx**2 + dy**2) ** 0.5
            
            if dist > 1.5:
                villager["state"] = "walking"
                task["target"] = (shop_x, shop_y)
                self.process_move_task(villager, task, delta_time)
                return False
            
            # 到達肉舖，進入宰殺階段
            task["phase"] = "slaughter"
            logger.info(f"🔪 {villager['name']} 帶羊 {sheep_id} 到達肉舖，開始宰殺")
            return False
        
        # 階段 3: 宰殺
        villager["state"] = "slaughter_sheep"
        elapsed = task.get("elapsed", 0) + delta_time
        task["elapsed"] = elapsed
        
        if elapsed >= duration:
            # 解除跟隨
            sheep["following"] = None
            # 執行效果
            success = self.apply_task_effect(villager, task)
            if not success:
                villager["task_queue"] = []
                villager["state"] = "idle"
            return True
        
        return False
    
    def process_shear_sheep_task(self, villager: dict, task: dict, delta_time: float) -> bool:
        """處理剪羊毛任務（整合移動+剪毛）"""
        sheep_id = task.get("sheep_id")
        duration = task.get("duration", 5)
        
        # 取得目標羊
        sheep = self.game_state.sheep.get(sheep_id)
        if not sheep:
            logger.warning(f"⚠️ {villager['name']}: 找不到羊 {sheep_id}")
            return True
        
        # 計算距離
        dx = sheep["x"] - villager["x"]
        dy = sheep["y"] - villager["y"]
        dist = (dx**2 + dy**2) ** 0.5
        
        # 太遠 → 移動靠近（動態追蹤）
        if dist > 1.5:
            villager["state"] = "walking"
            task["target"] = (sheep["x"], sheep["y"])
            self.process_move_task(villager, task, delta_time)
            return False
        
        # 夠近了 → 執行剪毛
        villager["state"] = "shear_sheep"
        elapsed = task.get("elapsed", 0) + delta_time
        task["elapsed"] = elapsed
        
        if elapsed >= duration:
            # 執行效果
            success = self.apply_task_effect(villager, task)
            if not success:
                villager["task_queue"] = []
                villager["state"] = "idle"
            return True
        
        return False
    
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
        asyncio.create_task(self.conversation_system.start_direct_conversation(villager, target_villager, self.ai_semaphore))
        
        return True
    
    def apply_task_effect(self, villager: dict, task: dict) -> bool:
        """執行任務效果（委託給 TaskEffectExecutor），返回是否成功"""
        result = self.task_executor.execute(villager, task)
        
        # 處理待廣播隊列（交易動畫等）
        pending_broadcasts = self.task_executor.context.get_pending_broadcasts()
        for broadcast in pending_broadcasts:
            asyncio.create_task(self.manager.broadcast(broadcast))
        
        return result
    
    def create_task_queue(self, villager: dict, action: str) -> list:
        """將 AI 決策轉換為任務排程（委託給 ActionHandlerExecutor）"""
        return self.action_executor.create_tasks(villager, action)
    
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
                    
                    # 檢查村民是否已有任務（避免異步競爭覆蓋）
                    if villager.get("task_queue"):
                        logger.info(f"⏭️ {villager['name']} 已有任務，丟棄此決策")
                        return
                    
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
                                "reason": reason
                            }
                        }
                    })
                except Exception as e:
                    logger.error(f"❌ AI決策失敗 {villager['name']}: {e}")
        
        # 並行執行所有決策（不限制數量，由 semaphore 控制並發）
        await asyncio.gather(*[process_single_decision(v) for v in pending])
    
    def get_villager_target(self, villager: dict):
        """取得村民的目標位置"""
        task_queue = villager.get("task_queue", [])
        for task in task_queue:
            task_type = task.get("type")
            # move、move_to_villager、slaughter_sheep、shear_sheep 都需要顯示路徑
            if task_type in ["move", "move_to_villager", "slaughter_sheep", "shear_sheep"]:
                # move_to_villager 需要動態取得目標村民位置
                if task_type == "move_to_villager":
                    target_id = task.get("target_villager_id")
                    if target_id:
                        target_v = self.game_state.villagers.get(target_id)
                        if target_v:
                            return (target_v["x"], target_v["y"])
                # slaughter_sheep / shear_sheep 需要動態取得目標羊位置
                elif task_type in ["slaughter_sheep", "shear_sheep"]:
                    sheep_id = task.get("sheep_id")
                    if sheep_id:
                        sheep = self.game_state.sheep.get(sheep_id)
                        if sheep:
                            return (sheep["x"], sheep["y"])
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
                "weather": self.game_state.get_weather_info(),
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
                        "inventory": v.get("inventory", [None] * 5),  # 背包（5格）
                        "money": v.get("money", 50),                          # 金錢
                        "tasks": [t.get("type") for t in v.get("task_queue", [])],
                        "memories": v.get("memories", [])[-5:],  # 只傳最近5條
                        "relationships": v.get("relationships", {})
                    }
                    for v in self.game_state.villagers.values()
                ],
                "world_items": self.game_state.get_all_world_items(),  # 地上物品
                "sheep": [
                    {
                        "id": s["id"],
                        "x": s["x"],
                        "y": s["y"],
                        "is_adult": s["is_adult"],
                        "wool_ready": s["wool_ready"],
                        "owner_id": s["owner_id"]
                    }
                    for s in self.game_state.sheep.values()
                ]
            }
        }
        
        await self.manager.broadcast(state)
    
    def stop(self):
        """停止主循環"""
        self.running = False
        print("🔄 遊戲主循環停止")
