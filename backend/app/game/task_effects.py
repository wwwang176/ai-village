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
    """吃東西效果 - 消耗背包裡的食物（麵包或熟肉）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        inventory = villager.get("inventory", [None] * 5)
        stats = villager.get("stats", {})
        old_satiety = stats.get("satiety", 100)
        from .production import get_food_info

        # 尋找背包裡可直接吃的食物（麵包或熟肉）
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") in ("bread", "meat"):
                item_id = slot.get("item_id")
                # 消耗一個
                if slot.get("quantity", 1) > 1:
                    slot["quantity"] -= 1
                else:
                    villager["inventory"][i] = None

                # 恢復飽足度
                food_info = get_food_info(item_id)
                restore = food_info.get("satiety_restore", 35)
                food_name = food_info.get("name", item_id)
                stats["satiety"] = min(100, old_satiety + restore)
                logger.info(f"🍖 {villager['name']} 吃了{food_name} (飽足: {old_satiety:.0f} → {stats['satiety']:.0f})")
                return True
        
        # 沒有食物可吃
        logger.info(f"😢 {villager['name']} 想吃東西但背包沒有食物")
        task["fail_reason"] = "吃東西：背包沒有食物"
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
        
        # 檢查是否在工作台附近（如果工作場所有工作台的話）
        game_state = ctx.production.game_state
        workbench = game_state.get_workbench_by_workplace(villager.get("id"))
        if workbench:
            vx, vy = int(villager.get("x", 0)), int(villager.get("y", 0))
            wx, wy = int(workbench["x"]), int(workbench["y"])
            distance = abs(vx - wx) + abs(vy - wy)  # 曼哈頓距離
            if distance > 1:
                logger.info(f"⚒️ {villager['name']} 不在工作台附近（距離 {distance}），無法工作")
                task["fail_reason"] = "工作：不在工作台附近"
                return False
        
        # 先檢查是否有工具（不消耗）
        if not ctx.production.has_tool(villager):
            logger.info(f"⚒️ {villager['name']} 沒有工具，無法工作")
            task["fail_reason"] = "工作：沒有工具"
            return False
        
        # 先執行生產（檢查材料並消耗）
        production_result = ctx.production.produce(villager)
        
        if not production_result["success"]:
            # 材料不足，不消耗工具耐久度
            reason = production_result.get("reason", "未知原因")
            logger.info(f"⚒️ {villager['name']} 無法生產：{reason}")
            task["fail_reason"] = f"工作：{reason}"
            return False  # 材料不足也算失敗，記錄原因
        
        # 生產成功，才消耗工具耐久度
        tool_result = ctx.production.use_tool(villager)
        
        product = production_result["product"]
        quantity = production_result["quantity"]
        location = production_result["location"]
        
        # 觸發生產動畫（物品從自己飛到自己）
        from ..data.items import ITEM_TYPES
        item_type = ITEM_TYPES.get(product)
        icon = item_type.icon if item_type else "📦"
        
        villager_x = villager.get("x", 0)
        villager_y = villager.get("y", 0)
        
        ctx.queue_broadcast({
            "type": "trade_animation",
            "data": {
                "from_pos": {"x": villager_x, "y": villager_y - 1},  # 從頭頂飛出
                "to_pos": {"x": villager_x, "y": villager_y},
                "item_id": product,
                "icon": icon,
                "quantity": quantity
            }
        })
        
        if tool_result == "broken":
            logger.info(f"⚒️ {villager['name']} 生產了 {product} x{quantity}（{location}），工具損壞！")
        else:
            logger.info(f"⚒️ {villager['name']} 生產了 {product} x{quantity}（{location}），工具耐久度: {tool_result}%")
        return True


# ==================== 購買相關效果 ====================

class BuyToolEffect(TaskEffect):
    """購買工具效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        # 找鐵匠
        game_state = ctx.production.game_state
        blacksmith = None
        for v in game_state.villagers.values():
            if v.get("occupation") == "blacksmith":
                blacksmith = v
                break
        
        # 檢查鐵匠是否在睡覺
        if blacksmith and blacksmith.get("state") == "sleeping":
            logger.info(f"🔨 {villager['name']} 無法購買工具：鐵匠在睡覺")
            task["fail_reason"] = "買工具：鐵匠在睡覺"
            return False
        
        tool_info = ctx.inventory.buy_tool(villager)
        if tool_info:
            logger.info(f"🔨 {villager['name']} 購買了 {tool_info['name']}！(花費 ${tool_info['price']})")
            
            villager_x = villager.get("x", 0)
            villager_y = villager.get("y", 0)
            
            if blacksmith:
                # 工具從鐵匠飛到買家
                ctx.queue_broadcast({
                    "type": "trade_animation",
                    "data": {
                        "from_pos": {"x": blacksmith.get("x", 0), "y": blacksmith.get("y", 0)},
                        "to_pos": {"x": villager_x, "y": villager_y},
                        "item_id": "tool",
                        "icon": "🔨",
                        "quantity": 1
                    }
                })
            return True
        else:
            logger.info(f"🔨 {villager['name']} 無法購買工具（錢不夠或不需要）")
            task["fail_reason"] = "買工具：錢不夠或不需要"
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
            seller_name = trade_info.get('seller_name', '賣家')
            logger.info(f"💰 {villager['name']} 購買失敗：{trade_info['reason']}")
            task["fail_reason"] = f"向 {seller_name} 買原料：{trade_info['reason']}"
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
                logger.info(f"🍽️ {villager['name']} 向 {food_result['seller_name']} 購買並吃了 {food_result['food_name']}（花費 ${food_result['price']}，飽足度 +{food_result['satiety_restore']}）")
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
            seller_name = food_result.get('seller_name', '賣家')
            logger.info(f"🍽️ {villager['name']} 購買失敗：{food_result['reason']}")
            task["fail_reason"] = f"向 {seller_name} 買食物：{food_result['reason']}"
            return False


