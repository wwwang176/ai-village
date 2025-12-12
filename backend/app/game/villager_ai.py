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
            logger.warning("⚠️ OpenAI API Key 未設定，使用規則系統")
        else:
            logger.info(f"✅ OpenAI 已初始化，模型: {self.model}")
    
    async def make_decision(self, villager: dict, game_state) -> dict:
        """為村民做出行為決策"""
        
        # 如果沒有 API Key，使用規則系統
        if not self.client:
            return self._rule_based_decision(villager, game_state)
        
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
                logger.info(f"📤 System Prompt:\n{system_prompt[:200]}...")
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
                logger.info(f"   mood: {result.get('mood')}")
                logger.info(f"💰 Tokens: {response.usage.total_tokens}")
                logger.info(f"{'='*50}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI 決策錯誤: {e}")
            return self._rule_based_decision(villager, game_state)
    
    async def generate_dialogue(
        self,
        villager: dict,
        player: dict,
        action: str,
        game_state,
        player_message: Optional[str] = None
    ) -> dict:
        """生成對話內容"""
        
        if not self.client:
            return self._rule_based_dialogue(villager, action)
        
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
            return self._rule_based_dialogue(villager, action)
    
    async def generate_encounter(
        self,
        villager_a: dict,
        villager_b: dict,
        game_state
    ) -> dict:
        """生成兩個村民相遇的互動"""
        
        if not self.client:
            return self._rule_based_encounter(villager_a, villager_b)
        
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
            print(f"相遇生成錯誤: {e}")
            return self._rule_based_encounter(villager_a, villager_b)
    
    def _get_system_prompt(self, villager: dict, game_state) -> str:
        """根據村民狀態動態生成系統提示詞"""
        # 檢查是否有過剩物品可賣給商人
        sell_action = self._get_sell_action(villager, game_state)
        # 檢查是否可以工作（有原料或有供應商可以買）
        can_work = self._can_work(villager, game_state)
        # 檢查是否能買到食物
        can_buy_food = self._can_buy_food(villager, game_state)
        
        # 動態生成行為列表
        action_list = [
            "- go_home: 回家休息",
        ]
        
        # 只有在能獲得食物時才顯示選項
        if can_buy_food:
            action_list.insert(0, "- buy_food: 買食物吃")
        
        # 只有在能工作時才顯示選項（有原料或有錢買）
        if can_work:
            action_list.append("- go_work: 去工作地點工作")
        
        action_list.extend([
            "- go_market: 去市集逛逛（社交）",
            "- sleep: 睡覺（晚上）",
            "- wander: 隨意閒逛",
        ])
        
        # 動態加入賣東西選項（過剩物品）
        if sell_action:
            action_list.append(f"- sell_goods: {sell_action}")
        
        actions = "可用的行為類型：\n" + "\n".join(action_list)
        
        return f"""你是一個中古世紀村莊模擬遊戲的 AI 系統。
你需要根據村民的性格、狀態和環境，決定他們的下一步行為。

【重要】你只能從下方「可用的行為類型」中選擇！

{actions}

回應必須是 JSON 格式:
{{
  "action": "行為類型（必須是上方列出的選項之一）",
  "reason": "簡短的理由（村民心中所想，用繁體中文，10字以內）",
  "mood": "當前心情"
}}

注意：不需要提供座標，系統會自動處理移動。
只能選擇上方列出的行為！"""
    
    def _get_sell_action(self, villager: dict, game_state) -> str:
        """檢查村民是否有過剩物品可賣給商人
        
        過剩條件：
        1. 同類物品（背包+地上）>= 該物品的過剩門檻
        2. 或 現金 < 12 且肚子餓（hunger < 50）
        """
        from ..data.item_categories import TOOLS
        from ..data.supply_chain import EXCESS_THRESHOLDS
        from ..game.production import MATERIAL_PRICES
        
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
            # 只賣有價格的物品
            if item_id not in MATERIAL_PRICES:
                continue
            
            # 取得該物品的過剩門檻（預設 10）
            threshold = EXCESS_THRESHOLDS.get(item_id, 10)
            
            if qty >= threshold:
                excess_items.append((item_id, qty, "過剩"))
            elif is_broke_and_hungry and qty >= 1:
                excess_items.append((item_id, qty, "缺錢"))
        
        if not excess_items:
            return ""
        
        # 選擇數量最多的物品賣
        excess_items.sort(key=lambda x: x[1], reverse=True)
        best_item, best_qty, reason = excess_items[0]
        
        item_names = {
            "grain": "穀物", "ore": "礦石", "wood": "木材", "wool": "羊毛",
            "flour": "麵粉", "iron": "鐵錠", "cloth": "布料", "leather": "皮革",
            "hide": "獸皮", "meat_raw": "生肉", "bread": "麵包", "meat": "肉品",
            "furniture": "家具", "clothes": "衣服", "plank": "木板"
        }
        item_name = item_names.get(best_item, best_item)
        
        if reason == "過剩":
            return f"賣{item_name}給商人（庫存 {best_qty} 個，過剩）←【優先處理】"
        else:
            return f"變賣{item_name}換錢（現金 ${money}，肚子餓）←【緊急！】"
    
    def _can_work(self, villager: dict, game_state) -> bool:
        """檢查村民是否有足夠原料可以工作（有原料，或有錢+供應商有貨）"""
        from ..data.supply_chain import REQUIRED_MATERIALS, MATERIAL_PRODUCERS
        from ..game.production import MATERIAL_PRICES
        
        occupation = villager.get("occupation", "")
        required = REQUIRED_MATERIALS.get(occupation, [])
        
        # 屠夫特殊處理：需要羊或有錢買羊
        if occupation == "butcher":
            return self._can_butcher_work(villager, game_state)
        
        # 不需要原料的職業（農夫、牧羊人、礦工、伐木工）可以直接工作
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
        
        # 1. 屠夫已有羊 → 可以工作（去宰羊）
        owned_sheep = game_state.get_sheep_by_owner(villager["id"])
        if owned_sheep:
            logger.info(f"🔍 _can_work: {villager['name']}(butcher) 有 {len(owned_sheep)} 隻羊可宰")
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
    
    def _can_buy_food(self, villager: dict, game_state) -> bool:
        """檢查村民是否能獲得食物（背包有食物、或有錢+有賣家有貨）"""
        from ..data.supply_chain import FOOD_SELLERS
        
        inventory = villager.get("inventory", [])
        money = villager.get("money", 0)
        
        # 1. 背包有麵包 → 可以直接吃
        for slot in inventory:
            if slot and slot.get("item_id") == "bread":
                return True
        
        # 2. 背包有生肉 → 可以回家煮
        for slot in inventory:
            if slot and slot.get("item_id") == "meat_raw":
                return True
        
        # 3. 地上有自己的麵包可撿
        owned_items = game_state.get_items_by_owner(villager["id"])
        for item in owned_items:
            if item.get("item_id") == "bread":
                return True
        
        # 4. 有錢 + 有賣家有貨
        FOOD_PRICES = {"bread": 3, "meat_raw": 5}
        for food_item, seller_occupation in FOOD_SELLERS:
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
        time = game_state.get_time()
        stats = villager["stats"]
        
        # 計算飽足度（100 - 飢餓度）
        satiety = 100 - stats.get('hunger', 0)
        
        return f"""村民資訊:
- 姓名: {villager['name']}
- 職業: {villager['occupation']}
- 性格: {', '.join(villager['personality'])}
- 當前狀態: 體力 {stats['energy']:.0f}%, 飽足度 {satiety:.0f}%, 社交 {stats['social']:.0f}%

時間: 第 {time['day']} 天 {time['hour']:02d}:{time['minute']:02d}
最近記憶: {self._format_memories(villager.get('memories', []))}

請決定這個村民接下來應該做什麼。"""

    def _build_dialogue_prompt(
        self,
        villager: dict,
        player: dict,
        action: str,
        game_state,
        player_message: Optional[str]
    ) -> str:
        relationship = villager.get("relationships", {}).get("player", {})
        
        prompt = f"""你是 {villager['name']}，一個 {villager['age']} 歲的 {self._get_occupation_name(villager['occupation'])}。
性格: {', '.join(villager['personality'])}
與玩家的關係: 好感度 {relationship.get('affection', 0)}，熟悉度 {relationship.get('familiarity', 0)}

玩家對你 {self._get_action_name(action)}。"""
        
        if player_message:
            prompt += f"\n玩家說: \"{player_message}\""
        
        prompt += "\n\n請用符合你性格的方式回應。"
        
        return prompt

    def _build_encounter_prompt(self, villager_a: dict, villager_b: dict, game_state) -> str:
        rel_a = villager_a.get("relationships", {}).get(villager_b["id"], {})
        rel_b = villager_b.get("relationships", {}).get(villager_a["id"], {})
        
        return f"""兩個村民相遇:

村民 A:
- 姓名: {villager_a['name']}
- 職業: {villager_a['occupation']}  
- 性格: {', '.join(villager_a['personality'])}
- 對 B 的好感: {rel_a.get('affection', 0)}

村民 B:
- 姓名: {villager_b['name']}
- 職業: {villager_b['occupation']}
- 性格: {', '.join(villager_b['personality'])}
- 對 A 的好感: {rel_b.get('affection', 0)}

請模擬他們的相遇互動。"""

    def _format_memories(self, memories: List[dict]) -> str:
        if not memories:
            return "無"
        recent = memories[-3:]
        return "; ".join([m.get("event", "") for m in recent])
    
    def _get_occupation_name(self, occupation: str) -> str:
        names = {
            "tavern": "酒保", "church": "神父", "market": "商人",
            "blacksmith": "鐵匠", "bakery": "麵包師", "farm": "農夫", "house": "村民"
        }
        return names.get(occupation, "村民")
    
    def _get_action_name(self, action: str) -> str:
        names = {
            "greet": "打招呼", "chat": "聊天",
            "ask_info": "打聽消息", "give_gift": "送禮物"
        }
        return names.get(action, action)
    
    # === 規則系統備用 ===
    
    def _rule_based_decision(self, villager: dict, game_state) -> dict:
        """規則系統決策（無 API 時使用）"""
        import random
        
        stats = villager["stats"]
        time = game_state.get_time()
        hour = time["hour"]
        
        # 睡眠時間
        if (hour >= 22 or hour < 6) and stats["energy"] < 50:
            return {"action": "go_home", "target": None, "reason": "太累了，該睡覺了", "mood": "tired"}
        
        # 很餓 - 去買食物
        if stats["hunger"] > 70:
            return {"action": "buy_food", "target": None, "reason": "肚子餓了，去買點吃的", "mood": "hungry"}
        
        # 工作時間（根據職業不同）
        occupation = villager.get("occupation", "")
        
        # 各職業的工作時間（新職業系統）
        work_schedules = {
            # 食物鏈
            "farmer": (5, 14),        # 農夫：05:00-14:00
            "miller": (7, 16),        # 磨坊主：07:00-16:00
            "butcher": (6, 15),       # 屠夫：06:00-15:00
            "baker": (4, 13),         # 麵包師：04:00-13:00
            # 器具鏈
            "miner": (6, 15),         # 礦工：06:00-15:00
            "lumberjack": (6, 15),    # 伐木工：06:00-15:00
            "blacksmith": (8, 17),    # 鐵匠：08:00-17:00
            "carpenter": (8, 17),     # 木匠：08:00-17:00
            # 服飾鏈
            "shepherd": (5, 14),      # 牧羊人：05:00-14:00
            "weaver": (8, 17),        # 織工：08:00-17:00
            "tanner": (8, 17),        # 皮革匠：08:00-17:00
            "tailor": (9, 18),        # 裁縫：09:00-18:00
            # 特殊
            "merchant": (8, 18),      # 商人：08:00-18:00
        }
        
        # 根據職業工作時間
        if occupation in work_schedules:
            start, end = work_schedules[occupation]
            if start <= hour < end:
                return {"action": "go_work", "target": None, "reason": "該工作了", "mood": "neutral"}
        elif occupation and occupation != "house":
            # 預設工作時間：08:00-17:00
            if 8 <= hour < 17:
                return {"action": "go_work", "target": None, "reason": "該工作了", "mood": "neutral"}
        
        # 社交需求 - 主動找人聊天
        if stats["social"] < 30:
            return {"action": "socialize", "target": None, "reason": "想找人聊聊", "mood": "lonely"}
        
        # 隨機閒逛
        actions = ["wander", "rest", "go_market"]
        return {
            "action": random.choice(actions),
            "target": None,
            "reason": "隨便走走",
            "mood": "content"
        }
    
    def _rule_based_dialogue(self, villager: dict, action: str) -> dict:
        """規則系統對話（無 API 時使用）"""
        dialogues = {
            "greet": [
                "你好！今天天氣真好。",
                "嗨，見到你真高興。",
                "早安！有什麼事嗎？"
            ],
            "chat": [
                "最近村裡挺熱鬧的。",
                "聽說市集來了新商人呢。",
                "你有聽說老磨坊的事嗎？"
            ],
            "ask_info": [
                "你想知道什麼？我倒是聽說了一些事...",
                "這個嘛...讓我想想...",
                "村裡最近有些傳言呢。"
            ],
            "give_gift": [
                "這是給我的？太感謝了！",
                "哇，你真是太好了！",
                "我很感動，謝謝你！"
            ]
        }
        
        import random
        texts = dialogues.get(action, ["..."])
        
        return {
            "speaker": villager["name"],
            "text": random.choice(texts)
        }
    
    def _rule_based_encounter(self, villager_a: dict, villager_b: dict) -> dict:
        """規則系統相遇（無 API 時使用）"""
        import random
        
        will_interact = random.random() > 0.3
        
        if not will_interact:
            return {"will_interact": False}
        
        return {
            "will_interact": True,
            "dialogue": [
                {"speaker": villager_a["name"], "text": f"嗨，{villager_b['name']}！"},
                {"speaker": villager_b["name"], "text": "你好！最近怎麼樣？"},
                {"speaker": villager_a["name"], "text": "還不錯，就是有點忙。"}
            ],
            "relationship_changes": {
                "a_to_b": {"affection": 1, "familiarity": 2},
                "b_to_a": {"affection": 1, "familiarity": 2}
            }
        }
