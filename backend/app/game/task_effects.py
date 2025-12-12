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
        sheep: "SheepSystem",
        manager=None
    ):
        self.production = production
        self.inventory = inventory
        self.sheep = sheep
        self.manager = manager  # ConnectionManager for broadcasting
        self._pending_broadcasts = []  # 待廣播的訊息（因為 execute 是同步的）
    
    def queue_broadcast(self, message: dict):
        """將訊息加入待廣播隊列（稍後由 async 函數發送）"""
        self._pending_broadcasts.append(message)
    
    def get_pending_broadcasts(self) -> list:
        """取得並清空待廣播隊列"""
        broadcasts = self._pending_broadcasts.copy()
        self._pending_broadcasts.clear()
        return broadcasts


class TaskEffect(ABC):
    """任務效果基類"""
    
    @abstractmethod
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        """執行任務效果，返回是否成功"""
        pass


# ==================== 基本任務效果 ====================

class EatEffect(TaskEffect):
    """吃東西效果 - 消耗背包裡的食物"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        inventory = villager.get("inventory", [None] * 5)
        stats = villager.get("stats", {})
        old_hunger = stats.get("hunger", 0)
        
        # 尋找背包裡的麵包
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == "bread":
                # 消耗一個麵包
                if slot.get("quantity", 1) > 1:
                    slot["quantity"] -= 1
                else:
                    villager["inventory"][i] = None
                
                # 恢復飽足度（麵包恢復 30）
                stats["hunger"] = max(0, old_hunger - 30)
                logger.info(f"🍞 {villager['name']} 吃了麵包 (飢餓: {old_hunger:.0f} → {stats['hunger']:.0f})")
                return True
        
        # 沒有食物可吃
        logger.info(f"😢 {villager['name']} 想吃東西但背包沒有食物")
        return False


class RestEffect(TaskEffect):
    """休息效果（睡覺恢復滿體力）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        stats = villager.get("stats", {})
        old_energy = stats.get("energy", 100)
        stats["energy"] = 100
        logger.info(f"💤 {villager['name']} 休息了 (體力: {old_energy:.0f} → {stats['energy']:.0f})")
        return True


class SocializeEffect(TaskEffect):
    """社交效果（社交值在對話結束時才增加）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        # 社交值在對話系統的 finish_conversation 中增加
        # 這裡只標記村民正在等待社交
        logger.info(f"💬 {villager['name']} 正在等待與人交流")
        return True


# ==================== 工作相關效果 ====================

class WorkEffect(TaskEffect):
    """工作效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        stats = villager.get("stats", {})
        stats["energy"] = max(0, stats.get("energy", 100) - 3)
        
        # 檢查並消耗工具耐久度
        tool_result = ctx.production.use_tool(villager)
        if tool_result == "no_tool":
            logger.info(f"⚒️ {villager['name']} 沒有工具，無法工作")
            return False
        
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
            return True
        else:
            reason = production_result.get("reason", "未知原因")
            if tool_result == "broken":
                logger.info(f"⚒️ {villager['name']} 無法生產：{reason}，工具損壞！")
            elif tool_result != "no_need":
                logger.info(f"⚒️ {villager['name']} 無法生產：{reason}（工具耐久度: {tool_result}%）")
            else:
                logger.info(f"⚒️ {villager['name']} 無法生產：{reason}")
            return True  # 工作失敗不清空任務，讓村民繼續嘗試


# ==================== 購買相關效果 ====================

class BuyToolEffect(TaskEffect):
    """購買工具效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        tool_info = ctx.inventory.buy_tool(villager)
        if tool_info:
            logger.info(f"🔨 {villager['name']} 購買了 {tool_info['name']}！(花費 ${tool_info['price']})")
            return True
        else:
            logger.info(f"🔨 {villager['name']} 無法購買工具（錢不夠或不需要）")
            return False


class BuyMaterialEffect(TaskEffect):
    """購買原料效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        trade_info = ctx.production.execute_material_trade(villager, task)
        if trade_info["success"]:
            logger.info(f"💰 {villager['name']} 向 {trade_info['seller_name']} 購買了 {trade_info['material']} x{trade_info['quantity']}（花費 ${trade_info['price']}）")
            # 廣播交易動畫事件
            from ..data.items import ITEM_TYPES
            item_type = ITEM_TYPES.get(trade_info['material'])
            ctx.queue_broadcast({
                "type": "trade_animation",
                "data": {
                    "from_pos": trade_info['seller_pos'],
                    "to_pos": trade_info['buyer_pos'],
                    "item_id": trade_info['material'],
                    "icon": item_type.icon if item_type else "📦",
                    "quantity": trade_info['quantity']
                }
            })
            return True
        else:
            logger.info(f"💰 {villager['name']} 購買失敗：{trade_info['reason']}")
            return False


