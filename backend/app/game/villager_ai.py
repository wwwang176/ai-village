"""
村民 AI 系統 - GPT 整合
"""

import os
import json
import logging
import asyncio
import time
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VillagerAI")

# 是否顯示詳細的 OpenAI 請求/回應
DEBUG_OPENAI = os.getenv("DEBUG_OPENAI", "true").lower() == "true"


def format_memories(memories: List[dict], target_name: str = None, exclude_name: str = None, limit: int = 5, style: str = "simple") -> str:
    """
    格式化記憶列表
    
    Args:
        memories: 記憶列表
        target_name: 只包含與此人相關的記憶（可選）
        exclude_name: 排除與此人相關的記憶（可選）
        limit: 最多取幾條記憶
        style: 格式風格 - "simple"（分號分隔）或 "detailed"（換行+對象名）
    """
    if not memories:
        return "無"
    
    recent = memories[-limit:]
    
    # 過濾
    if target_name:
        recent = [m for m in recent if m.get("with") == target_name]
    elif exclude_name:
        recent = [m for m in recent if m.get("with") != exclude_name and m.get("summary")]
    
    if not recent:
        return "無"
    
    # 格式化
    prefix = "- " if style == "detailed" else ""
    separator = "\n" if style == "detailed" else "; "
    formatted = [f"{prefix}和 {m.get('with', '某人')}：{m.get('summary', '')}" for m in recent if m.get("summary")]
    return separator.join(formatted) if formatted else "無"


