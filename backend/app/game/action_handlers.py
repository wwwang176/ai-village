"""
行為處理器系統 - 使用策略模式將 AI 決策轉換為任務排程
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState
    from .production import ProductionSystem
    from .inventory import InventorySystem
    from .sheep import SheepSystem

from .models import Task

logger = logging.getLogger("ActionHandler")


class ActionContext:
    """行為執行上下文"""
    
    def __init__(
        self,
        game_state: "GameState",
        production: "ProductionSystem",
        inventory: "InventorySystem",
        sheep: "SheepSystem"
    ):
        self.game_state = game_state
        self.production = production
        self.inventory = inventory
        self.sheep = sheep
    
    def resolve_target(self, villager: dict, action: str) -> Optional[Tuple[int, int]]:
        """解析目標位置"""
        return self.game_state.resolve_action_target(villager, action)
    
    def need_move(self, villager: dict, target: Optional[Tuple[int, int]]) -> bool:
        """判斷是否需要移動"""
        if not target:
            return False
        dx = target[0] - villager["x"]
        dy = target[1] - villager["y"]
        dist = (dx**2 + dy**2) ** 0.5
        return dist > 1.5
    
    def get_building(self, building_type: str) -> Optional[dict]:
        """取得建築物"""
        return self.game_state.get_building_by_type(building_type)
    
    def get_building_by_id(self, building_id: str) -> Optional[dict]:
        """根據 ID 取得建築物"""
        return self.game_state.get_building_by_id(building_id)


class ActionHandler(ABC):
    """行為處理器基類"""
    
    @abstractmethod
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        """創建任務列表"""
        pass
    
    def _find_owned_ground_item(self, villager: dict, item_id: str, ctx: ActionContext) -> Optional[dict]:
        """找村民擁有的地上物品"""
        owner_items = ctx.game_state.get_items_by_owner(villager["id"])
        for item in owner_items:
            if item.get("item_id") == item_id:
                return item
        return None
    
    def _try_pickup_owned(self, villager: dict, item_id: str, ctx: ActionContext) -> Optional[List[dict]]:
        """嘗試從地上撿起自己的物品，返回任務列表或 None"""
        ground_item = self._find_owned_ground_item(villager, item_id, ctx)
        if ground_item:
            logger.info(f"📦 {villager['name']} 地上有自己的 {item_id}，去撿起來")
            return [
                Task(type="move", target=(ground_item["x"], ground_item["y"])).to_dict(),
                Task(type="pickup", item_id=ground_item["id"], duration=1).to_dict()
            ]
        return None


# ==================== 基本行為處理器 ====================

class EatActionHandler(ActionHandler):
    """吃東西行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        target = ctx.resolve_target(villager, "eat")
        if ctx.need_move(villager, target):
            tasks.append(Task(type="move", target=target).to_dict())
        tasks.append(Task(type="eat", duration=3).to_dict())
        return tasks


class RestActionHandler(ActionHandler):
    """休息行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        target = ctx.resolve_target(villager, "go_home")
        if ctx.need_move(villager, target):
            tasks.append(Task(type="move", target=target).to_dict())
        tasks.append(Task(type="rest", duration=15).to_dict())
        return tasks


class SleepActionHandler(ActionHandler):
    """睡覺行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        target = ctx.resolve_target(villager, "sleep")
        if ctx.need_move(villager, target):
            tasks.append(Task(type="move", target=target).to_dict())
        tasks.append(Task(type="rest", duration=20).to_dict())
        return tasks


class GoMarketActionHandler(ActionHandler):
    """去市集行為（等待遇人）"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        target = ctx.resolve_target(villager, "go_market")
        if ctx.need_move(villager, target):
            tasks.append(Task(type="move", target=target).to_dict())
        # 在市集等待，等對話系統檢測到相遇後會自動開始對話
        tasks.append(Task(type="wait", duration=8).to_dict())
        return tasks


class WanderActionHandler(ActionHandler):
    """閒逛行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        target = ctx.resolve_target(villager, "wander")
        if target:
            tasks.append(Task(type="move", target=target).to_dict())
        return tasks


# ==================== 社交行為處理器 ====================

