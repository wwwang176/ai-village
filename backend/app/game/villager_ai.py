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


class VillagerAI:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # 每個村民的上次 API 呼叫時間（避免 rate limit）
        self._last_api_call: Dict[str, float] = {}
        self._api_interval = 3.0  # 每村民至少間隔 3 秒
        
        if not self.client:
            raise RuntimeError("❌ OpenAI API Key 未設定，無法啟動遊戲")
        
        logger.info(f"✅ OpenAI 已初始化，模型: {self.model}")
    
    async def make_decision(self, villager: dict, game_state) -> dict:
        """為村民做出行為決策"""
        
        
        # 檢查此村民的 API 呼叫間隔
        villager_id = villager.get("id", "unknown")
        now = time.time()
        last_call = self._last_api_call.get(villager_id, 0)
        wait_time = self._api_interval - (now - last_call)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self._last_api_call[villager_id] = time.time()
        
        try:
            # 建構提示詞
            prompt = self._build_decision_prompt(villager, game_state)
            system_prompt = self._get_system_prompt(villager, game_state)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # 輸出請求日誌
            if DEBUG_OPENAI:
                logger.info(f"\n{'='*50}")
                logger.info(f"🤖 [決策請求] 村民: {villager.get('name', villager.get('id'))}")
                logger.info(f"📤 System Prompt:\n{system_prompt[:500]}...")
                logger.info(f"📤 User Prompt:\n{prompt}")
                logger.info(f"{'='*50}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 輸出回應日誌
            if DEBUG_OPENAI:
                logger.info(f"{'='*50}")
                logger.info(f"📥 OpenAI 回傳:")
                logger.info(f"   action: {result.get('action')}")
                logger.info(f"   reason: {result.get('reason')}")
                logger.info(f"💰 Tokens: {response.usage.total_tokens}")
                logger.info(f"{'='*50}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI 決策錯誤: {e}")
            return None  # 跳過這輪決策
    
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
                logger.info(f"📤 System Prompt:\n{system_prompt[:200]}...")
                logger.info(f"📤 User Prompt:\n{prompt}")
                logger.info(f"{'='*50}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9,
                max_tokens=300
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
                temperature=0.85,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"相遇生成錯誤: {e}")
            return None  # 跳過這次相遇
    
    def _get_system_prompt(self, villager: dict, game_state) -> str:
        """動態生成系統提示詞（只包含村民擁有的性格）"""
        from ..data.personalities import get_trait_description
        
        # 建構村民性格描述
        traits = villager.get("personality", [])
        trait_lines = []
        for trait in traits:
            desc = get_trait_description(trait)
            trait_lines.append(f"- {trait}：{desc}")
        traits_section = "\n".join(trait_lines) if trait_lines else "- 無特殊性格"
        
        return f"""你是中古世紀村莊模擬遊戲的村民 AI。
根據村民的性格和當前狀態，選擇最符合角色個性的行為。

【決策原則】
1. 🚨 危急（<20%）：必須立即處理，無視性格
2. ⚠️ 偏低（20-50%）：建議處理，可依性格延後
3. 正常（>50%）：自由選擇

【此村民的性格】
{traits_section}

【職業特性】
- 農夫/磨坊主/麵包師：工作可生產食物鏈物資，餓了也可選擇工作

【回應格式】JSON
{{
  "action": "行為類型（從可用行為中選擇）",
  "reason": "第一人稱理由（繁體中文，15字內）"
}}"""
    
    def _get_status_tag(self, value: float) -> str:
        """取得狀態標記"""
        if value < 20:
            return " 🚨 危急"
        elif value < 50:
            return " ⚠️ 偏低"
        return ""
    
    def _build_action_list(self, villager: dict, game_state) -> str:
        """建構可用行為列表"""
        import random
        action_list = []
        
        # 檢查條件
        sell_action = self._get_sell_action(villager, game_state)
        can_work = self._can_work(villager, game_state)
        can_buy_food = self._can_buy_food(villager, game_state)
        occupation = villager.get("occupation", "")
        food_chain_jobs = ["farmer", "miller", "baker"]
        money = villager.get("money", 0)
        hour = game_state.get_time()["hour"]
        is_night = hour >= 19 or hour < 4
        
        # 1. 賣東西（有貨才顯示）
        if sell_action:
            action_list.append(f"- sell_goods：{sell_action}")
        
        # 2. 吃飯（能吃才顯示，食物鏈職業要很餓才買）
        if can_buy_food:
            if occupation in food_chain_jobs:
                hunger = villager.get("stats", {}).get("hunger", 0)
                if hunger >= 60:  # 食物鏈職業：飢餓度 >= 60% 才買食物
                    action_list.append("- buy_food：買食物吃 → 恢復飽足度（無法恢復體力與社交滿足度）")
            else:
                action_list.append("- buy_food：買食物吃 → 恢復飽足度（無法恢復體力與社交滿足度）")
        
        # 3. 休息（很餓時不顯示，強迫先吃飯）
        hunger = villager.get("stats", {}).get("hunger", 0)
        if hunger < 90:  # 飢餓度 < 90% 才能回家睡覺
            action_list.append("- go_home：回家睡覺 → 恢復體力（無法恢復飽足度與社交滿足度）")
        
        # 4. 工作（能工作才顯示，食物鏈職業加註）
        if can_work:
            if occupation in food_chain_jobs:
                action_list.append("- go_work：產生食物 → 恢復飽足度（無法恢復體力與社交滿足度）")
            else:
                action_list.append("- go_work：去工作 → 賺錢")
        
        # 5. 社交（晚上且有錢時只顯示酒吧，否則顯示市集）
        if is_night and money >= 200:
            action_list.append("- go_bar：去酒吧 → 恢復社交滿足度（無法恢復飽足度與體力）")
        else:
            action_list.append("- go_market：去市集 → 恢復社交滿足度（無法恢復飽足度與體力）")
            if money >= 200:
                action_list.append("- go_bar：去酒吧 → 恢復社交滿足度（無法恢復飽足度與體力）")
        
        # 6. 閒逛
        action_list.append("- wander：閒逛 → 無特定目的（不恢復任何狀態）")
        
        # 隨機排序選項
        random.shuffle(action_list)
        
        return "\n".join(action_list)
    
    def _get_sell_action(self, villager: dict, game_state) -> str:
        """檢查村民是否有過剩物品可賣給商人
        
        過剩條件：
        1. 同類物品（背包+地上）>= 該物品的過剩門檻
        2. 或 現金 < 12 且肚子餓（hunger < 50）
        """
        from ..data.item_categories import TOOLS
        from ..data.supply_chain import EXCESS_THRESHOLDS, MERCHANT_BUY_PRICES
        
        money = villager.get("money", 0)
        stats = villager.get("stats", {})
        hunger = 100 - stats.get("hunger", 0)  # hunger 是飢餓度，轉換成飽足度
        
        # 檢查是否缺錢且餓
        is_broke_and_hungry = money < 12 and hunger < 50
        
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
        money = villager.get("money", 0)
        
        logger.info(f"🔍 _can_work: {villager['name']}({occupation}) 需要原料: {required}, 金錢: ${money}")
        
        # 檢查每種需要的原料
        for material in required:
            # 背包有原料嗎？
            has_material = False
            for slot in inventory:
                if slot and slot.get("item_id") == material and slot.get("quantity", 0) >= 1:
                    has_material = True
                    break
            
            if has_material:
                logger.info(f"   ✓ {material}: 背包有")
                continue  # 這個原料有了，檢查下一個
            
            # 沒有原料，檢查：有錢 + 供應商有貨
            price = MATERIAL_PRICES.get(material, 5)
            if money < price:
                logger.info(f"   ✗ {material}: 背包沒有，錢不夠(需${price})")
                return False  # 沒錢買
            
            # 檢查供應商有沒有庫存
            supplier_occupation = MATERIAL_PRODUCERS.get(material)
            if not supplier_occupation:
                logger.info(f"   ✗ {material}: 沒有供應商")
                return False  # 沒有供應商
            
            supplier_has_stock = self._check_supplier_stock(game_state, supplier_occupation, material)
            if not supplier_has_stock:
                logger.info(f"   ✗ {material}: {supplier_occupation}沒有庫存")
                return False  # 供應商沒貨
            
            logger.info(f"   ✓ {material}: 背包沒有，但有錢且{supplier_occupation}有貨")
        
        logger.info(f"   → 可以工作")
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
        
        # 1. 背包有麵包 → 可以直接吃
        for slot in inventory:
            if slot and slot.get("item_id") == "bread":
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
            for slot in inventory:
                if slot and slot.get("item_id") == material and slot.get("quantity", 0) >= 1:
                    return True
            
            # 計算地上庫存
            owner_items = game_state.get_items_by_owner(v["id"])
            for item in owner_items:
                if item.get("item_id") == material and item.get("quantity", 0) >= 1:
                    return True
        
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

    def _build_decision_prompt(self, villager: dict, game_state) -> str:
        """建構 User Prompt"""
        time_info = game_state.get_time()
        stats = villager["stats"]
        
        # 計算狀態值
        satiety = 100 - stats.get('hunger', 0)
        energy = stats.get('energy', 100)
        social = stats.get('social', 100)
        money = villager.get('money', 0)
        
        # 取得職業名稱
        occupation_name = self._get_occupation_name(villager.get('occupation', ''))
        
        # 建構可用行為列表
        action_list = self._build_action_list(villager, game_state)
        
        # 取得天氣資訊
        weather_info = game_state.get_weather_info()
        weather_text = f"{weather_info['icon']} {weather_info['name']}"
        if weather_info['stamina_drain'] > 0:
            weather_text += "（室外活動消耗更多體力）"
        
        # 取得村民所在位置
        building = game_state.get_building_at_position(int(villager["x"]), int(villager["y"]))
        if building:
            if game_state.is_outdoor_building(building["type"]):
                location_text = f"室外（{building['name']}）"
            else:
                location_text = f"{building['name']}內"
        else:
            location_text = "室外"
        
        return f"""【村民】{villager['name']}（{occupation_name}）
【性格】{', '.join(villager['personality'])}

【狀態】
- 飽足度：{satiety:.0f}%{self._get_status_tag(satiety)}
- 體力：{energy:.0f}%{self._get_status_tag(energy)}
- 社交滿足度：{social:.0f}%{self._get_status_tag(social)}
- 金錢：${money}

【可用行為】
{action_list}

【位置】{location_text}
【時間】第 {time_info['day']} 天 {time_info['hour']:02d}:{time_info['minute']:02d}
【天氣】{weather_text}
【記憶】{self._format_memories(villager.get('memories', []))}

請選擇一個行為。"""

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

    def _format_memories(self, memories: List[dict]) -> str:
        if not memories:
            return "無"
        recent = memories[-3:]
        return "; ".join([m.get("event", "") for m in recent])
    
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
