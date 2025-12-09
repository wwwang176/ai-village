"""
任務效果系統 - 使用策略模式處理各種任務效果
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .production import ProductionSystem
    from .inventory import InventorySystem
    from .sheep import SheepSystem

logger = logging.getLogger("TaskEffect")


class TaskContext:
    """任務執行上下文，提供各子系統的存取"""
    
    def __init__(
        self, 
        production: "ProductionSystem",
        inventory: "InventorySystem",
        sheep: "SheepSystem"
    ):
        self.production = production
        self.inventory = inventory
        self.sheep = sheep


class TaskEffect(ABC):
    """任務效果基類"""
    
    @abstractmethod
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        """執行任務效果"""
        pass


# ==================== 基本任務效果 ====================

class EatEffect(TaskEffect):
    """吃東西效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        stats = villager.get("stats", {})
        old_hunger = stats.get("hunger", 0)
        stats["hunger"] = max(0, old_hunger - 40)
        logger.info(f"🍖 {villager['name']} 吃飽了 (飢餓: {old_hunger:.0f} → {stats['hunger']:.0f})")


class RestEffect(TaskEffect):
    """休息效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        stats = villager.get("stats", {})
        old_energy = stats.get("energy", 100)
        stats["energy"] = 90
        logger.info(f"💤 {villager['name']} 休息了 (體力: {old_energy:.0f} → {stats['energy']:.0f})")


class SocializeEffect(TaskEffect):
    """社交效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        stats = villager.get("stats", {})
        old_social = stats.get("social", 50)
        stats["social"] = min(100, old_social + 25)
        logger.info(f"💬 {villager['name']} 社交了 (社交: {old_social:.0f} → {stats['social']:.0f})")


# ==================== 工作相關效果 ====================

class WorkEffect(TaskEffect):
    """工作效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        stats = villager.get("stats", {})
        stats["energy"] = max(0, stats.get("energy", 100) - 10)
        
        # 檢查並消耗工具耐久度
        tool_result = ctx.production.use_tool(villager)
        if tool_result == "no_tool":
            logger.info(f"⚒️ {villager['name']} 沒有工具，無法工作")
            return
        
        # 執行生產
        production_result = ctx.production.produce(villager)
        
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


# ==================== 購買相關效果 ====================

class BuyToolEffect(TaskEffect):
    """購買工具效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        tool_info = ctx.inventory.buy_tool(villager)
        if tool_info:
            logger.info(f"🔨 {villager['name']} 購買了 {tool_info['name']}！(花費 ${tool_info['price']})")
        else:
            logger.info(f"🔨 {villager['name']} 無法購買工具（錢不夠或不需要）")


class BuyMaterialEffect(TaskEffect):
    """購買原料效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        trade_info = ctx.production.execute_material_trade(villager, task)
        if trade_info["success"]:
            logger.info(f"💰 {villager['name']} 向 {trade_info['seller_name']} 購買了 {trade_info['material']} x{trade_info['quantity']}（花費 ${trade_info['price']}）")
        else:
            logger.info(f"💰 {villager['name']} 購買失敗：{trade_info['reason']}")


class BuyFoodEffect(TaskEffect):
    """購買食物效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        food_result = ctx.production.execute_food_purchase(villager, task)
        if food_result["success"]:
            if food_result.get("need_cook"):
                # 生肉放到背包，等回家煮
                logger.info(f"🥩 {villager['name']} 向 {food_result['seller_name']} 購買了 {food_result['food_name']}（花費 ${food_result['price']}，放入{food_result['location']}）")
            else:
                # 其他食物直接吃
                logger.info(f"🍽️ {villager['name']} 向 {food_result['seller_name']} 購買並吃了 {food_result['food_name']}（花費 ${food_result['price']}，飽足度 +{food_result['hunger_restore']}）")
        else:
            # 購買失敗
            logger.info(f"🍽️ {villager['name']} 購買失敗：{food_result['reason']}")


# ==================== 物品相關效果 ====================