class BuyFoodEffect(TaskEffect):
    """購買食物效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        food_result = ctx.production.execute_food_purchase(villager, task)
        if food_result["success"]:
            if food_result.get("need_cook"):
                # 生肉放到背包，等回家煮
                logger.info(f"🥩 {villager['name']} 向 {food_result['seller_name']} 購買了 {food_result['food_name']}（花費 ${food_result['price']}，放入{food_result['location']}）")
            else:
                # 其他食物直接吃
                logger.info(f"🍽️ {villager['name']} 向 {food_result['seller_name']} 購買並吃了 {food_result['food_name']}（花費 ${food_result['price']}，飽足度 +{food_result['hunger_restore']}）")
            # 廣播交易動畫事件
            from ..data.items import ITEM_TYPES
            item_type = ITEM_TYPES.get(food_result.get('food_item', 'bread'))
            ctx.queue_broadcast({
                "type": "trade_animation",
                "data": {
                    "from_pos": food_result['seller_pos'],
                    "to_pos": food_result['buyer_pos'],
                    "item_id": food_result.get('food_item', 'bread'),
                    "icon": item_type.icon if item_type else "🍞",
                    "quantity": 2
                }
            })
            return True
        else:
            # 購買失敗
            logger.info(f"🍽️ {villager['name']} 購買失敗：{food_result['reason']}")
            return False


# ==================== 物品相關效果 ====================

class DropItemEffect(TaskEffect):
    """放下物品效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        dropped = ctx.inventory.drop_one_non_tool_item(villager)
        if dropped:
            logger.info(f"📦 {villager['name']} 在家門口放下了 {dropped['item_id']} x{dropped['quantity']}")
            return True
        else:
            logger.info(f"📦 {villager['name']} 沒有可以放下的物品")
            return True  # 沒東西放不算失敗


class DropForFoodEffect(TaskEffect):
    """為了撿食物而丟東西（優先丟原料，其次工具）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        dropped = ctx.inventory.drop_one_for_food(villager)
        if dropped:
            logger.info(f"📦 {villager['name']} 為了撿食物丟下了 {dropped['item_id']} x{dropped['quantity']}")
            return True
        else:
            logger.info(f"📦 {villager['name']} 沒有可以丟的東西")
            return True  # 沒東西丟不算失敗


# ==================== 羊相關效果 ====================

class ShearSheepEffect(TaskEffect):
    """剪羊毛效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        sheep_id = task.get("sheep_id")
        result = ctx.sheep.execute_shear(villager, sheep_id, ctx.production.use_tool)
        if result["success"]:
            location = ctx.inventory.add_item(villager, "wool", result["wool_qty"])
            logger.info(f"🧶 {villager['name']} 剪了羊 {sheep_id} 的毛，獲得羊毛 x{result['quantity']}（{location}）")
            return True
        else:
            logger.info(f"🧶 {villager['name']} 剪毛失敗：{result['reason']}")
            return False


class BuySheepEffect(TaskEffect):
    """購買羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        seller_id = task.get("seller_id")
        result = ctx.sheep.execute_buy(villager, seller_id)
        if result["success"]:
            logger.info(f"🐑 {villager['name']} 向 {result['seller_name']} 購買了一隻活羊（花費 ${result['price']}）")
            return True
        else:
            logger.info(f"🐑 {villager['name']} 買羊失敗：{result['reason']}")
            return False


class SlaughterSheepEffect(TaskEffect):
    """宰殺羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        sheep_id = task.get("sheep_id")
        result = ctx.sheep.execute_slaughter(villager, sheep_id, ctx.production.use_tool)
        if result["success"]:
            loc1 = ctx.inventory.add_item(villager, "meat_raw", result["meat_qty"])
            loc2 = ctx.inventory.add_item(villager, "hide", result["hide_qty"])
            logger.info(f"🔪 {villager['name']} 宰殺了羊 {sheep_id}，獲得生肉 x{result['meat_qty']}、羊皮 x{result['hide_qty']}（肉:{loc1}, 皮:{loc2}）")
            return True
        else:
            logger.info(f"🔪 {villager['name']} 宰殺失敗：{result['reason']}")
            return False


# ==================== 煮飯相關效果 ====================