class SocializeActionHandler(ActionHandler):
    """社交行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        
        # 取得社交目標（透過 target_resolver）
        target, target_villager_id = ctx.game_state.target_resolver._get_social_target(villager)
        
        if target and target_villager_id:
            # 主動社交：記錄目標村民 ID
            villager["social_target_id"] = target_villager_id
            tasks.append(Task(
                type="move_to_villager", 
                target=target, 
                target_villager_id=target_villager_id
            ).to_dict())
            tasks.append(Task(
                type="initiate_chat", 
                target_villager_id=target_villager_id
            ).to_dict())
            logger.info(f"💬 {villager['name']} 準備去找 {target_villager_id} 聊天")
        elif target:
            # 沒找到人，去市集
            tasks.append(Task(type="move", target=target).to_dict())
            tasks.append(Task(type="socialize", duration=4).to_dict())
        
        return tasks


# ==================== 工作行為處理器 ====================

class GoWorkActionHandler(ActionHandler):
    """去工作行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        tasks = []
        
        # 1. 檢查是否有工具
        if not ctx.production.has_tool(villager):
            return self._handle_no_tool(villager, ctx)
        
        occupation = villager.get("occupation")
        
        # 2. 牧羊人特殊處理（不需要原料，透過羊系統）
        if occupation == "shepherd":
            sheep_tasks = ctx.sheep.create_shepherd_work_tasks(villager)
            if sheep_tasks:
                return sheep_tasks
            logger.info(f"🐑 {villager['name']} 沒有可以剪毛的羊")
            return tasks
        
        # 3. 屠夫特殊處理（不需要原料，透過羊系統買羊殺羊）
        if occupation == "butcher":
            butcher_tasks = ctx.sheep.create_butcher_work_tasks(villager)
            if butcher_tasks:
                return butcher_tasks
            logger.info(f"🔪 {villager['name']} 沒有可以宰殺的羊")
            return tasks
        
        # 4. 檢查是否有原料（L2/L3 職業）
        missing_material = self._check_missing_material(villager, ctx)
        if missing_material:
            return self._handle_missing_material(villager, missing_material, ctx)
        
        # 5. 有工具有原料，根據職業處理
        
        # 一般職業：移動到工作地點
        work_target = ctx.resolve_target(villager, "go_work")
        if ctx.need_move(villager, work_target):
            tasks.append(Task(type="move", target=work_target).to_dict())
        tasks.append(Task(type="work", duration=8).to_dict())
        
        return tasks
    
    def _handle_no_tool(self, villager: dict, ctx: ActionContext) -> List[dict]:
        """處理沒有工具的情況"""
        from .production import OCCUPATION_TOOLS
        
        occupation = villager.get("occupation", "")
        required_tool = OCCUPATION_TOOLS.get(occupation)
        
        # 1. 先嘗試撿地上自己的工具
        if required_tool:
            pickup_tasks = self._try_pickup_owned(villager, required_tool, ctx)
            if pickup_tasks:
                return pickup_tasks
        
        # 2. 沒有則去購買
        tasks = []
        
        # 檢查背包是否滿了
        inventory = villager.get("inventory", [None] * 5)
        has_empty_slot = any(slot is None for slot in inventory)
        
        if not has_empty_slot:
            logger.info(f"🎒 {villager['name']} 背包滿了，先回家放東西")
            home = ctx.get_building_by_id(villager.get("residence"))
            if home:
                home_target = (home["doorX"], home["doorY"] + 1)
                tasks.append(Task(type="move", target=home_target).to_dict())
                tasks.append(Task(type="drop_one_item", duration=1).to_dict())
        
        logger.info(f"🔧 {villager['name']} 沒有工具，改去鐵匠購買")
        blacksmith = ctx.get_building("blacksmith")
        if blacksmith:
            blacksmith_target = (blacksmith["doorX"], blacksmith["doorY"] + 1)
            tasks.append(Task(type="move", target=blacksmith_target).to_dict())
            tasks.append(Task(type="buy_tool", duration=2).to_dict())
        
        return tasks
    
    def _check_missing_material(self, villager: dict, ctx: ActionContext) -> Optional[str]:
        """檢查缺少的原料（庫存 < 需求量 就觸發補貨）"""
        from ..data.occupations import OCCUPATIONS
        
        occupation_id = villager.get("occupation", "")
        occupation = OCCUPATIONS.get(occupation_id)
        
        if not occupation or not occupation.input_materials:
            return None
        
        inventory = villager.get("inventory", [None] * 5)
        
        # 檢查每種原料是否足夠（從 occupations.py 讀取需求量）
        for material, required_qty in occupation.input_materials:
            owned_qty = ctx.inventory.count_item(inventory, material)
            if owned_qty < required_qty:  # 低於需求量就補貨
                return material
        
        return None
    
    def _handle_missing_material(self, villager: dict, material: str, ctx: ActionContext) -> List[dict]:
        """處理缺少原料的情況（補貨量 = 消耗 × 3）"""
        from ..data.supply_chain import MATERIAL_PRODUCERS, MATERIAL_QUANTITIES, RESTOCK_MULTIPLIER
        from ..game.production import MATERIAL_PRICES
        
        # 1. 先嘗試撿地上自己的原料
        pickup_tasks = self._try_pickup_owned(villager, material, ctx)
        if pickup_tasks:
            return pickup_tasks
        
        # 2. 計算補貨量 = 消耗 × 倍數
        consumption = MATERIAL_QUANTITIES.get(material, 1)
        want_quantity = consumption * RESTOCK_MULTIPLIER
        
        # 3. 檢查錢夠不夠（至少買 1 個）
        price_per_unit = MATERIAL_PRICES.get(material, 5)
        money = villager.get("money", 0)
        if money < price_per_unit:
            logger.info(f"💸 {villager['name']} 沒有足夠的錢買 {material}（需要 ${price_per_unit}，擁有 ${money}）")
            return []  # 返回空，讓 AI 重新決策（可能會選擇 sell_goods）
        
        # 4. 找出誰生產這個原料
        supplier_occupation = MATERIAL_PRODUCERS.get(material)
        if not supplier_occupation:
            return []
        
        # 找到供應商村民（有庫存 >= 1 就算有貨）
        supplier = self._find_supplier_villager(supplier_occupation, material, ctx)
        if not supplier:
            logger.info(f"🔍 {villager['name']} 找不到 {material} 的供應商")
            logger.info(f"🔧 {villager['name']} 缺少 {material}，但找不到供應商，無法工作")
            return []
        
        # 記錄交易資訊
        from .models import PendingTrade
        villager["pending_trade"] = PendingTrade(
            material=material,
            supplier_id=supplier["id"],
            quantity=want_quantity
        ).to_dict()
        
        logger.info(f"🛒 {villager['name']} 準備向 {supplier['name']} 購買 {material} x{want_quantity}")
        
        # 創建移動到供應商並交易的任務（帶上需求數量）
        return [
            Task(type="move_to_villager", target=(supplier["x"], supplier["y"]), target_villager_id=supplier["id"]).to_dict(),
            Task(type="buy_material", supplier_id=supplier["id"], material=material, quantity=want_quantity, duration=2).to_dict()
        ]
    
    def _find_supplier_villager(self, occupation: str, material: str, ctx: ActionContext) -> Optional[dict]:
        """找到有庫存的供應商（背包 + 地上物品，>= 1 就算有貨）"""
        candidates = []
        
        for v in ctx.game_state.villagers.values():
            if v.get("occupation") != occupation:
                continue
            
            # 計算背包庫存
            inventory = v.get("inventory", [None] * 5)
            bag_qty = 0
            for slot in inventory:
                if slot and slot.get("item_id") == material:
                    bag_qty += slot.get("quantity", 0)
            
            # 計算地上庫存（該村民擁有的）
            ground_qty = 0
            owner_items = ctx.game_state.get_items_by_owner(v["id"])
            for item in owner_items:
                if item.get("item_id") == material:
                    ground_qty += item.get("quantity", 0)
            
            # 總數 >= 1 就算有貨
            if bag_qty + ground_qty >= 1:
                candidates.append(v)
        
        if candidates:
            import random
            return random.choice(candidates)
        return None


