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
        asyncio.create_task(self.conversation_system.start_direct_conversation(villager, target_villager, self.ai_semaphore))
        
        return True
    
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
            tool_result = self.production_system.use_tool(villager)
            if tool_result == "no_tool":
                logger.info(f"⚒️ {villager['name']} 沒有工具，無法工作")
                return
            
            # 執行生產
            production_result = self.production_system.produce(villager)
            
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
            tool_info = self.inventory_system.buy_tool(villager)
            if tool_info:
                logger.info(f"🔨 {villager['name']} 購買了 {tool_info['name']}！(花費 ${tool_info['price']})")
            else:
                logger.info(f"🔨 {villager['name']} 無法購買工具（錢不夠或不需要）")
        
        elif task_type == "buy_material":
            # 購買原料
            trade_info = self.production_system.execute_material_trade(villager, task)
            if trade_info["success"]:
                logger.info(f"💰 {villager['name']} 向 {trade_info['seller_name']} 購買了 {trade_info['material']} x{trade_info['quantity']}（花費 ${trade_info['price']}）")
            else:
                logger.info(f"💰 {villager['name']} 購買失敗：{trade_info['reason']}")
        
        elif task_type == "buy_food":
            # 購買食物並吃掉
            food_result = self.production_system.execute_food_purchase(villager, task)
            if food_result["success"]:
                logger.info(f"🍽️ {villager['name']} 向 {food_result['seller_name']} 購買並吃了 {food_result['food_name']}（花費 ${food_result['price']}，飽足度 +{food_result['hunger_restore']}）")
            else:
                # 購買失敗，直接在酒館吃
                stats["hunger"] = max(0, stats.get("hunger", 50) - 40)
                logger.info(f"🍽️ {villager['name']} 購買失敗：{food_result['reason']}，在酒館吃了東西")
        
        elif task_type == "drop_one_item":
            # 放下背包中的一格物品（非工具）
            dropped = self.inventory_system.drop_one_non_tool_item(villager)
            if dropped:
                logger.info(f"📦 {villager['name']} 在家門口放下了 {dropped['item_id']} x{dropped['quantity']}")
            else:
                logger.info(f"📦 {villager['name']} 沒有可以放下的物品")
        
        elif task_type == "shear_sheep":
            # 剪羊毛
            sheep_id = task.get("sheep_id")
            result = self.sheep_system.execute_shear(villager, sheep_id, self.production_system.use_tool)
            if result["success"]:
                location = self.inventory_system.add_item(villager, "wool", result["wool_qty"])
                logger.info(f"🧶 {villager['name']} 剪了羊 {sheep_id} 的毛，獲得羊毛 x{result['quantity']}（{location}）")
            else:
                logger.info(f"🧶 {villager['name']} 剪毛失敗：{result['reason']}")
        
        elif task_type == "buy_sheep":
            # 購買活羊
            seller_id = task.get("seller_id")
            result = self.sheep_system.execute_buy(villager, seller_id)
            if result["success"]:
                logger.info(f"🐑 {villager['name']} 向 {result['seller_name']} 購買了一隻活羊（花費 ${result['price']}）")
            else:
                logger.info(f"🐑 {villager['name']} 買羊失敗：{result['reason']}")
        
        elif task_type == "slaughter_sheep":
            # 宰殺羊
            sheep_id = task.get("sheep_id")
            result = self.sheep_system.execute_slaughter(villager, sheep_id, self.production_system.use_tool)
            if result["success"]:
                loc1 = self.inventory_system.add_item(villager, "meat_raw", result["meat_qty"])
                loc2 = self.inventory_system.add_item(villager, "hide", result["hide_qty"])
                logger.info(f"🔪 {villager['name']} 宰殺了羊 {sheep_id}，獲得生肉 x{result['meat_qty']}、羊皮 x{result['hide_qty']}（肉:{loc1}, 皮:{loc2}）")
            else:
                logger.info(f"🔪 {villager['name']} 宰殺失敗：{result['reason']}")
    
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
            owned_qty = self.inventory_system.count_item(inventory, material)
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
            if not self.production_system.has_tool(villager):
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
                    # 找不到供應商，無法工作，改成閒逛
                    logger.info(f"🔧 {villager['name']} 缺少 {missing_material}，但找不到供應商，無法工作")
                    return tasks  # 返回空任務，讓 AI 重新決策
            
            # 有工具有原料，去工作
            occupation = villager.get("occupation")
            
            # 牧羊人特殊處理：走到羊旁邊剪毛
            if occupation == "shepherd":
                sheep_tasks = self.sheep_system.create_shepherd_work_tasks(villager)
                if sheep_tasks:
                    tasks.extend(sheep_tasks)
                    return tasks
                else:
                    logger.info(f"🐑 {villager['name']} 沒有可以剪毛的羊")
                    return tasks
            
            # 屠夫特殊處理：殺羊
            if occupation == "butcher":
                butcher_tasks = self.sheep_system.create_butcher_work_tasks(villager)
                if butcher_tasks:
                    tasks.extend(butcher_tasks)
                    return tasks
                else:
                    logger.info(f"🔪 {villager['name']} 沒有可以宰殺的羊")
                    return tasks
            
            # 一般職業：移動到工作地點
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