class CookEffect(TaskEffect):
    """煮飯效果 - 使用灶台把生肉煮成熟肉並吃掉"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        # 檢查是否有生肉
        inventory = villager.get("inventory", [None] * 5)
        meat_slot = None
        meat_index = -1
        
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == "meat_raw":
                meat_slot = slot
                meat_index = i
                break
        
        if not meat_slot:
            logger.info(f"🍳 {villager['name']} 沒有生肉可以煮")
            return False
        
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
        return True


class PickupEffect(TaskEffect):
    """撿起地上物品效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        item_id = task.get("item_id")
        if not item_id:
            logger.info(f"📦 {villager['name']} 沒有指定要撿的物品")
            return False
        
        # 從 game_state 取得物品（透過 production 存取）
        game_state = ctx.production.game_state
        
        # 檢查背包是否滿了，如果滿了先丟一個優先級低的物品
        inventory = villager.get("inventory", [None] * 5)
        has_empty_slot = any(slot is None for slot in inventory)
        
        if not has_empty_slot:
            # 背包滿了，嘗試丟一個非工具、非食物的物品
            dropped = ctx.inventory.drop_one_for_pickup(villager)
            if dropped:
                logger.info(f"📦 {villager['name']} 背包滿了，丟下 {dropped['item_id']} x{dropped.get('quantity', 1)}")
            else:
                logger.info(f"📦 {villager['name']} 背包滿了且沒有可丟的物品，無法撿取")
                return False
        
        # 找到並移除地上的物品
        item = game_state.remove_world_item(item_id)
        if not item:
            logger.info(f"📦 {villager['name']} 找不到物品 {item_id}")
            return False
        
        # 放到村民背包
        location = ctx.inventory.add_item(villager, item["item_id"], item.get("quantity", 1))
        logger.info(f"📦 {villager['name']} 撿起了 {item['item_id']} x{item.get('quantity', 1)}（{location}）")
        return True


# ==================== 販賣給商人效果 ====================