class DropItemEffect(TaskEffect):
    """放下物品效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        dropped = ctx.inventory.drop_one_non_tool_item(villager)
        if dropped:
            logger.info(f"📦 {villager['name']} 在家門口放下了 {dropped['item_id']} x{dropped['quantity']}")
        else:
            logger.info(f"📦 {villager['name']} 沒有可以放下的物品")


# ==================== 羊相關效果 ====================

class ShearSheepEffect(TaskEffect):
    """剪羊毛效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        sheep_id = task.get("sheep_id")
        result = ctx.sheep.execute_shear(villager, sheep_id, ctx.production.use_tool)
        if result["success"]:
            location = ctx.inventory.add_item(villager, "wool", result["wool_qty"])
            logger.info(f"🧶 {villager['name']} 剪了羊 {sheep_id} 的毛，獲得羊毛 x{result['quantity']}（{location}）")
        else:
            logger.info(f"🧶 {villager['name']} 剪毛失敗：{result['reason']}")


class BuySheepEffect(TaskEffect):
    """購買羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        seller_id = task.get("seller_id")
        result = ctx.sheep.execute_buy(villager, seller_id)
        if result["success"]:
            logger.info(f"🐑 {villager['name']} 向 {result['seller_name']} 購買了一隻活羊（花費 ${result['price']}）")
        else:
            logger.info(f"🐑 {villager['name']} 買羊失敗：{result['reason']}")


class SlaughterSheepEffect(TaskEffect):
    """宰殺羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        sheep_id = task.get("sheep_id")
        result = ctx.sheep.execute_slaughter(villager, sheep_id, ctx.production.use_tool)
        if result["success"]:
            loc1 = ctx.inventory.add_item(villager, "meat_raw", result["meat_qty"])
            loc2 = ctx.inventory.add_item(villager, "hide", result["hide_qty"])
            logger.info(f"🔪 {villager['name']} 宰殺了羊 {sheep_id}，獲得生肉 x{result['meat_qty']}、羊皮 x{result['hide_qty']}（肉:{loc1}, 皮:{loc2}）")
        else:
            logger.info(f"🔪 {villager['name']} 宰殺失敗：{result['reason']}")


# ==================== 煮飯相關效果 ====================

class CookEffect(TaskEffect):
    """煮飯效果 - 使用灶台把生肉煮成熟肉並吃掉"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> None:
        # 檢查是否有生肉
        inventory = villager.get("inventory", [None, None, None])
        meat_slot = None
        meat_index = -1
        
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == "meat_raw":
                meat_slot = slot
                meat_index = i
                break
        
        if not meat_slot:
            logger.info(f"🍳 {villager['name']} 沒有生肉可以煮")
            return
        
        # 消耗一個生肉
        if meat_slot.get("quantity", 1) > 1:
            meat_slot["quantity"] -= 1
        else:
            villager["inventory"][meat_index] = None
        
        # 煮熟並吃掉，恢復飽足度
        stats = villager.get("stats", {})
        old_hunger = stats.get("hunger", 0)
        stats["hunger"] = max(0, old_hunger - 50)  # 熟肉比麵包更飽
        
        logger.info(f"🍳 {villager['name']} 用灶台煮了生肉吃 (飢餓: {old_hunger:.0f} → {stats['hunger']:.0f})")


# ==================== 效果註冊表 ====================

TASK_EFFECTS: Dict[str, TaskEffect] = {
    "eat": EatEffect(),
    "rest": RestEffect(),
    "socialize": SocializeEffect(),
    "work": WorkEffect(),
    "buy_tool": BuyToolEffect(),
    "buy_material": BuyMaterialEffect(),
    "buy_food": BuyFoodEffect(),
    "drop_one_item": DropItemEffect(),
    "shear_sheep": ShearSheepEffect(),
    "buy_sheep": BuySheepEffect(),
    "slaughter_sheep": SlaughterSheepEffect(),
    "cook": CookEffect(),
}


class TaskEffectExecutor:
    """任務效果執行器"""
    
    def __init__(self, context: TaskContext):
        self.context = context
    
    def execute(self, villager: dict, task: dict) -> None:
        """執行任務效果"""
        task_type = task.get("type")
        effect = TASK_EFFECTS.get(task_type)
        
        if effect:
            effect.execute(villager, task, self.context)