class BuyBeerEffect(TaskEffect):
    """在酒吧買啤酒效果（直接消耗，不經過背包）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        from ..game.production import get_food_info
        beer_info = get_food_info("beer")
        beer_price = beer_info["price"]
        beer_qty = 1  # 一次買 1 杯
        satiety_per_beer = beer_info["satiety_restore"]
        
        # 找酒保
        bartender = None
        for v in ctx.production.game_state.villagers.values():
            if v.get("occupation") == "bartender":
                bartender = v
                break
        
        if not bartender:
            logger.info(f"🍺 {villager['name']} 找不到酒保")
            return True  # 不算失敗，繼續社交
        
        # 檢查酒保是否在睡覺
        if bartender.get("state") == "sleeping":
            logger.info(f"🍺 {villager['name']} 無法買啤酒：酒保在睡覺")
            return True  # 不算失敗，繼續社交
        
        # 檢查酒保是否在酒吧內
        bartender_workplace = bartender.get("workplace")
        tavern = ctx.production.game_state.get_building_by_id(bartender_workplace)
        if not tavern:
            logger.info(f"🍺 {villager['name']} 酒保不在酒吧")
            return True
        
        # 檢查酒保距離酒吧門口是否夠近（8格內）
        bx, by = bartender.get("x", 0), bartender.get("y", 0)
        door_x, door_y = tavern.get("doorX", 0), tavern.get("doorY", 0)
        dist = ((bx - door_x) ** 2 + (by - door_y) ** 2) ** 0.5
        if dist > 8:
            logger.info(f"🍺 {villager['name']} 酒保不在酒吧附近")
            return True
        
        # 檢查酒保有沒有啤酒（背包 + 地上）
        bartender_inventory = bartender.get("inventory", [None] * 5)
        beer_in_bag = 0
        for slot in bartender_inventory:
            if slot and slot.get("item_id") == "beer":
                beer_in_bag += slot.get("quantity", 0)
        
        ground_beer = 0
        for item in ctx.production.game_state.get_items_by_owner(bartender["id"]):
            if item.get("item_id") == "beer":
                ground_beer += item.get("quantity", 0)
        
        total_beer = beer_in_bag + ground_beer
        if total_beer < 1:
            logger.info(f"🍺 {villager['name']} 酒保沒有啤酒可賣")
            return True
        
        # 決定實際購買數量
        actual_qty = min(beer_qty, total_beer)
        total_price = beer_price * actual_qty
        
        # 檢查村民有沒有錢
        buyer_money = villager.get("money", 0)
        if buyer_money < beer_price:
            logger.info(f"🍺 {villager['name']} 沒錢買啤酒（需要 ${beer_price}，擁有 ${buyer_money}）")
            return True
        
        # 錢不夠買想要的量，看能買多少
        if buyer_money < total_price:
            actual_qty = buyer_money // beer_price
            total_price = beer_price * actual_qty
        
        # 從酒保扣除啤酒（優先從背包扣）
        remaining = actual_qty
        for i, slot in enumerate(bartender_inventory):
            if remaining <= 0:
                break
            if slot and slot.get("item_id") == "beer":
                slot_qty = slot.get("quantity", 0)
                deduct = min(slot_qty, remaining)
                if slot_qty <= deduct:
                    bartender["inventory"][i] = None
                else:
                    slot["quantity"] = slot_qty - deduct
                remaining -= deduct
        
        # 背包不夠再從地上扣
        if remaining > 0:
            for item in ctx.production.game_state.get_items_by_owner(bartender["id"]):
                if remaining <= 0:
                    break
                if item.get("item_id") == "beer":
                    item_qty = item.get("quantity", 0)
                    deduct = min(item_qty, remaining)
                    if item_qty <= deduct:
                        ctx.production.game_state.remove_world_item(item["id"])
                    else:
                        item["quantity"] = item_qty - deduct
                    remaining -= deduct
        
        # 金錢轉移
        villager["money"] = buyer_money - total_price
        bartender["money"] = bartender.get("money", 0) + total_price
        
        # 直接喝掉（恢復飽足度，啤酒不進背包）
        stats = villager.get("stats", {})
        satiety_restore = actual_qty * satiety_per_beer
        stats["satiety"] = min(100, stats.get("satiety", 100) + satiety_restore)
        
        # 廣播交易動畫
        ctx.queue_broadcast({
            "type": "trade_animation",
            "data": {
                "from_pos": {"x": bx, "y": by},
                "to_pos": {"x": villager.get("x", 0), "y": villager.get("y", 0)},
                "item_id": "beer",
                "icon": "🍺",
                "quantity": actual_qty
            }
        })
        
        logger.info(f"🍺 {villager['name']} 向 {bartender['name']} 買了 {actual_qty} 杯啤酒並喝掉（花費 ${total_price}，飽足度 +{satiety_restore}）")
        return True  # 不管成功失敗都繼續社交


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
            
            # 取得羊的位置，廣播羊毛從羊飛到牧羊人的動畫
            sheep = ctx.sheep.game_state.sheep.get(sheep_id)
            if sheep:
                sheep_x = sheep.get("x", villager.get("x", 0))
                sheep_y = sheep.get("y", villager.get("y", 0))
                villager_x = villager.get("x", 0)
                villager_y = villager.get("y", 0)
                
                ctx.queue_broadcast({
                    "type": "trade_animation",
                    "data": {
                        "from_pos": {"x": sheep_x, "y": sheep_y},
                        "to_pos": {"x": villager_x, "y": villager_y},
                        "item_id": "wool",
                        "icon": "☁️",
                        "quantity": result["wool_qty"]
                    }
                })
            
            logger.info(f"☁️ {villager['name']} 剪了羊 {sheep_id} 的毛，獲得羊毛 x{result['quantity']}（{location}）")
            return True
        else:
            logger.info(f"☁️ {villager['name']} 剪毛失敗：{result['reason']}")
            task["fail_reason"] = f"剪羊毛：{result['reason']}"
            return False


class TendSheepEffect(TaskEffect):
    """照顧羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        sheep_id = task.get("sheep_id")
        result = ctx.sheep.execute_tend(villager, sheep_id)
        if result["success"]:
            logger.info(f"🐑 {villager['name']} 照顧了羊 {sheep_id}")
            return True
        else:
            logger.info(f"🐑 {villager['name']} 照顧羊失敗：{result['reason']}")
            task["fail_reason"] = f"照顧羊：{result['reason']}"
            return False