class VillagerAI:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # 每個村民的上次 API 呼叫時間（避免 rate limit）
        self._last_api_call: Dict[str, float] = {}
        self._api_interval = 4.0  # 每村民至少間隔 4 秒
        
        if not self.client:
            raise RuntimeError("❌ OpenAI API Key 未設定，無法啟動遊戲")
        
        logger.info(f"✅ OpenAI 已初始化，模型: {self.model}")
    
    # ========== 多輪決策系統 ==========
    
    async def make_destination_decision(self, villager: dict, game_state) -> dict:
        """第一階段決策：選擇要去哪裡"""
        villager_id = villager.get("id", "unknown")
        now = time.time()
        last_call = self._last_api_call.get(villager_id, 0)
        wait_time = self._api_interval - (now - last_call)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self._last_api_call[villager_id] = time.time()
        
        try:
            prompt = self._build_destination_prompt(villager, game_state)
            system_prompt = self._build_destination_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            if DEBUG_OPENAI:
                logger.info(f"\n{'='*50}")
                logger.info(f"🚶 [目的地決策] 村民: {villager.get('name')}")
                logger.info(f"📤 Prompt:\n{prompt}")
                logger.info(f"{'='*50}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if DEBUG_OPENAI:
                logger.info(f"📥 回傳: action={result.get('action')}, reason={result.get('reason')}")
                logger.info(f"💰 Tokens: {response.usage.total_tokens}")
            
            return result
            
        except Exception as e:
            logger.error(f"決策錯誤: {e}")
            return {"action": "wander", "reason": "不知道要做什麼"}
    
    async def make_action_decision(self, villager: dict, game_state) -> dict:
        """第二階段決策：在當前位置選擇要做什麼"""
        villager_id = villager.get("id", "unknown")
        now = time.time()
        last_call = self._last_api_call.get(villager_id, 0)
        wait_time = self._api_interval - (now - last_call)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self._last_api_call[villager_id] = time.time()
        
        try:
            context = game_state.get_location_context(villager)
            prompt = self._build_action_prompt(villager, game_state, context)
            system_prompt = self._build_action_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            if DEBUG_OPENAI:
                logger.info(f"\n{'='*50}")
                logger.info(f"🎯 [動作決策] 村民: {villager.get('name')} @ {context['location_name']}")
                logger.info(f"📤 Prompt:\n{prompt}")
                logger.info(f"{'='*50}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if DEBUG_OPENAI:
                logger.info(f"📥 回傳: action={result.get('action')}, target={result.get('target')}")
                logger.info(f"💰 Tokens: {response.usage.total_tokens}")
            
            return result
            
        except Exception as e:
            logger.error(f"動作決策錯誤: {e}")
            return {"action": "leave", "destination": "home", "reason": "不知道要做什麼"}
    
    def _build_destination_system_prompt(self) -> str:
        return """你是中古世紀村莊模擬遊戲中勤勞的村民。
你需要工作來維持生計，這是你生存的基本。

【行為優先級】（由高到低）
1. 工作賺錢（最重要）
2. 吃飽（飽足度低時）
3. 休息（體力低時）
4. 社交（以上都滿足時才考慮）

根據你的狀態、優先級和性格，選擇行動。

【回應格式】JSON
{
  "action": "行動代碼",
  "reason": "簡短理由（15字內）
}"""
    
    def _build_action_system_prompt(self) -> str:
        return """你是中古世紀村莊模擬遊戲中勤勞的村民。

【行為優先級】（由高到低）
1. 工作（在工作場所時優先工作）
2. 吃飽（有食物就吃）
3. 休息（在家時休息恢復體力）
4. 社交（以上都滿足時才聊天）

根據優先級選擇動作。

【回應格式】JSON
{
  "action": "動作代碼",
  "target": "目標ID（如果需要）",
  "item": "物品ID（如果需要）",
  "reason": "簡短理由（15字內）"
}"""
    
    def _build_destination_prompt(self, villager: dict, game_state) -> str:
        time_info = game_state.get_time()
        stats = villager["stats"]
        
        satiety = stats.get('satiety', 100)
        energy = stats.get('energy', 100)
        social = stats.get('social', 100)
        money = villager.get('money', 0)
        
        occupation_name = self._get_occupation_name(villager.get('occupation', ''))
        traits = villager.get("personality", [])
        traits_text = "、".join(traits) if traits else "普通"
        destinations = self._build_destination_list(villager, game_state)
        weather_info = game_state.get_weather_info()
        weather_text = f"{weather_info['icon']} {weather_info['name']}"
        memories_text = format_memories(villager.get('memories', []), limit=3)
        
        # 背包物品
        inventory_text = self._format_inventory(villager)
        
        # 地上物品（自己的）
        ground_text = self._format_ground_items(villager, game_state)
        
        return f"""【{villager['name']}】{occupation_name}，性格：{traits_text}

【狀態】
- 飽足：{satiety:.0f}%（{self._get_status_tag(satiety)}）
- 體力：{energy:.0f}%（{self._get_status_tag(energy)}）
- 社交：{social:.0f}%（{self._get_status_tag(social)}）
- 金錢：${money}

【背包】{inventory_text}
【地上】{ground_text}

【可用行動】
{destinations}

【時間】第 {time_info['day']} 天 {time_info['hour']:02d}:{time_info['minute']:02d}
【天氣】{weather_text}
【最近】{memories_text}

你要做什麼？"""
    
    def _build_action_prompt(self, villager: dict, game_state, context: dict) -> str:
        stats = villager["stats"]
        
        satiety = stats.get('satiety', 100)
        energy = stats.get('energy', 100)
        social = stats.get('social', 100)
        money = villager.get('money', 0)
        
        occupation_name = self._get_occupation_name(villager.get('occupation', ''))
        inventory_text = self._format_inventory(villager)
        nearby_text = self._format_nearby_villagers(context["nearby_villagers"], villager)
        trade_text = self._format_trade_options(context["trade_options"])
        actions_text = self._build_location_actions(villager, game_state, context)
        
        return f"""【{villager['name']}】{occupation_name}
【位置】{context['location_name']}

【狀態】飽足 {satiety:.0f}% | 體力 {energy:.0f}% | 社交 {social:.0f}% | ${money}

【背包】{inventory_text}

【周圍的人】
{nearby_text if nearby_text else "- 沒有人"}

【可交易】
{trade_text if trade_text else "- 無"}

【可執行動作】
{actions_text}

你要做什麼？"""
    
    def _build_destination_list(self, villager: dict, game_state) -> str:
        """建構可用行動列表（方向 A：一次決定，直接執行）"""
        import random
        actions = []
        money = villager.get("money", 0)
        hour = game_state.get_time()["hour"]
        is_night = hour >= 19 or hour < 4
        inventory = villager.get("inventory", [])
        
        # 1. go_work - 去工作賺錢
        if self._can_work(villager, game_state):
            work_desc = self._get_work_description(villager)
            actions.append(f"- go_work：{work_desc}")
        
        # 2. go_sell - 去賣東西給商人
        sell_info = self._get_sell_info(villager, game_state)
        if sell_info:
            actions.append(f"- go_sell：{sell_info}")
        
        # 3. go_buy_food - 去買食物
        food_info = self._get_buy_food_info(villager, game_state)
        if food_info:
            actions.append(f"- go_buy_food：{food_info}")
        
        # 4. eat - 吃背包裡的食物
        eat_info = self._get_eat_info(villager)
        if eat_info:
            actions.append(f"- eat：{eat_info}")
        
        # 4.5. go_cook - 回家煮生肉
        cook_info = self._get_cook_info(villager, game_state)
        if cook_info:
            actions.append(f"- go_cook：{cook_info}")
        
        # 5. go_pickup - 撿地上的物品
        pickup_info = self._get_pickup_info(villager, game_state)
        if pickup_info:
            actions.append(f"- go_pickup：{pickup_info}")
        
        # 6. go_buy_material - 去買工作材料
        material_info = self._get_buy_material_info(villager, game_state)
        if material_info:
            actions.append(f"- go_buy_material：{material_info}")
        
        # 7. go_buy_tool - 去買工具
        tool_info = self._get_buy_tool_info(villager, game_state)
        if tool_info:
            actions.append(f"- go_buy_tool：{tool_info}")
        
        # 8. go_sleep - 回家睡覺
        actions.append("- go_sleep：回家睡覺 → 恢復體力")
        
        # 8. go_market - 去市集社交
        actions.append("- go_market：去市集找人聊天 → 恢復社交")
        
        # 9. go_bar - 去酒吧
        if is_night or money >= 100:
            actions.append("- go_bar：去酒吧社交喝酒 → 恢復社交（需 $100）")
        
        # 10. wander - 閒逛
        actions.append("- wander：隨意閒逛")
        
        # 隨機排序，避免總是選第一個
        random.shuffle(actions)
        
        return "\n".join(actions)
    
    def _build_location_actions(self, villager: dict, game_state, context: dict) -> str:
        actions = []
        location_type = context["location_type"]
        trade_options = context["trade_options"]
        nearby = context["nearby_villagers"]
        
        if nearby:
            actions.append("- talk：找人聊天（需指定 target: villager_id）")
        if trade_options["can_buy"]:
            actions.append("- buy：購買物品（需指定 item）")
        if trade_options["can_sell"]:
            actions.append("- sell：出售物品（需指定 item）")
        if self._has_food_in_inventory(villager):
            actions.append("- eat：吃背包裡的食物")
        if location_type in ("farm", "mine", "workshop", "shop", "mill", "bakery", 
                             "blacksmith", "carpentry", "tannery", "tailor", "bar",
                             "butcher", "pasture"):
            if self._can_work(villager, game_state):
                actions.append("- work：在這裡工作")
        if location_type == "house":
            actions.append("- rest：在家休息")
        actions.append("- leave：離開此地（需指定 destination: market/home/workplace/bar/wander）")
        
        return "\n".join(actions) if actions else "- leave：離開此地"
    
    def _format_inventory(self, villager: dict) -> str:
        from ..data.items import ITEM_TYPES
        inventory = villager.get("inventory", [])
        items = []
        for slot in inventory:
            if slot:
                item_id = slot.get("item_id")
                qty = slot.get("quantity", 1)
                item_type = ITEM_TYPES.get(item_id)
                name = item_type.name if item_type else item_id
                items.append(f"{name} x{qty}")
        return "、".join(items) if items else "空"
    
    def _format_ground_items(self, villager: dict, game_state) -> str:
        """格式化地上物品（自己擁有的）"""
        from ..data.items import ITEM_TYPES
        owned_items = game_state.get_items_by_owner(villager["id"])
        if not owned_items:
            return "無"
        
        items = []
        for item in owned_items:
            item_id = item.get("item_id")
            qty = item.get("quantity", 1)
            item_type = ITEM_TYPES.get(item_id)
            name = item_type.name if item_type else item_id
            items.append(f"{name} x{qty}")
        return "、".join(items) if items else "無"
    
    def _format_nearby_villagers(self, nearby: List[dict], me: dict) -> str:
        if not nearby:
            return ""
        
        lines = []
        for v in nearby[:5]:
            occupation_name = self._get_occupation_name(v["occupation"])
            rel_desc = ""
            if v["familiarity"] > 30:
                rel_desc = f"，{v['affection_desc']}"
            elif v["familiarity"] > 10:
                rel_desc = f"，{v['familiarity_desc']}"
            lines.append(f"- {v['name']} ({v['id']})：{occupation_name}{rel_desc}")
        
        return "\n".join(lines)
    
    def _format_trade_options(self, trade_options: dict) -> str:
        from ..data.items import ITEM_TYPES
        lines = []
        
        for opt in trade_options.get("can_buy", [])[:3]:
            item_type = ITEM_TYPES.get(opt["item"])
            item_name = item_type.name if item_type else opt["item"]
            lines.append(f"- 向 {opt['from_name']} 購買 {item_name} ${opt['price']}")
        
        for opt in trade_options.get("can_sell", [])[:3]:
            item_type = ITEM_TYPES.get(opt["item"])
            item_name = item_type.name if item_type else opt["item"]
            lines.append(f"- 賣 {item_name} 給 {opt['to_name']} ${opt['price']}")
        
        return "\n".join(lines)
    
    def _has_food_in_inventory(self, villager: dict) -> bool:
        from ..data.item_categories import FOODS
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") in FOODS:
                return True
        return False
    
    async def generate_dialogue(
        self,
        villager: dict,
        player: dict,
        action: str,
        game_state,
        player_message: Optional[str] = None
    ) -> dict:
        """生成對話內容"""
        try:
            prompt = self._build_dialogue_prompt(villager, player, action, game_state, player_message)
            system_prompt = self._get_dialogue_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # 輸出請求日誌
            if DEBUG_OPENAI:
                logger.info(f"\n{'='*50}")
                logger.info(f"💬 [對話請求] 村民: {villager.get('name')}")
                logger.info(f"📤 System Prompt:\n{system_prompt}...")
                logger.info(f"📤 User Prompt:\n{prompt}")
                logger.info(f"{'='*50}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # temperature=0.9,
                max_tokens=400
            )
            
            result_text = response.choices[0].message.content
            
            # 輸出回應日誌
            if DEBUG_OPENAI:
                logger.info(f"📥 Response: {result_text}")
                logger.info(f"💰 Tokens: {response.usage.total_tokens}")
            
            return {
                "speaker": villager["name"],
                "text": result_text
            }
            
        except Exception as e:
            logger.error(f"對話生成錯誤: {e}")
            return None  # 跳過這次對話
    
    async def generate_encounter(
        self,
        villager_a: dict,
        villager_b: dict,
        game_state
    ) -> dict:
        """生成兩個村民相遇的互動"""
        try:
            prompt = self._build_encounter_prompt(villager_a, villager_b, game_state)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_encounter_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                # temperature=0.85,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"相遇生成錯誤: {e}")
            return None  # 跳過這次相遇
    
    def _get_status_tag(self, value: float) -> str:
        """取得狀態標記（隨機閾值讓 AI 行為更有變化）"""
        import random
        critical_threshold = random.randint(10, 30)  # 危急閾值：10~30
        low_threshold = random.randint(40, 60)       # 偏低閾值：40~60
        satisfied_threshold = random.randint(70, 90) # 滿足閾值：70~90
        
        if value < critical_threshold:
            return "危急"
        elif value < low_threshold:
            return "偏低"
        elif value >= satisfied_threshold:
            return "滿足"
        return "正常"
    
    def _get_sell_action(self, villager: dict, game_state) -> str:
        """檢查村民是否有過剩物品可賣給商人
        
        過剩條件：
        1. 同類物品（背包+地上）>= 該物品的過剩門檻
        2. 或 現金 < 12 且肚子餓（satiety < 50）
        """
        from ..data.item_categories import TOOLS
        from ..data.supply_chain import EXCESS_THRESHOLDS, MERCHANT_BUY_PRICES
        
        money = villager.get("money", 0)
        stats = villager.get("stats", {})
        satiety = stats.get("satiety", 100)
        
        # 檢查是否缺錢且餓
        is_broke_and_hungry = money < 12 and satiety < 50
        
        # 統計所有物品（背包 + 地上）
        item_counts = {}  # {item_id: total_qty}
        
        # 背包物品
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot:
                item_id = slot.get("item_id")
                if item_id and item_id not in TOOLS:
                    qty = slot.get("quantity", 1)
                    item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        # 地上物品（自己擁有的）
        ground_items = game_state.get_items_by_owner(villager["id"])
        for item in ground_items:
            item_id = item.get("item_id")
            if item_id and item_id not in TOOLS:
                qty = item.get("quantity", 1)
                item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        # 找出過剩的物品（依照分層門檻）
        excess_items = []
        for item_id, qty in item_counts.items():
            # 只賣商人會收購的物品
            if item_id not in MERCHANT_BUY_PRICES:
                continue
            
            # 取得該物品的過剩門檻（預設 10）
            threshold = EXCESS_THRESHOLDS.get(item_id, 10)
            
            if qty >= threshold:
                excess_items.append((item_id, qty, "過剩"))
            elif is_broke_and_hungry and qty >= 1:
                excess_items.append((item_id, qty, "缺錢"))
        
        if not excess_items:
            return ""
        
        from ..data.supply_chain import get_occupation_products
        
        occupation = villager.get("occupation", "")
        own_products = get_occupation_products(occupation)
        
        # 優先找自己職業的產品
        own_excess = [e for e in excess_items if e[0] in own_products]
        if own_excess:
            # 自己的產品中，選數量最多的
            own_excess.sort(key=lambda x: x[1], reverse=True)
            best_item, best_qty, reason = own_excess[0]
        else:
            # 沒有自己的產品，選數量最多的
            excess_items.sort(key=lambda x: x[1], reverse=True)
            best_item, best_qty, reason = excess_items[0]
        
        from ..data.items import ITEM_TYPES
        item_type = ITEM_TYPES.get(best_item)
        item_name = item_type.name if item_type else best_item
        
        if reason == "過剩":
            return f"賣{item_name}給商人（庫存 {best_qty} 個，過剩）←【優先處理】"
        else:
            return f"變賣{item_name}換錢←【優先處理】"
    
    def _can_work(self, villager: dict, game_state) -> bool:
        """檢查村民是否有足夠原料可以工作（有原料，或有錢+供應商有貨）"""
        from ..data.supply_chain import REQUIRED_MATERIALS, MATERIAL_PRODUCERS
        from ..game.production import MATERIAL_PRICES
        
        occupation = villager.get("occupation", "")
        required = REQUIRED_MATERIALS.get(occupation, [])
        
        # 屠夫特殊處理：需要羊或有錢買羊
        if occupation == "butcher":
            return self._can_butcher_work(villager, game_state)
        
        # 牧羊人特殊處理：需要有可剪毛的羊
        if occupation == "shepherd":
            return self._can_shepherd_work(villager, game_state)
        
        # 不需要原料的職業（農夫、礦工、伐木工）可以直接工作
        if not required:
            return True
        
        inventory = villager.get("inventory", [])
        
        # 檢查每種需要的原料（必須背包有原料才能工作）
        for material in required:
            has_material = False
            for slot in inventory:
                if slot and slot.get("item_id") == material and slot.get("quantity", 0) >= 1:
                    has_material = True
                    break
            
            if not has_material:
                logger.info(f"🔍 _can_work: {villager['name']}({occupation}) 缺少原料 {material}")
                return False
        
        logger.info(f"🔍 _can_work: {villager['name']}({occupation}) 原料充足，可以工作")
        return True
    
    def _can_butcher_work(self, villager: dict, game_state) -> bool:
        """檢查屠夫是否能工作（有羊或有錢買羊+牧羊人有羊賣）"""
        SHEEP_PRICE = 10
        money = villager.get("money", 0)
        
        # 1. 屠夫已有成羊 → 可以工作（去宰羊）
        owned_sheep = game_state.get_sheep_by_owner(villager["id"])
        adult_owned = [s for s in owned_sheep if s.get("is_adult")]
        if adult_owned:
            logger.info(f"🔍 _can_work: {villager['name']}(butcher) 有 {len(adult_owned)} 隻成羊可宰")
            return True
        
        # 2. 沒有羊，檢查有沒有錢買羊
        if money < SHEEP_PRICE:
            logger.info(f"🔍 _can_work: {villager['name']}(butcher) 沒羊且錢不夠(${money}<${SHEEP_PRICE})")
            return False
        
        # 3. 有錢，檢查牧羊人是否有成羊可賣（至少留 2 隻繁殖）
        for v in game_state.villagers.values():
            if v.get("occupation") != "shepherd":
                continue
            shepherd_sheep = game_state.get_sheep_by_owner(v["id"])
            adult_sheep = [s for s in shepherd_sheep if s.get("is_adult")]
            if len(adult_sheep) > 2:
                logger.info(f"🔍 _can_work: {villager['name']}(butcher) 有錢且牧羊人有 {len(adult_sheep)} 隻成羊")
                return True
        
        logger.info(f"🔍 _can_work: {villager['name']}(butcher) 有錢但牧羊人沒有足夠成羊")
        return False
    
    def _can_shepherd_work(self, villager: dict, game_state) -> bool:
        """檢查牧羊人是否能工作（有可剪毛的成羊）"""
        owned_sheep = game_state.get_sheep_by_owner(villager["id"])
        
        # 檢查是否有可剪毛的成羊（成羊且羊毛已長好）
        shearable_sheep = [
            s for s in owned_sheep 
            if s.get("is_adult") and s.get("wool_ready", False)
        ]
        
        if shearable_sheep:
            logger.info(f"🔍 _can_work: {villager['name']}(shepherd) 有 {len(shearable_sheep)} 隻可剪毛的羊")
            return True
        
        logger.info(f"🔍 _can_work: {villager['name']}(shepherd) 沒有可剪毛的羊")
        return False
    
    def _can_buy_food(self, villager: dict, game_state) -> bool:
        """檢查村民是否能獲得食物（背包有食物、地上有食物、或有錢+有賣家有貨）"""
        from ..data.supply_chain import FOOD_SELLERS
        
        inventory = villager.get("inventory", [])
        money = villager.get("money", 0)
        has_stove = game_state.get_stove_by_residence(villager["id"]) is not None
        
        # 1. 背包有麵包或熟肉 → 可以直接吃
        for slot in inventory:
            if slot and slot.get("item_id") in ("bread", "meat"):
                return True
        
        # 2. 背包有生肉 + 有灶台 → 可以回家煮
        if has_stove:
            for slot in inventory:
                if slot and slot.get("item_id") == "meat_raw":
                    return True
        
        # 3. 地上有自己的食物可撿
        owned_items = game_state.get_items_by_owner(villager["id"])
        for item in owned_items:
            if item.get("item_id") == "bread":
                return True
            if item.get("item_id") == "meat_raw" and has_stove:
                return True
        
        # 4. 有錢 + 有賣家有貨（生肉要有灶台）
        FOOD_PRICES = {"bread": 3, "meat_raw": 5}
        for food_item, seller_occupation in FOOD_SELLERS:
            # 生肉需要有灶台
            if food_item == "meat_raw" and not has_stove:
                continue
            price = FOOD_PRICES.get(food_item, 5)
            if money < price:
                continue
            # 檢查有沒有賣家有庫存
            if self._check_supplier_stock(game_state, seller_occupation, food_item):
                return True
        
        return False
    
    def _check_supplier_stock(self, game_state, supplier_occupation: str, material: str) -> bool:
        """檢查供應商是否有庫存"""
        for v in game_state.villagers.values():
            if v.get("occupation") != supplier_occupation:
                continue
            
            # 計算背包庫存
            inventory = v.get("inventory", [])
            inv_qty = 0
            for slot in inventory:
                if slot and slot.get("item_id") == material:
                    inv_qty += slot.get("quantity", 0)
            
            # 計算地上庫存
            ground_qty = 0
            owner_items = game_state.get_items_by_owner(v["id"])
            for item in owner_items:
                if item.get("item_id") == material:
                    ground_qty += item.get("quantity", 0)
            
            total = inv_qty + ground_qty
            if total > 0:
                logger.info(f"🔍 _check_supplier_stock: {v['name']}({supplier_occupation}) 有 {material} 背包:{inv_qty} 地上:{ground_qty}")
                return True
        
        logger.info(f"🔍 _check_supplier_stock: 沒有 {supplier_occupation} 有 {material} 庫存")
        return False

    def _get_dialogue_system_prompt(self) -> str:
        return """你是一個中古世紀村莊的村民。
根據你的性格和背景，用第一人稱回應玩家。
保持對話自然、簡短，符合中古世紀的語氣。
可以透露一些村莊的八卦或資訊。"""

    def _get_encounter_system_prompt(self) -> str:
        return """你是中古世紀村莊模擬遊戲的 AI 系統。
你需要模擬兩個村民相遇時的互動。

回應必須是 JSON 格式:
{
  "will_interact": true/false,
  "dialogue": [
    {"speaker": "名字", "text": "對話內容"},
    {"speaker": "名字", "text": "對話內容"}
  ],
  "relationship_changes": {
    "a_to_b": {"affection": 數字, "familiarity": 數字},
    "b_to_a": {"affection": 數字, "familiarity": 數字}
  }
}"""

    def _build_dialogue_prompt(
        self,
        villager: dict,
        player: dict,
        action: str,
        game_state,
        player_message: Optional[str]
    ) -> str:
        relationship = villager.get("relationships", {}).get("player", {})
        affection = relationship.get('affection', 0)
        familiarity = relationship.get('familiarity', 0)
        
        # 好感度文字描述
        affection_desc = self._get_affection_desc(affection)
        familiarity_desc = self._get_familiarity_desc(familiarity)
        
        prompt = f"""你是 {villager['name']}，一個 {villager['age']} 歲的 {self._get_occupation_name(villager['occupation'])}。
性格: {', '.join(villager['personality'])}
與玩家的關係:
- 好感度: {affection}（{affection_desc}）
- 熟悉度: {familiarity}（{familiarity_desc}）

玩家對你 {self._get_action_name(action)}。"""
        
        if player_message:
            prompt += f"\n玩家說: \"{player_message}\""
        
        prompt += "\n\n請用符合你性格的方式回應。"
        
        return prompt

    def _build_encounter_prompt(self, villager_a: dict, villager_b: dict, game_state) -> str:
        rel_a = villager_a.get("relationships", {}).get(villager_b["id"], {})
        rel_b = villager_b.get("relationships", {}).get(villager_a["id"], {})
        
        aff_a = rel_a.get('affection', 0)
        aff_b = rel_b.get('affection', 0)
        fam_a = rel_a.get('familiarity', 0)
        fam_b = rel_b.get('familiarity', 0)
        
        return f"""兩個村民相遇:

村民 A:
- 姓名: {villager_a['name']}
- 職業: {self._get_occupation_name(villager_a['occupation'])}
- 性格: {', '.join(villager_a['personality'])}
- 對 B 的好感: {aff_a}（{self._get_affection_desc(aff_a)}）
- 對 B 的熟悉度: {fam_a}（{self._get_familiarity_desc(fam_a)}）

村民 B:
- 姓名: {villager_b['name']}
- 職業: {self._get_occupation_name(villager_b['occupation'])}
- 性格: {', '.join(villager_b['personality'])}
- 對 A 的好感: {aff_b}（{self._get_affection_desc(aff_b)}）
- 對 A 的熟悉度: {fam_b}（{self._get_familiarity_desc(fam_b)}）

請模擬他們的相遇互動。"""

    def _get_occupation_name(self, occupation: str) -> str:
        from ..data.occupations import OCCUPATIONS
        occ = OCCUPATIONS.get(occupation)
        return occ.name if occ else "村民"
    
    def _get_action_name(self, action: str) -> str:
        names = {
            "greet": "打招呼", "chat": "聊天",
            "ask_info": "打聽消息", "give_gift": "送禮物"
        }
        return names.get(action, action)
    
    def _get_affection_desc(self, affection: int) -> str:
        from .game_state import get_affection_desc
        return get_affection_desc(affection)
    
    def _get_familiarity_desc(self, familiarity: int) -> str:
        from .game_state import get_familiarity_desc
        return get_familiarity_desc(familiarity)
    
    # ========== 新選項輔助方法 ==========
    
    def _get_work_description(self, villager: dict) -> str:
        """取得工作描述（含工具與材料需求）"""
        from ..data.supply_chain import get_occupation_products, REQUIRED_MATERIALS
        from ..data.items import ITEM_TYPES
        from ..game.inventory import OCCUPATION_TOOLS
        
        occupation = villager.get("occupation", "")
        products = get_occupation_products(occupation)
        required = REQUIRED_MATERIALS.get(occupation, [])
        tool_info = OCCUPATION_TOOLS.get(occupation)
        
        # 工具描述
        tool_desc = ""
        if tool_info:
            tool_desc = f"使用{tool_info['name']}"
        
        # 產出描述
        product_desc = ""
        if products:
            item_type = ITEM_TYPES.get(products[0])
            product_name = item_type.name if item_type else products[0]
            product_desc = f"生產{product_name}"
        else:
            product_desc = "賺錢"
        
        # 組合描述
        if tool_desc:
            base_desc = f"{tool_desc}工作 → {product_desc}"
        else:
            base_desc = f"去工作 → {product_desc}"
        
        # 材料描述
        if required:
            material_names = []
            for mat in required:
                item_type = ITEM_TYPES.get(mat)
                material_names.append(item_type.name if item_type else mat)
            material_desc = "、".join(material_names)
            return f"{base_desc}（需消耗：{material_desc}）"
        
        return base_desc
    
    def _get_sell_info(self, villager: dict, game_state) -> str:
        """取得可賣物品資訊"""
        sell_action = self._get_sell_action(villager, game_state)
        if sell_action:
            return sell_action
        return ""
    
    def _get_buy_food_info(self, villager: dict, game_state) -> str:
        """取得可購買食物資訊"""
        from ..data.supply_chain import FOOD_SELLERS
        
        # 背包已有食物 → 不顯示 go_buy_food（應該用 eat）
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") in ("bread", "meat"):
                return ""
        
        # 地上有食物 → 不顯示 go_buy_food（應該用 go_pickup）
        owned_items = game_state.get_items_by_owner(villager["id"])
        for item in owned_items:
            if item.get("item_id") in ("bread", "meat", "meat_raw"):
                return ""
        
        money = villager.get("money", 0)
        has_stove = game_state.get_stove_by_residence(villager["id"]) is not None
        FOOD_PRICES = {"bread": 3, "meat_raw": 5}
        
        for food_item, seller_occupation in FOOD_SELLERS:
            if food_item == "meat_raw" and not has_stove:
                continue
            price = FOOD_PRICES.get(food_item, 5)
            if money < price:
                continue
            if self._check_supplier_stock(game_state, seller_occupation, food_item):
                food_name = "麵包" if food_item == "bread" else "生肉"
                return f"去買{food_name}吃 → 恢復飽足度（需 ${price}）"
        return ""
    
    def _get_eat_info(self, villager: dict) -> str:
        """取得背包食物資訊"""
        from ..data.items import ITEM_TYPES
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") in ("bread", "meat"):
                item_type = ITEM_TYPES.get(slot.get("item_id"))
                name = item_type.name if item_type else slot.get("item_id")
                return f"吃{name} → 恢復飽足度"
        return ""
    
    def _get_cook_info(self, villager: dict, game_state) -> str:
        """取得可煮食物資訊（背包有生肉且有灶台）"""
        has_stove = game_state.get_stove_by_residence(villager["id"]) is not None
        if not has_stove:
            return ""
        
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") == "meat_raw":
                return "回家煮生肉 → 恢復飽足度"
        return ""
    
    def _get_pickup_info(self, villager: dict, game_state) -> str:
        """取得可撿地上物品資訊"""
        from ..data.items import ITEM_TYPES
        owned_items = game_state.get_items_by_owner(villager["id"])
        if not owned_items:
            return ""
        
        # 統計地上物品
        item_counts = {}
        for item in owned_items:
            item_id = item.get("item_id")
            qty = item.get("quantity", 1)
            item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        if not item_counts:
            return ""
        
        # 產生描述
        item_names = []
        item_ids = []
        for item_id, qty in item_counts.items():
            item_type = ITEM_TYPES.get(item_id)
            name = item_type.name if item_type else item_id
            item_names.append(f"{name} x{qty}")
            item_ids.append(item_id)
        
        items_desc = "、".join(item_names)
        ids_desc = "/".join(item_ids)
        return f"撿起地上的物品（需指定 item: {ids_desc}）"
    
    def _get_buy_tool_info(self, villager: dict, game_state) -> str:
        """取得可購買工具資訊"""
        from ..game.inventory import OCCUPATION_TOOLS
        
        occupation = villager.get("occupation", "")
        tool_info = OCCUPATION_TOOLS.get(occupation)
        
        # 此職業不需要工具
        if not tool_info:
            return ""
        
        # 檢查背包是否已有工具（且耐久度 > 0）
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") == tool_info["id"]:
                if slot.get("durability", 0) > 0:
                    return ""  # 已有可用工具
        
        # 沒有工具，檢查金錢是否足夠
        money = villager.get("money", 0)
        if money < tool_info["price"]:
            return ""  # 錢不夠
        
        return f"去鐵匠買{tool_info['name']}（需 ${tool_info['price']}）"
    
    def _get_buy_material_info(self, villager: dict, game_state) -> str:
        """取得可購買材料資訊"""
        from ..data.supply_chain import REQUIRED_MATERIALS, MATERIAL_PRODUCERS
        from ..game.production import MATERIAL_PRICES
        
        occupation = villager.get("occupation", "")
        required = REQUIRED_MATERIALS.get(occupation, [])
        if not required:
            return ""
        
        money = villager.get("money", 0)
        inventory = villager.get("inventory", [])
        
        for material in required:
            # 檢查背包是否已有
            has_material = False
            for slot in inventory:
                if slot and slot.get("item_id") == material and slot.get("quantity", 0) >= 1:
                    has_material = True
                    break
            
            if has_material:
                continue
            
            # 需要買材料
            price = MATERIAL_PRICES.get(material, 5)
            if money < price:
                continue
            
            supplier_occupation = MATERIAL_PRODUCERS.get(material)
            if supplier_occupation and self._check_supplier_stock(game_state, supplier_occupation, material):
                from ..data.items import ITEM_TYPES
                item_type = ITEM_TYPES.get(material)
                name = item_type.name if item_type else material
                return f"去買{name}（工作材料，需 ${price}）"
        
        return ""