class SellToMerchantEffect(TaskEffect):
    """販賣物品給商人"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        from ..data.supply_chain import MERCHANT_BUY_PRICES
        
        merchant_id = task.get("merchant_id")
        item_id = task.get("item")
        
        if not merchant_id or not item_id:
            logger.info(f"💰 {villager['name']} 販賣失敗：缺少參數")
            return False
        
        # 找商人
        game_state = ctx.production.game_state
        merchant = game_state.get_villager(merchant_id)
        if not merchant:
            logger.info(f"💰 {villager['name']} 找不到商人")
            return False
        
        # 取得價格
        price = MERCHANT_BUY_PRICES.get(item_id, 5)
        
        # 檢查商人有沒有錢
        merchant_money = merchant.get("money", 0)
        if merchant_money < price:
            logger.info(f"💰 商人 {merchant['name']} 沒有足夠的錢 (需要 ${price}，擁有 ${merchant_money})")
            return False
        
        # 檢查賣家背包是否有物品
        inventory = villager.get("inventory", [None] * 5)
        item_slot = None
        item_index = -1
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == item_id:
                item_slot = slot
                item_index = i
                break
        
        if not item_slot:
            logger.info(f"💰 {villager['name']} 背包沒有 {item_id}")
            return False
        
        # 計算賣出數量（全部賣出）
        sell_qty = item_slot.get("quantity", 1)
        total_price = price * sell_qty
        
        # 檢查商人是否有足夠的錢買全部
        if merchant_money < total_price:
            # 商人錢不夠，只買得起部分
            sell_qty = merchant_money // price
            if sell_qty <= 0:
                logger.info(f"💰 商人 {merchant['name']} 錢不夠買任何 {item_id}")
                return False
            total_price = price * sell_qty
        
        # 執行交易
        # 1. 賣家移除物品
        if item_slot.get("quantity", 1) <= sell_qty:
            villager["inventory"][item_index] = None
        else:
            item_slot["quantity"] -= sell_qty
        
        # 2. 金錢轉移
        villager["money"] = villager.get("money", 0) + total_price
        merchant["money"] = merchant_money - total_price
        
        # 3. 物品消失（視為出口）- 商人不保留物品
        # 4. 商人從出口獲得賣價（收購價 × 1.2），淨賺 20%
        export_sell_price = int(total_price * 1.2)
        merchant["money"] += export_sell_price
        export_profit = export_sell_price - total_price
        
        # 清除交易資訊
        if "pending_sell" in villager:
            del villager["pending_sell"]
        
        logger.info(f"💰 {villager['name']} 賣了 {sell_qty} 個 {item_id} 給 {merchant['name']}，獲得 ${total_price}（商人出口利潤 +${export_profit}）")
        
        # 廣播交易動畫事件（物品從賣家飛到商人）
        from ..data.items import ITEM_TYPES
        item_type = ITEM_TYPES.get(item_id)
        ctx.queue_broadcast({
            "type": "trade_animation",
            "data": {
                "from_pos": {"x": villager.get("x", 0), "y": villager.get("y", 0)},
                "to_pos": {"x": merchant.get("x", 0), "y": merchant.get("y", 0)},
                "item_id": item_id,
                "icon": item_type.icon if item_type else "📦",
                "quantity": sell_qty
            }
        })
        return True


# ==================== 變賣物品效果 ====================

class SellExcessEffect(TaskEffect):
    """變賣物品給商人（原價）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        from ..game.production import MATERIAL_PRICES
        from ..data.item_categories import TOOLS
        
        merchant_id = task.get("merchant_id")
        item_id = task.get("item")
        
        if not merchant_id or not item_id:
            logger.info(f"💸 {villager['name']} 變賣失敗：缺少參數")
            return False
        
        # 找商人
        game_state = ctx.production.game_state
        merchant = game_state.get_villager(merchant_id)
        if not merchant:
            logger.info(f"💸 {villager['name']} 找不到商人")
            return False
        
        # 取得原價
        price = MATERIAL_PRICES.get(item_id, 2)
        
        # 檢查商人有沒有錢
        merchant_money = merchant.get("money", 0)
        if merchant_money < price:
            logger.info(f"💸 商人 {merchant['name']} 沒有足夠的錢收購 {item_id}")
            return False
        
        # 檢查賣家背包是否有物品
        inventory = villager.get("inventory", [None] * 5)
        item_slot = None
        item_index = -1
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == item_id:
                item_slot = slot
                item_index = i
                break
        
        if not item_slot:
            logger.info(f"💸 {villager['name']} 背包沒有 {item_id}")
            return False
        
        # 計算賣出數量（全部賣出）
        sell_qty = item_slot.get("quantity", 1)
        total_price = price * sell_qty
        
        # 檢查商人是否有足夠的錢買全部
        if merchant_money < total_price:
            sell_qty = merchant_money // price
            if sell_qty <= 0:
                logger.info(f"💸 商人 {merchant['name']} 錢不夠買任何 {item_id}")
                return False
            total_price = price * sell_qty
        
        # 執行交易
        # 1. 賣家移除物品
        if item_slot.get("quantity", 1) <= sell_qty:
            villager["inventory"][item_index] = None
        else:
            item_slot["quantity"] -= sell_qty
        
        # 2. 金錢轉移（原價，商人不賺錢）
        villager["money"] = villager.get("money", 0) + total_price
        merchant["money"] = merchant_money - total_price
        
        # 3. 物品消失（視為出口）
        
        # 清除交易資訊
        if "pending_sell" in villager:
            del villager["pending_sell"]
        
        logger.info(f"💸 {villager['name']} 變賣了 {sell_qty} 個 {item_id} 給 {merchant['name']}，獲得 ${total_price}（原價）")
        
        # 廣播交易動畫事件（物品從賣家飛到商人）
        from ..data.items import ITEM_TYPES
        item_type = ITEM_TYPES.get(item_id)
        ctx.queue_broadcast({
            "type": "trade_animation",
            "data": {
                "from_pos": {"x": villager.get("x", 0), "y": villager.get("y", 0)},
                "to_pos": {"x": merchant.get("x", 0), "y": merchant.get("y", 0)},
                "item_id": item_id,
                "icon": item_type.icon if item_type else "📦",
                "quantity": sell_qty
            }
        })
        return True


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
    "drop_item": DropForFoodEffect(),
    "shear_sheep": ShearSheepEffect(),
    "buy_sheep": BuySheepEffect(),
    "slaughter_sheep": SlaughterSheepEffect(),
    "cook": CookEffect(),
    "pickup": PickupEffect(),
    "sell_to_merchant": SellToMerchantEffect(),
    "sell_excess": SellExcessEffect(),
}


class TaskEffectExecutor:
    """任務效果執行器"""
    
    def __init__(self, context: TaskContext):
        self.context = context
    
    def execute(self, villager: dict, task: dict) -> bool:
        """執行任務效果，返回是否成功"""
        task_type = task.get("type")
        effect = TASK_EFFECTS.get(task_type)
        
        if effect:
            return effect.execute(villager, task, self.context)
        return True  # 沒有對應效果視為成功