# ==================== 購買食物行為處理器 ====================

class BuyFoodActionHandler(ActionHandler):
    """購買食物行為"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        from ..data.supply_chain import FOOD_SELLERS
        from .models import PendingFoodTrade
        
        inventory = villager.get("inventory", [None] * 5)
        
        # 1. 先檢查背包有沒有可以直接吃的食物（麵包）
        for slot in inventory:
            if slot and slot.get("item_id") == "bread":
                logger.info(f"🍞 {villager['name']} 背包有麵包，原地吃")
                return [Task(type="eat", duration=2).to_dict()]
        
        # 2. 檢查背包有沒有生肉，有的話回家煮
        for slot in inventory:
            if slot and slot.get("item_id") == "meat_raw":
                logger.info(f"🥩 {villager['name']} 背包有生肉，回家煮")
                stove = ctx.game_state.get_stove_by_residence(villager["id"])
                if stove:
                    return [
                        Task(type="move", target=(stove["x"], stove["y"])).to_dict(),
                        Task(type="cook", duration=3).to_dict()
                    ]
        
        # 3. 檢查地上有沒有自己的麵包可以撿（統一使用基類方法）
        ground_bread = self._find_owned_ground_item(villager, "bread", ctx)
        if ground_bread:
            tasks = []
            
            # 檢查背包是否滿了
            has_empty_slot = any(slot is None for slot in inventory)
            if not has_empty_slot:
                # 背包滿了，先丟一個非食物物品
                drop_index = self._find_non_food_slot(inventory)
                if drop_index is not None:
                    logger.info(f"🎒 {villager['name']} 背包滿了，先丟一個東西")
                    tasks.append(Task(type="drop_item", duration=1).to_dict())
            
            logger.info(f"🍞 {villager['name']} 地上有自己的麵包，去撿")
            tasks.extend([
                Task(type="move", target=(ground_bread["x"], ground_bread["y"])).to_dict(),
                Task(type="pickup", item_id=ground_bread["id"], duration=1).to_dict(),
                Task(type="eat", duration=2).to_dict()
            ])
            return tasks
        
        # 4. 背包沒食物，尋找有食物賣的村民
        for food_item, seller_occupation in FOOD_SELLERS:
            seller = self._find_food_seller(seller_occupation, food_item, ctx)
            if seller:
                # 記錄交易資訊
                villager["pending_food_trade"] = PendingFoodTrade(
                    food_item=food_item,
                    seller_id=seller["id"]
                ).to_dict()
                
                logger.info(f"🍽️ {villager['name']} 準備向 {seller['name']} 購買 {food_item}")
                
                tasks = [
                    Task(type="move_to_villager", target=(seller["x"], seller["y"]), target_villager_id=seller["id"]).to_dict(),
                    Task(type="buy_food", seller_id=seller["id"], food_item=food_item, duration=2).to_dict()
                ]
                
                # 如果是生肉，需要回家用灶台煮
                if food_item == "meat_raw":
                    home = ctx.get_building_by_id(villager.get("residence"))
                    if home:
                        # 取得灶台位置
                        stove = ctx.game_state.get_stove_by_residence(villager["id"])
                        if stove:
                            tasks.append(Task(type="move", target=(stove["x"], stove["y"])).to_dict())
                            tasks.append(Task(type="cook", duration=3).to_dict())
                            logger.info(f"🍳 {villager['name']} 買完肉會回家煮")
                
                return tasks
        
        # 找不到賣食物的人，回家自己煮（如果有生肉的話）
        logger.info(f"🍖 {villager['name']} 找不到賣食物的人，回家煮飯")
        tasks = []
        
        # 回家
        home = ctx.get_building_by_id(villager.get("residence"))
        if home:
            stove = ctx.game_state.get_stove_by_residence(villager["id"])
            if stove:
                tasks.append(Task(type="move", target=(stove["x"], stove["y"])).to_dict())
                tasks.append(Task(type="cook", duration=3).to_dict())
                return tasks
        
        # 沒有家或沒有灶台，只能挨餓
        logger.info(f"😢 {villager['name']} 沒有地方煮飯，只能挨餓")
        return tasks
    
    def _find_non_food_slot(self, inventory: list) -> Optional[int]:
        """找到一個非食物的背包格子（優先丟原料）"""
        from ..data.item_categories import FOODS, TOOLS
        
        # 優先丟原料（非食物、非工具）
        for i, slot in enumerate(inventory):
            if slot:
                item_id = slot.get("item_id")
                if item_id not in FOODS and item_id not in TOOLS:
                    return i
        
        # 其次丟工具
        for i, slot in enumerate(inventory):
            if slot:
                item_id = slot.get("item_id")
                if item_id in TOOLS:
                    return i
        
        return None
    
    def _find_food_seller(self, occupation: str, food_item: str, ctx: ActionContext) -> Optional[dict]:
        """找到有食物賣的村民"""
        candidates = []
        
        for v in ctx.game_state.villagers.values():
            if v.get("occupation") != occupation:
                continue
            
            # 檢查是否有食物庫存
            inventory = v.get("inventory", [None] * 5)
            for slot in inventory:
                if slot and slot.get("item_id") == food_item:
                    if slot.get("quantity", 0) >= 2:
                        candidates.append(v)
                        break
        
        if candidates:
            import random
            return random.choice(candidates)
        return None


# ==================== 販賣物品行為處理器 ====================

class SellGoodsActionHandler(ActionHandler):
    """販賣物品給商人"""
    
    def create_tasks(self, villager: dict, ctx: ActionContext) -> List[dict]:
        from ..data.supply_chain import SELLABLE_OCCUPATIONS, MERCHANT_BUY_PRICES
        
        occupation = villager.get("occupation", "")
        sellable_item = SELLABLE_OCCUPATIONS.get(occupation)
        
        if not sellable_item:
            logger.info(f"💰 {villager['name']} 沒有可賣的物品")
            return []
        
        # 檢查背包是否有可賣的物品
        inventory = villager.get("inventory", [None] * 5)
        has_item = False
        for slot in inventory:
            if slot and slot.get("item_id") == sellable_item:
                has_item = True
                break
        
        if not has_item:
            logger.info(f"💰 {villager['name']} 背包沒有 {sellable_item}")
            return []
        
        # 找商人
        merchant = self._find_merchant(ctx)
        if not merchant:
            logger.info(f"💰 {villager['name']} 找不到商人")
            return []
        
        # 記錄交易資訊
        villager["pending_sell"] = {
            "item": sellable_item,
            "merchant_id": merchant["id"]
        }
        
        logger.info(f"💰 {villager['name']} 準備向商人 {merchant['name']} 賣 {sellable_item}")
        
        tasks = []
        # 移動到商人位置
        if ctx.need_move(villager, (merchant["x"], merchant["y"])):
            tasks.append(Task(type="move_to_villager", target=(merchant["x"], merchant["y"]), target_villager_id=merchant["id"]).to_dict())
        
        # 執行販賣
        tasks.append(Task(type="sell_to_merchant", merchant_id=merchant["id"], item=sellable_item, duration=2).to_dict())
        
        return tasks
    
    def _find_merchant(self, ctx: ActionContext) -> Optional[dict]:
        """找到商人"""
        for v in ctx.game_state.villagers.values():
            if v.get("occupation") == "merchant":
                return v
        return None


# ==================== 行為註冊表 ====================

ACTION_HANDLERS: Dict[str, ActionHandler] = {
    "eat": EatActionHandler(),
    "rest": RestActionHandler(),
    "go_home": RestActionHandler(),  # go_home 同 rest
    "sleep": SleepActionHandler(),
    "go_market": GoMarketActionHandler(),
    "socialize": SocializeActionHandler(),
    "go_work": GoWorkActionHandler(),
    "buy_food": BuyFoodActionHandler(),
    "sell_goods": SellGoodsActionHandler(),
    "wander": WanderActionHandler(),
}


class ActionHandlerExecutor:
    """行為處理器執行器"""
    
    def __init__(self, context: ActionContext):
        self.context = context
    
    def create_tasks(self, villager: dict, action: str) -> List[dict]:
        """根據行為創建任務列表"""
        handler = ACTION_HANDLERS.get(action)
        
        if handler:
            return handler.create_tasks(villager, self.context)
        
        # 未知行為，預設閒逛
        return WanderActionHandler().create_tasks(villager, self.context)