class BuySheepEffect(TaskEffect):
    """購買羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        seller_id = task.get("seller_id")
        
        # 檢查牧羊人是否在睡覺
        if seller_id:
            seller = ctx.production.game_state.get_villager(seller_id)
            if seller and seller.get("state") == "sleeping":
                logger.info(f"🐑 {villager['name']} 無法買羊：牧羊人在睡覺")
                task["fail_reason"] = "買羊：牧羊人在睡覺"
                return False
        
        result = ctx.sheep.execute_buy(villager, seller_id)
        if result["success"]:
            logger.info(f"🐑 {villager['name']} 向 {result['seller_name']} 購買了一隻活羊（花費 ${result['price']}）")
            return True
        else:
            seller_name = result.get('seller_name', '賣家')
            logger.info(f"🐑 {villager['name']} 買羊失敗：{result['reason']}")
            task["fail_reason"] = f"向 {seller_name} 買羊：{result['reason']}"
            return False


class SlaughterSheepEffect(TaskEffect):
    """宰殺羊效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        sheep_id = task.get("sheep_id")
        result = ctx.sheep.execute_slaughter(villager, sheep_id, ctx.production.use_tool)
        if result["success"]:
            loc1 = ctx.inventory.add_item(villager, "meat_raw", result["meat_qty"])
            loc2 = ctx.inventory.add_item(villager, "hide", result["hide_qty"])
            
            # 觸發動畫（生肉和羊皮從羊的位置飛到屠夫）
            villager_x = villager.get("x", 0)
            villager_y = villager.get("y", 0)
            
            # 生肉動畫
            ctx.queue_broadcast({
                "type": "trade_animation",
                "data": {
                    "from_pos": {"x": villager_x, "y": villager_y - 1},
                    "to_pos": {"x": villager_x, "y": villager_y},
                    "item_id": "meat_raw",
                    "icon": "🥩",
                    "quantity": result["meat_qty"]
                }
            })
            
            # 羊皮動畫（稍微延遲顯示）
            ctx.queue_broadcast({
                "type": "trade_animation",
                "data": {
                    "from_pos": {"x": villager_x + 0.5, "y": villager_y - 1},
                    "to_pos": {"x": villager_x, "y": villager_y},
                    "item_id": "hide",
                    "icon": "🟫",
                    "quantity": result["hide_qty"]
                }
            })
            
            logger.info(f"🔪 {villager['name']} 宰殺了羊 {sheep_id}，獲得生肉 x{result['meat_qty']}、羊皮 x{result['hide_qty']}（肉:{loc1}, 皮:{loc2}）")
            return True
        else:
            logger.info(f"🔪 {villager['name']} 宰殺失敗：{result['reason']}")
            task["fail_reason"] = f"宰殺羊：{result['reason']}"
            return False


