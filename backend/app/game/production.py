"""
生產系統 - 管理生產、工具使用、交易
"""

import random
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState
    from .inventory import InventorySystem

logger = logging.getLogger("Production")

# 職業需要的工具
OCCUPATION_TOOLS = {
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

# 原料價格表（平衡後：L1=$80/分, L2=$100/分, L3=$120/分）
MATERIAL_PRICES = {
    # L1 產出
    "grain": 2, "ore": 3, "wood": 2, "wool": 2,
    # L2 產出
    "flour": 3, "iron": 8, "cloth": 7, "leather": 10,
    "hide": 4, "meat_raw": 5,
    # L3 產出（麵包師 $80/分，因為食物是生存必需）
    "bread": 4,
    # 飲料
    "beer": 3,
}

# 食物資訊
FOOD_INFO = {
    "bread": {"name": "麵包", "price": 4, "satiety_restore": 35},
    "meat_raw": {"name": "生肉", "price": 5, "satiety_restore": 40},
    "meat": {"name": "肉品", "price": 6, "satiety_restore": 55},
    "beer": {"name": "啤酒", "price": 3, "satiety_restore": 2},
}


class ProductionSystem:
    """生產系統管理器"""
    
    def __init__(self, game_state: "GameState", inventory_system: "InventorySystem"):
        self.game_state = game_state
        self.inventory_system = inventory_system
    
    def use_tool(self, villager: dict) -> str:
        """使用村民的工具（消耗耐久度）
        
        返回:
            - "no_tool": 沒有需要的工具
            - "broken": 工具損壞
            - 數字字串: 剩餘耐久度百分比
            - "no_need": 此職業不需要工具
        """
        occupation = villager.get("occupation", "")
        required_tool = OCCUPATION_TOOLS.get(occupation)
        
        if not required_tool:
            return "no_need"
        
        inventory = villager.get("inventory", [None] * 5)
        tool_slot = None
        tool_index = -1
        
        for i, slot in enumerate(inventory):
            if slot and slot.get("item_id") == required_tool:
                tool_slot = slot
                tool_index = i
                break
        
        if not tool_slot:
            return "no_tool"
        
        # 消耗耐久度（每次工作消耗 5 點）
        durability = tool_slot.get("durability", 100)
        durability -= 5
        
        if durability <= 0:
            villager["inventory"][tool_index] = None
            return "broken"
        
        tool_slot["durability"] = durability
        return str(durability)
    
    def has_tool(self, villager: dict) -> bool:
        """檢查村民是否有工作需要的工具"""
        occupation = villager.get("occupation", "")
        required_tool = OCCUPATION_TOOLS.get(occupation)
        
        if not required_tool:
            return True
        
        inventory = villager.get("inventory", [None] * 5)
        for slot in inventory:
            if slot and slot.get("item_id") == required_tool:
                if slot.get("durability", 0) > 0:
                    return True
        
        return False
    
    def produce(self, villager: dict) -> dict:
        """執行生產，根據職業產出物品（從 occupations.py 讀取配方）
        
        返回:
            {"success": True/False, "product": "物品名", "quantity": 數量, "location": "背包/地上", "reason": "失敗原因"}
        """
        from ..data.occupations import OCCUPATIONS
        
        occupation_id = villager.get("occupation", "")
        occupation = OCCUPATIONS.get(occupation_id)
        
        if not occupation or not occupation.output_product:
            return {"success": False, "reason": "此職業不生產物品"}
        
        inventory = villager.get("inventory", [None] * 5)
        
        # 檢查原料是否足夠（從 occupation.input_materials 讀取）
        for input_item, input_qty in occupation.input_materials:
            owned_qty = self.inventory_system.count_item(inventory, input_item)
            if owned_qty < input_qty:
                return {"success": False, "reason": f"缺少原料 {input_item}（需要 {input_qty}，擁有 {owned_qty}）"}
        
        # 消耗原料
        for input_item, input_qty in occupation.input_materials:
            self.inventory_system.remove_item(villager, input_item, input_qty)
        
        # 產出物品（從 occupation 讀取）
        output_item = occupation.output_product
        output_qty = occupation.output_quantity
        
        # early_bird/night_owl 工作效率加成
        personality = villager.get("personality", [])
        game_time = self.game_state.get_time()
        hour = game_time.get("hour", 12)
        is_daytime = 6 <= hour < 18
        
        efficiency_bonus = 0
        if "early_bird" in personality:
            efficiency_bonus = 0.05 if is_daytime else -0.05  # 白天+5%、晚上-5%
        elif "night_owl" in personality:
            efficiency_bonus = -0.05 if is_daytime else 0.05  # 白天-5%、晚上+5%
        
        # 用機率方式實現效率（例如 +5% 表示有 5% 機率多產一個）
        if efficiency_bonus > 0 and random.random() < efficiency_bonus:
            output_qty += 1
        elif efficiency_bonus < 0 and random.random() < abs(efficiency_bonus):
            output_qty = max(1, output_qty - 1)
        
        location = self.inventory_system.add_item(villager, output_item, output_qty)
        
        return {
            "success": True,
            "product": output_item,  # 返回物品 ID，用於取得 icon
            "product_name": occupation.name + "產品",  # 顯示名稱
            "quantity": output_qty,
            "location": location
        }
    
    def execute_trade(self, buyer: dict, seller_id: str, item_id: str, 
                       want_quantity: int, price_per_unit: int, 
                       flexible_quantity: bool = False) -> dict:
        """通用交易執行
        
        Args:
            buyer: 買家村民
            seller_id: 賣家 ID
            item_id: 物品 ID
            want_quantity: 想買的數量
            price_per_unit: 單價
            flexible_quantity: 是否彈性數量（有多少買多少）
        
        Returns:
            交易結果 dict
        """
        seller = self.game_state.get_villager(seller_id)
        if not seller:
            return {"success": False, "reason": "找不到賣家"}
        
        seller_name = seller.get("name", "未知")
        
        # 計算賣家背包庫存
        seller_inventory = seller.get("inventory", [None] * 5)
        bag_qty = 0
        for slot in seller_inventory:
            if slot and slot.get("item_id") == item_id:
                bag_qty += slot.get("quantity", 0)
        
        # 計算賣家地上庫存
        ground_items = []
        ground_qty = 0
        for item in self.game_state.get_items_by_owner(seller["id"]):
            if item.get("item_id") == item_id:
                ground_items.append(item)
                ground_qty += item.get("quantity", 0)
        
        total_available = bag_qty + ground_qty
        
        # 決定實際購買數量
        if flexible_quantity:
            if total_available == 0:
                return {"success": False, "reason": f"賣家沒有 {item_id}", "seller_name": seller_name}
            quantity = min(want_quantity, total_available)
        else:
            if total_available < want_quantity:
                return {"success": False, "reason": f"賣家沒有足夠的 {item_id}", "seller_name": seller_name}
            quantity = want_quantity
        
        total_price = price_per_unit * quantity
        
        # 檢查買家金錢
        buyer_money = buyer.get("money", 0)
        if buyer_money < total_price:
            if flexible_quantity:
                # 買不起想要的量，看能買多少
                affordable_qty = buyer_money // price_per_unit
                if affordable_qty == 0:
                    return {"success": False, "reason": f"錢不夠（單價 ${price_per_unit}，擁有 ${buyer_money}）", "seller_name": seller_name}
                quantity = min(quantity, affordable_qty)
                total_price = price_per_unit * quantity
            else:
                return {"success": False, "reason": f"錢不夠（需要 ${total_price}）", "seller_name": seller_name}
        
        # 執行交易 - 金錢轉移
        buyer["money"] = buyer_money - total_price
        seller["money"] = seller.get("money", 0) + total_price
        
        # 從賣家扣除物品（優先從背包）
        remaining = quantity
        from_bag = 0  # 追蹤從背包扣了多少
        
        # 1. 先從背包扣
        for i, slot in enumerate(seller_inventory):
            if remaining <= 0:
                break
            if slot and slot.get("item_id") == item_id:
                slot_qty = slot.get("quantity", 0)
                deduct = min(slot_qty, remaining)
                if slot_qty <= deduct:
                    seller["inventory"][i] = None
                else:
                    slot["quantity"] = slot_qty - deduct
                remaining -= deduct
                from_bag += deduct
        
        # 2. 不夠再從地上扣（轉移擁有者，買家自己去撿）
        for item in ground_items:
            if remaining <= 0:
                break
            item_qty = item.get("quantity", 0)
            deduct = min(item_qty, remaining)
            if item_qty <= deduct:
                # 整個轉移擁有者
                item["owner_id"] = buyer["id"]
            else:
                # 部分扣除：原物品減量，買家在相同位置獲得新物品
                item["quantity"] = item_qty - deduct
                self.game_state.add_world_item(
                    item_id=item_id,
                    x=item.get("x", 0),
                    y=item.get("y", 0),
                    owner_id=buyer["id"],
                    quantity=deduct
                )
            remaining -= deduct
        
        # 只有從背包扣的數量才放入買家背包（地上的由買家自己去撿）
        location = "ground"
        if from_bag > 0:
            location = self.inventory_system.add_item(buyer, item_id, from_bag)
        
        return {
            "success": True,
            "item_id": item_id,
            "quantity": quantity,
            "from_bag": from_bag,
            "from_ground": quantity - from_bag,
            "price": total_price,
            "seller_name": seller_name,
            "location": location,
            "seller_pos": {"x": seller.get("x", 0), "y": seller.get("y", 0)},
            "buyer_pos": {"x": buyer.get("x", 0), "y": buyer.get("y", 0)}
        }
    
    def execute_food_purchase(self, buyer: dict, task: dict) -> dict:
        """執行食物購買"""
        seller_id = task.get("seller_id")
        food_item = task.get("food_item")
        food_info = FOOD_INFO.get(food_item, {"name": food_item, "price": 4, "satiety_restore": 30})
        
        result = self.execute_trade(
            buyer=buyer,
            seller_id=seller_id,
            item_id=food_item,
            want_quantity=2,
            price_per_unit=food_info["price"],
            flexible_quantity=False
        )
        
        if result["success"]:
            if "pending_food_trade" in buyer:
                del buyer["pending_food_trade"]
            result["food_name"] = food_info["name"]
            result["food_item"] = food_item
            result["satiety_restore"] = 0
            result["need_cook"] = food_item == "meat_raw"
        
        return result
    
    def execute_material_trade(self, buyer: dict, task: dict) -> dict:
        """執行原料交易（有多少買多少）"""
        supplier_id = task.get("supplier_id")
        material = task.get("material")
        want_quantity = task.get("quantity", 3)
        price_per_unit = MATERIAL_PRICES.get(material, 5)
        
        result = self.execute_trade(
            buyer=buyer,
            seller_id=supplier_id,
            item_id=material,
            want_quantity=want_quantity,
            price_per_unit=price_per_unit,
            flexible_quantity=True
        )
        
        if result["success"]:
            if "pending_trade" in buyer:
                del buyer["pending_trade"]
            result["material"] = material
        
        return result