# ==================== 煮飯相關效果 ====================

class CookEffect(TaskEffect):
    """煮飯效果 - 使用灶台把生肉煮成熟肉"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        inventory = villager.get("inventory", [None] * 5)
        
        # 1. 先計算總生肉數量並移除所有生肉格子
        total_raw_meat = 0
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == "meat_raw":
                total_raw_meat += slot.get("quantity", 1)
                villager["inventory"][i] = None  # 清空生肉格子
        
        if total_raw_meat == 0:
            logger.info(f"🍳 {villager['name']} 沒有生肉可煮")
            task["fail_reason"] = "煮飯：沒有生肉可煮"
            return False
        
        # 2. 使用 InventorySystem 加入熟肉（會自動合併已有的熟肉，超過10個放地上）
        location = ctx.inventory.add_item(villager, "meat", total_raw_meat)
        
        logger.info(f"🍳 {villager['name']} 用灶台把 {total_raw_meat} 個生肉煮成熟肉（{location}）")
        return True


class PickupEffect(TaskEffect):
    """撿起地上物品效果"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        world_item_id = task.get("world_item_id")
        item_id = task.get("item_id")
        
        if not world_item_id:
            logger.info(f"📦 {villager['name']} 沒有指定要撿的物品")
            task["fail_reason"] = "撿物品：沒有指定要撿的物品"
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
                task["fail_reason"] = "撿物品：背包滿了"
                return False
        
        # 找到並移除地上的物品（使用世界物品唯一 ID）
        item = game_state.remove_world_item(world_item_id)
        if not item:
            logger.info(f"📦 {villager['name']} 找不到物品 {item_id} (id: {world_item_id})")
            task["fail_reason"] = "撿物品：找不到物品"
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
            task["fail_reason"] = "賣物品：缺少參數"
            return False
        
        # 找商人
        game_state = ctx.production.game_state
        merchant = game_state.get_villager(merchant_id)
        if not merchant:
            logger.info(f"💰 {villager['name']} 找不到商人")
            task["fail_reason"] = "賣物品：找不到商人"
            return False
        
        merchant_name = merchant.get('name', '商人')
        
        # 檢查商人是否在睡覺
        if merchant.get("state") == "sleeping":
            logger.info(f"💰 {villager['name']} 無法賣物品：商人在睡覺")
            task["fail_reason"] = f"賣給 {merchant_name}：商人在睡覺"
            return False
        
        # 取得價格
        price = MERCHANT_BUY_PRICES.get(item_id, 5)
        
        # 檢查商人有沒有錢
        merchant_money = merchant.get("money", 0)
        if merchant_money < price:
            logger.info(f"💰 商人 {merchant['name']} 沒有足夠的錢 (需要 ${price}，擁有 ${merchant_money})")
            task["fail_reason"] = f"賣給 {merchant_name}：商人沒錢"
            return False
        
        # 計算賣家背包庫存
        inventory = villager.get("inventory", [None] * 5)
        bag_qty = 0
        bag_slots = []  # [(index, slot), ...]
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == item_id:
                bag_slots.append((i, slot))
                bag_qty += slot.get("quantity", 0)
        
        # 計算賣家地上庫存
        ground_items = []
        for item in game_state.get_items_by_owner(villager["id"]):
            if item.get("item_id") == item_id:
                ground_items.append(item)
        
        # 決定賣出來源：背包有則只賣背包，背包沒有則賣地上一堆
        if bag_qty > 0:
            # 賣背包的全部
            sell_qty = bag_qty
            sell_from = "bag"
        elif ground_items:
            # 賣地上隨機一堆（取第一堆）
            import random
            target_item = random.choice(ground_items)
            sell_qty = target_item.get("quantity", 1)
            sell_from = "ground"
        else:
            logger.info(f"💰 {villager['name']} 沒有 {item_id} 可賣")
            task["fail_reason"] = f"賣給 {merchant_name}：沒有 {item_id}"
            return False
        
        total_price = price * sell_qty
        
        # 檢查商人是否有足夠的錢買全部
        if merchant_money < total_price:
            # 商人錢不夠，只買得起部分
            sell_qty = merchant_money // price
            if sell_qty <= 0:
                logger.info(f"💰 商人 {merchant['name']} 錢不夠買任何 {item_id}")
                task["fail_reason"] = f"賣給 {merchant_name}：商人沒錢"
                return False
            total_price = price * sell_qty
        
        # 執行交易 - 從賣家扣除物品
        if sell_from == "bag":
            # 從背包扣
            remaining = sell_qty
            for i, slot in bag_slots:
                if remaining <= 0:
                    break
                slot_qty = slot.get("quantity", 0)
                deduct = min(slot_qty, remaining)
                if slot_qty <= deduct:
                    villager["inventory"][i] = None
                else:
                    slot["quantity"] = slot_qty - deduct
                remaining -= deduct
        else:
            # 從地上扣（整堆移除或部分扣除）
            item_qty = target_item.get("quantity", 0)
            if sell_qty >= item_qty:
                # 整堆移除
                game_state.remove_world_item(target_item["id"])
            else:
                # 部分扣除
                target_item["quantity"] = item_qty - sell_qty
        
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
        from ..game.production import get_material_price
        from ..data.item_categories import TOOLS

        merchant_id = task.get("merchant_id")
        item_id = task.get("item")

        if not merchant_id or not item_id:
            logger.info(f"💸 {villager['name']} 變賣失敗：缺少參數")
            task["fail_reason"] = "變賣物品：缺少參數"
            return False

        # 找商人
        game_state = ctx.production.game_state
        merchant = game_state.get_villager(merchant_id)
        if not merchant:
            logger.info(f"💸 {villager['name']} 找不到商人")
            task["fail_reason"] = "變賣物品：找不到商人"
            return False

        merchant_name = merchant.get('name', '商人')

        # 取得原價
        price = get_material_price(item_id, default=2)
        
        # 檢查商人有沒有錢
        merchant_money = merchant.get("money", 0)
        if merchant_money < price:
            logger.info(f"💸 商人 {merchant['name']} 沒有足夠的錢收購 {item_id}")
            task["fail_reason"] = f"變賣給 {merchant_name}：商人沒錢"
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
            task["fail_reason"] = f"變賣給 {merchant_name}：背包沒有 {item_id}"
            return False
        
        # 計算賣出數量（全部賣出）
        sell_qty = item_slot.get("quantity", 1)
        total_price = price * sell_qty
        
        # 檢查商人是否有足夠的錢買全部
        if merchant_money < total_price:
            sell_qty = merchant_money // price
            if sell_qty <= 0:
                logger.info(f"💸 商人 {merchant['name']} 錢不夠買任何 {item_id}")
                task["fail_reason"] = f"變賣給 {merchant_name}：商人沒錢"
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


# ==================== 商人收購效果 ====================

class BuyFromVillagerEffect(TaskEffect):
    """商人主動收購村民物品（一次收購一個物品）"""
    
    def execute(self, villager: dict, task: dict, ctx: TaskContext) -> bool:
        from ..data.supply_chain import MERCHANT_BUY_PRICES
        
        seller_id = task.get("seller_id")
        item_id = task.get("item")
        
        if not seller_id or not item_id:
            logger.info(f"🛒 {villager['name']} 收購失敗：缺少參數")
            task["fail_reason"] = "收購：缺少參數"
            return False
        
        # 找賣家
        game_state = ctx.production.game_state
        seller = game_state.get_villager(seller_id)
        if not seller:
            logger.info(f"🛒 {villager['name']} 找不到賣家")
            task["fail_reason"] = "收購：找不到賣家"
            return False
        
        seller_name = seller.get('name', '村民')
        
        # 檢查賣家是否在睡覺
        if seller.get("state") == "sleeping":
            logger.info(f"🛒 {villager['name']} 無法收購：{seller_name} 在睡覺")
            task["fail_reason"] = f"收購：{seller_name} 在睡覺"
            return False
        
        merchant_money = villager.get("money", 0)
        price = MERCHANT_BUY_PRICES.get(item_id, 5)
        
        if merchant_money < price:
            logger.info(f"🛒 {villager['name']} 金錢不足，無法收購")
            task["fail_reason"] = "收購：金錢不足"
            return False
        
        # 先檢查賣家背包
        seller_inventory = seller.get("inventory", [None] * 5)
        item_slot = None
        item_index = -1
        for i, slot in enumerate(seller_inventory):
            if slot and slot.get("item_id") == item_id:
                item_slot = slot
                item_index = i
                break
        
        if item_slot:
            # 從背包購買 1 個
            if item_slot.get("quantity", 1) <= 1:
                seller["inventory"][item_index] = None
            else:
                item_slot["quantity"] -= 1
        else:
            # 檢查地上
            ground_items = game_state.get_items_by_owner(seller_id)
            found = False
            for ground_item in ground_items:
                if ground_item.get("item_id") == item_id:
                    qty = ground_item.get("quantity", 1)
                    if qty <= 1:
                        game_state.remove_world_item(ground_item.get("world_item_id"))
                    else:
                        ground_item["quantity"] -= 1
                    found = True
                    break
            
            if not found:
                logger.info(f"🛒 {villager['name']} 收購失敗：{seller_name} 沒有 {item_id}")
                task["fail_reason"] = f"收購：{seller_name} 沒有 {item_id}"
                return False
        
        # 金錢轉移
        villager["money"] -= price
        seller["money"] = seller.get("money", 0) + price
        
        # 商人從出口獲得賣價（收購價 × 1.2），淨賺 20%
        export_sell_price = int(price * 1.2)
        villager["money"] += export_sell_price
        export_profit = export_sell_price - price
        
        logger.info(f"🛒 {villager['name']} 從 {seller_name} 收購了 {item_id} x1，花費 ${price}，獲利 ${export_profit}")
        
        # 取得物品圖示
        from ..data.items import ITEM_TYPES
        item_type = ITEM_TYPES.get(item_id)
        item_icon = item_type.icon if item_type else "📦"
        
        # 廣播交易動畫 1: 村民向商人飛物品
        ctx.queue_broadcast({
            "type": "trade_animation",
            "data": {
                "from_pos": {"x": seller.get("x", 0), "y": seller.get("y", 0)},
                "to_pos": {"x": villager.get("x", 0), "y": villager.get("y", 0)},
                "item_id": item_id,
                "icon": item_icon,
                "quantity": 1
            }
        })
        
        # 廣播交易動畫 2: 商人向村民飛錢袋
        ctx.queue_broadcast({
            "type": "trade_animation",
            "data": {
                "from_pos": {"x": villager.get("x", 0), "y": villager.get("y", 0)},
                "to_pos": {"x": seller.get("x", 0), "y": seller.get("y", 0)},
                "item_id": "coins",
                "icon": "💰",
                "quantity": price
            }
        })
        return True


# ==================== 效果註冊表 ====================

TASK_EFFECTS: Dict[str, TaskEffect] = {
    "eat": EatEffect(),
    "rest": RestEffect(),
    "sleep": RestEffect(),  # sleep 與 rest 使用相同效果（恢復體力）
    "socialize": SocializeEffect(),
    "work": WorkEffect(),
    "buy_tool": BuyToolEffect(),
    "buy_material": BuyMaterialEffect(),
    "buy_food": BuyFoodEffect(),
    "buy_beer": BuyBeerEffect(),
    "drop_one_item": DropItemEffect(),
    "drop_item": DropForFoodEffect(),
    "shear_sheep": ShearSheepEffect(),
    "tend_sheep": TendSheepEffect(),
    "buy_sheep": BuySheepEffect(),
    "slaughter_sheep": SlaughterSheepEffect(),
    "cook": CookEffect(),
    "pickup": PickupEffect(),
    "sell_to_merchant": SellToMerchantEffect(),
    "sell_excess": SellExcessEffect(),
    "buy_from_villager": BuyFromVillagerEffect(),
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
