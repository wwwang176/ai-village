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
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
        
        # 每個村民的上次 API 呼叫時間（避免 rate limit）
        self._last_api_call: Dict[str, float] = {}
        self._api_interval = 4.0  # 每村民至少間隔 4 秒
        
        if not self.client:
            raise RuntimeError("❌ OpenAI API Key 未設定，無法啟動遊戲")
        
        logger.info(f"✅ OpenAI 已初始化，模型: {self.model}")
    
    # ========== 多輪決策系統 ==========
    
    async def make_decision(self, villager: dict, game_state) -> dict:
        """統一決策：選擇要執行的動作（合併目的地和動作決策）"""
        villager_id = villager.get("id", "unknown")
        now = time.time()
        last_call = self._last_api_call.get(villager_id, 0)
        wait_time = self._api_interval - (now - last_call)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self._last_api_call[villager_id] = time.time()
        
        try:
            # 取得可用動作和 tools schema
            action_info = self._get_available_destination_actions(villager, game_state)
            tools = self._build_destination_tools(action_info)
            
            prompt = self._build_destination_prompt(villager, game_state, action_info)
            system_prompt = self._build_destination_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            if DEBUG_OPENAI:
                logger.info(f"\n{'='*50}")
                logger.info(f"🎯 [決策] 村民: {villager.get('name')}")
                logger.info(f"📤 Prompt:\n{prompt}")
                logger.info(f"{'='*50}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "choose_action"}},
                max_completion_tokens=150
            )
            
            # 解析 function call 結果
            tool_call = response.choices[0].message.tool_calls[0]
            result = json.loads(tool_call.function.arguments)
            
            if DEBUG_OPENAI:
                logger.info(f"📥 回傳: action={result.get('action')}, reason={result.get('reason')}")
                logger.info(f"💰 Tokens: {response.usage.total_tokens}")
            
            return result
            
        except Exception as e:
            logger.error(f"決策錯誤: {e}")
            return {"action": "wander", "reason": "不知道要做什麼"}
    
    # ========== Function Calling Tools 構建 ==========
    
    def _get_available_destination_actions(self, villager: dict, game_state) -> dict:
        """取得可用的動作列表（統一決策系統）"""
        actions = []
        pickup_items = []
        talk_targets = []
        money = villager.get("money", 0)
        hour = game_state.get_time()["hour"]
        is_night = hour >= 19 or hour < 4
        
        # 取得位置資訊
        context = game_state.get_location_context(villager)
        location_type = context["location_type"]
        nearby = context["nearby_villagers"]
        
        # 1. go_work（商人除外，商人改用 go_buy_goods）
        if villager.get("occupation") != "merchant" and self._can_work(villager, game_state):
            actions.append("go_work")
        
        # 2. go_sell
        sell_items = self._get_sellable_items_list(villager, game_state)
        if sell_items:
            actions.append("go_sell")
        
        # 3. go_buy_food
        if self._get_buy_food_info(villager, game_state):
            actions.append("go_buy_food")
        
        # 4. eat
        if self._get_eat_info(villager):
            actions.append("eat")
        
        # 4.5. go_cook
        if self._get_cook_info(villager, game_state):
            actions.append("go_cook")
        
        # 5. go_pickup
        pickup_info = self._get_pickup_info(villager, game_state)
        if pickup_info:
            actions.append("go_pickup")
            ground_items = self._get_ground_items_list(villager, game_state)
            pickup_items = ground_items
        
        # 6. go_buy_material
        if self._get_buy_material_info(villager, game_state):
            actions.append("go_buy_material")
        
        # 7. go_buy_tool
        if self._get_buy_tool_info(villager, game_state):
            actions.append("go_buy_tool")
        
        # 7.5. go_buy_goods（商人專用：主動收購）
        buy_targets = []
        buy_goods_info = self._get_buy_goods_targets(villager, game_state)
        if buy_goods_info:
            actions.append("go_buy_goods")
            buy_targets = [t["villager_id"] for t in buy_goods_info]
        
        # 8. go_sleep（總是可用）
        actions.append("go_sleep")
        
        # 9. go_plaza（總是可用）
        actions.append("go_plaza")
        
        # 10. go_bar
        if is_night or money >= 100:
            actions.append("go_bar")
        
        # 11. wander（總是可用）
        actions.append("wander")
        
        # === 位置相關動作 ===
        
        # 12. talk（周圍有人時）
        if nearby:
            actions.append("talk")
            talk_targets = [v["id"] for v in nearby]
        
        # 13. buy_beer（在酒吧且酒保在附近）
        if location_type == "tavern":
            bartender_nearby = any(v.get("occupation") == "bartender" for v in nearby)
            if bartender_nearby and money > 100:
                actions.append("buy_beer")
        
        # 14. idle（總是可用）
        actions.append("idle")
        
        return {
            "actions": actions,
            "pickup_items": pickup_items,
            "sell_items": sell_items,
            "talk_targets": talk_targets,
            "buy_targets": buy_targets,
            "context": context
        }
    
    def _get_ground_items_list(self, villager: dict, game_state) -> List[str]:
        """取得地上可撿物品列表"""
        items = []
        villager_id = villager.get("id")
        for obj in game_state.map_data.get("objects", []):
            if obj.get("type") == "ground_item" and obj.get("owner_id") == villager_id:
                item_id = obj.get("item_id")
                if item_id and item_id not in items:
                    items.append(item_id)
        return items
    
    def _get_sellable_items_list(self, villager: dict, game_state) -> List[str]:
        """取得可賣給商人的物品列表（必須過剩或缺錢且餓）"""
        from ..data.item_categories import TOOLS
        from ..data.supply_chain import EXCESS_THRESHOLDS, MERCHANT_BUY_PRICES
        
        money = villager.get("money", 0)
        stats = villager.get("stats", {})
        satiety = stats.get("satiety", 100)
        is_broke_and_hungry = money < 12 and satiety < 50
        
        # 統計所有物品（背包 + 地上）
        item_counts = {}
        
        # 背包物品
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot:
                item_id = slot.get("item_id")
                if item_id and item_id not in TOOLS:
                    qty = slot.get("quantity", 1)
                    item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        # 地上物品
        ground_items = game_state.get_items_by_owner(villager["id"])
        for item in ground_items:
            item_id = item.get("item_id")
            if item_id and item_id not in TOOLS:
                qty = item.get("quantity", 1)
                item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        # 找出過剩或缺錢可賣的物品
        items = []
        for item_id, qty in item_counts.items():
            if item_id not in MERCHANT_BUY_PRICES:
                continue
            threshold = EXCESS_THRESHOLDS.get(item_id, 10)
            if qty >= threshold or (is_broke_and_hungry and qty >= 1):
                items.append(item_id)
        
        return items
    
    def _build_destination_tools(self, action_info: dict) -> List[dict]:
        """構建決策的 tools schema（統一決策系統）"""
        available_actions = action_info["actions"]
        pickup_items = action_info.get("pickup_items", [])
        sell_items = action_info.get("sell_items", [])
        talk_targets = action_info.get("talk_targets", [])
        
        # 基本 properties
        properties = {
            "action": {
                "type": "string",
                "enum": available_actions,
                "description": "要執行的動作"
            },
            "reason": {
                "type": "string",
                "description": "選擇這個動作的原因（15字內）"
            }
        }
        required = ["action", "reason"]
        
        # 如果有 go_pickup 或 go_sell，加入 item 參數
        all_items = []
        if "go_pickup" in available_actions and pickup_items:
            all_items.extend(pickup_items)
        if "go_sell" in available_actions and sell_items:
            all_items.extend([i for i in sell_items if i not in all_items])
        
        if all_items:
            properties["item"] = {
                "type": ["string", "null"],
                "enum": all_items + [None],
                "description": "要操作的物品（go_pickup/go_sell 時需要）"
            }
            required.append("item")
        
        # 如果有 talk，加入 target 參數
        if "talk" in available_actions and talk_targets:
            properties["target"] = {
                "type": ["string", "null"],
                "enum": talk_targets + [None],
                "description": "目標村民 ID（talk 時需要）"
            }
            required.append("target")
        
        # 如果有 go_buy_goods，加入 buy_target 參數
        buy_targets = action_info.get("buy_targets", [])
        if "go_buy_goods" in available_actions and buy_targets:
            properties["buy_target"] = {
                "type": ["string", "null"],
                "enum": buy_targets + [None],
                "description": "要收購的村民 ID（go_buy_goods 時需要）"
            }
            required.append("buy_target")
        
        return [{
            "type": "function",
            "function": {
                "name": "choose_action",
                "description": "選擇要執行的動作",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }]
    
    # ========== System Prompts ==========
    
    def _build_destination_system_prompt(self) -> str:
        return """你是中古世紀村莊模擬遊戲中勤勞的村民。
你需要工作來維持生計，這是你生存的基本。

【行為優先級】（由高到低）
1. 工作賺錢（最重要）
2. 吃飽（飽足度低時）
3. 休息（體力低時）
4. 社交（以上都滿足時才考慮）

【行為注意事項】
1. 如果金錢超過200，則「吃飽」比「工作賺錢」優先級更高
2. 工作必須有工具，缺少工具可以去買或撿地上的
3. 工作必須要有材料，缺少材料可以去買或撿地上的
4. 飽足滿足時，不需要吃東西
5. 白天且體力滿足時，不需要睡覺
6. 如果行為失敗過，就不要再重覆選擇

【村莊經濟系統】

食物產業鏈（只有以下三條路徑能解餓）：
  農夫種出穀物🌾 → 磨坊主磨成麵粉🌫️ → 麵包師烤成麵包🍞（吃了 +35 飽足）
  牧羊人養羊🐑 → 屠夫宰殺出生肉🥩（吃了 +40 飽足，但要先煮）→ 自家灶台煮成熟肉🍖（+55 飽足）
  酒保用穀物釀啤酒🍺（+2 飽足，主要解社交）

器具產業鏈（不能吃）：
  礦工挖鐵礦🪨 → 鐵匠煉成鐵錠🔩 → 木匠做家具🪑
  伐木工砍木材🪵 → 木匠做家具🪑

服飾產業鏈（不能吃）：
  牧羊人剪羊毛☁️ → 織工織成布料🧵
  屠夫剝下羊皮🟫 → 皮革匠鞣成皮革🟤
  布料 + 皮革 → 裁縫做衣服👕

【吃飽的唯一方法】
飢餓時只有三個動作能解餓：
- eat：背包有麵包或熟肉時才可用
- go_buy_food：去找麵包師買麵包（$3），或去找屠夫買生肉（$5）
- go_cook：背包有生肉且家裡有灶台時，回家煮成熟肉

【絕對不能誤會的事】
- 穀物🌾、麵粉🌫️、鐵礦🪨、木材🪵、羊毛☁️、羊皮🟫、布料🧵、皮革🟤、鐵錠🔩 全部都是【原料/半成品】，吃了不會飽，撿了也不會解餓
- go_work（工作賺錢）、go_pickup（撿原料）、go_sell（賣東西）這些動作都【不會解餓】，餓了就要選 eat / go_buy_food / go_cook
- 即使你是農夫，種出來的穀物也【不能拿來吃】，那是要賣給磨坊主的銷售商品
- 「飽足危急」時請優先選 eat / go_buy_food / go_cook，不要去撿穀物或工作

根據你的狀態、優先級和性格，呼叫 choose_action 選擇行動。"""
    
    def _build_destination_prompt(self, villager: dict, game_state, action_info: dict = None) -> str:
        time_info = game_state.get_time()
        stats = villager["stats"]
        
        satiety = stats.get('satiety', 100)
        energy = stats.get('energy', 100)
        social = stats.get('social', 100)
        money = villager.get('money', 0)
        
        occupation_name = self._get_occupation_name(villager.get('occupation', ''))
        traits = villager.get("personality", [])
        traits_text = "、".join(traits) if traits else "普通"
        destinations = self._build_destination_list(villager, game_state, action_info)
        weather_info = game_state.get_weather_info()
        weather_text = f"{weather_info['icon']} {weather_info['name']}"
        memories_text = format_memories(villager.get('memories', []), limit=3)
        action_history_text = self._format_action_history(villager)
        
        # 背包物品
        inventory_text = self._format_inventory(villager)
        
        # 地上物品（自己的）
        ground_text = self._format_ground_items(villager, game_state)
        
        # 周圍的人（如果有）
        nearby_text = ""
        if action_info and action_info.get("context"):
            nearby = action_info["context"].get("nearby_villagers", [])
            if nearby:
                nearby_text = self._format_nearby_villagers(nearby, villager)
        
        # 構建提示詞
        prompt = f"""【{villager['name']}】{occupation_name}，性格：{traits_text}

【狀態】
- 飽足：{self._get_status_tag(satiety)}
- 體力：{self._get_status_tag(energy)}
- 社交：{self._get_status_tag(social)}
- 金錢：${money}

【背包】{inventory_text}
【地上】{ground_text}
"""
        
        # 如果周圍有人，加入周圍的人資訊
        if nearby_text:
            prompt += f"""
【周圍的人】
{nearby_text}
"""
        
        prompt += f"""
【可用行動】
{destinations}

【時間】第 {time_info['day']} 天 {time_info['hour']:02d}:{time_info['minute']:02d}
【天氣】{weather_text}
【最近】{memories_text}
【前幾次行為】{action_history_text}

你要做什麼？"""
        
        return prompt
    
    def _build_destination_list(self, villager: dict, game_state, action_info: dict = None) -> str:
        """建構可用行動列表（統一決策系統）- 根據 action_info["actions"] 決定顯示"""
        import random
        actions = []
        available = action_info["actions"] if action_info else []
        
        # 1. go_work
        if "go_work" in available:
            work_desc = self._get_work_description(villager)
            actions.append(f"- go_work：{work_desc}")
        
        # 2. go_sell
        if "go_sell" in available:
            sell_info = self._get_sell_info(villager, game_state) or "賣東西給商人"
            actions.append(f"- go_sell：{sell_info}")
        
        # 3. go_buy_food
        if "go_buy_food" in available:
            food_info = self._get_buy_food_info(villager, game_state) or "去買食物"
            actions.append(f"- go_buy_food：{food_info}")
        
        # 4. eat
        if "eat" in available:
            eat_info = self._get_eat_info(villager) or "吃食物"
            actions.append(f"- eat：{eat_info}")
        
        # 4.5. go_cook
        if "go_cook" in available:
            cook_info = self._get_cook_info(villager, game_state) or "回家煮生肉"
            actions.append(f"- go_cook：{cook_info}")
        
        # 5. go_pickup
        if "go_pickup" in available:
            pickup_info = self._get_pickup_info(villager, game_state) or "撿地上的物品"
            actions.append(f"- go_pickup：{pickup_info}")
        
        # 6. go_buy_material
        if "go_buy_material" in available:
            material_info = self._get_buy_material_info(villager, game_state) or "去買材料"
            actions.append(f"- go_buy_material：{material_info}")
        
        # 7. go_buy_tool
        if "go_buy_tool" in available:
            tool_info = self._get_buy_tool_info(villager, game_state) or "去買工具"
            actions.append(f"- go_buy_tool：{tool_info}")
        
        # 7.5. go_buy_goods（商人專用）
        if "go_buy_goods" in available:
            buy_goods_info = self._get_buy_goods_info(villager, game_state) or "去收購物品"
            actions.append(f"- go_buy_goods：{buy_goods_info}")
        
        # 8. go_sleep
        if "go_sleep" in available:
            actions.append("- go_sleep：回家睡覺 → 只恢復體力")
        
        # 9. go_plaza
        if "go_plaza" in available:
            actions.append("- go_plaza：去廣場找人聊天 → 只恢復社交")
        
        # 10. go_bar
        if "go_bar" in available:
            actions.append("- go_bar：去酒吧社交喝酒 → 只恢復社交（需 $100）")
        
        # 11. wander
        if "wander" in available:
            actions.append("- wander：隨意閒逛")
        
        # 12. talk
        if "talk" in available:
            actions.append("- talk：找人聊天（需指定 target: villager_id）")
        
        # 13. buy_beer
        if "buy_beer" in available:
            actions.append("- buy_beer：跟酒保買杯啤酒喝（需 $3）")
        
        # 14. idle
        if "idle" in available:
            actions.append("- idle：什麼都不做，在這裡待著")
        
        # 隨機排序，避免總是選第一個
        random.shuffle(actions)
        
        return "\n".join(actions)
    
    def _format_inventory(self, villager: dict) -> str:
        inventory = villager.get("inventory", [])
        items = []
        for slot in inventory:
            if slot:
                item_id = slot.get("item_id")
                qty = slot.get("quantity", 1)
                items.append(f"{item_id} x{qty}")
        return "、".join(items) if items else "空"
    
    def _format_ground_items(self, villager: dict, game_state) -> str:
        """格式化地上物品（自己擁有的），相同物品合併顯示"""
        owned_items = game_state.get_items_by_owner(villager["id"])
        if not owned_items:
            return "無"
        
        # 合併相同物品的數量
        totals = {}
        for item in owned_items:
            item_id = item.get("item_id")
            qty = item.get("quantity", 1)
            totals[item_id] = totals.get(item_id, 0) + qty
        
        items = [f"{item_id} x{qty}" for item_id, qty in totals.items()]
        return "、".join(items) if items else "無"
    
    def _format_action_history(self, villager: dict) -> str:
        """格式化行為歷史"""
        history = villager.get("action_history", [])
        if not history:
            return "無"
        
        lines = []
        for record in history:
            action = record.get("action", "unknown")
            result = record.get("result", "unknown")
            detail = record.get("detail", "")
            icon = "✅" if result == "success" else "❌"
            if detail:
                lines.append(f"{action} → {icon} {detail}")
            else:
                lines.append(f"{action} → {icon}")
        
        return "; ".join(lines)
    
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
        lines = []
        
        for opt in trade_options.get("can_buy", [])[:3]:
            lines.append(f"- 向 {opt['from_name']} 購買 {opt['item']} ${opt['price']}")
        
        for opt in trade_options.get("can_sell", [])[:3]:
            lines.append(f"- 賣 {opt['item']} 給 {opt['to_name']} ${opt['price']}")
        
        return "\n".join(lines)
    
    def _has_food_in_inventory(self, villager: dict) -> bool:
        from ..data.item_categories import FOODS
        inventory = villager.get("inventory", [])
        for slot in inventory:
            item_id = slot.get("item_id") if slot else None
            # 生肉需要煮，不能直接吃
            if item_id and item_id in FOODS and item_id != "meat_raw":
                return True
        return False

    def _get_mood_desc(self, villager: dict) -> str:
        """取得心情文字描述（給對話 prompt 使用）"""
        stats = villager.get("stats", {})
        moods = []
        if stats.get("energy", 100) < 30:
            moods.append("很累")
        if stats.get("satiety", 100) < 30:
            moods.append("很餓")
        if stats.get("social", 50) < 20:
            moods.append("寂寞")
        if stats.get("happiness", 50) > 70:
            moods.append("開心")
        return "、".join(moods) if moods else "普通"

    def _get_village_sellers_text(self, game_state) -> str:
        """列出本村各職業的村民名字（給對話 prompt 使用）"""
        by_occupation: Dict[str, List[str]] = {}
        for v in game_state.villagers.values():
            occ = v.get("occupation")
            if occ:
                by_occupation.setdefault(occ, []).append(v.get("name", "?"))
        # 按食物優先排序，列出對話常用的職業
        order = [
            ("baker", "麵包師（賣麵包 $3）"),
            ("butcher", "屠夫（賣生肉 $5）"),
            ("bartender", "酒保（賣啤酒）"),
            ("blacksmith", "鐵匠（賣工具）"),
            ("miller", "磨坊主"),
            ("farmer", "農夫"),
            ("shepherd", "牧羊人"),
            ("merchant", "商人"),
        ]
        lines = []
        for occ, label in order:
            names = by_occupation.get(occ)
            if names:
                lines.append(f"- {label}：{', '.join(names)}")
        return "\n".join(lines) if lines else "（無）"
    
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
                max_completion_tokens=400
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
                max_completion_tokens=400,
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
        """檢查牧羊人是否能工作（有需要照顧的羊或有可剪毛的羊）"""
        owned_sheep = game_state.get_sheep_by_owner(villager["id"])
        
        # 1. 檢查是否有需要照顧的羊
        needs_care_sheep = [s for s in owned_sheep if s.get("needs_care")]
        if needs_care_sheep:
            logger.info(f"🔍 _can_work: {villager['name']}(shepherd) 有 {len(needs_care_sheep)} 隻需要照顧的羊")
            return True
        
        # 2. 檢查是否有可剪毛的成羊
        shearable_sheep = [
            s for s in owned_sheep 
            if s.get("is_adult") and s.get("wool_ready", False)
        ]
        if shearable_sheep:
            logger.info(f"🔍 _can_work: {villager['name']}(shepherd) 有 {len(shearable_sheep)} 隻可剪毛的羊")
            return True
        
        logger.info(f"🔍 _can_work: {villager['name']}(shepherd) 沒有需要照顧或可剪毛的羊")
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

        mood_a = self._get_mood_desc(villager_a)
        mood_b = self._get_mood_desc(villager_b)
        inv_a = self._format_inventory(villager_a)
        inv_b = self._format_inventory(villager_b)
        sellers = self._get_village_sellers_text(game_state)

        return f"""兩個村民相遇:

村民 A:
- 姓名: {villager_a['name']}
- 職業: {self._get_occupation_name(villager_a['occupation'])}
- 性格: {', '.join(villager_a['personality'])}
- 心情: {mood_a}
- 背包: {inv_a}
- 金錢: ${villager_a.get('money', 0)}
- 對 B 的好感: {aff_a}（{self._get_affection_desc(aff_a)}）
- 對 B 的熟悉度: {fam_a}（{self._get_familiarity_desc(fam_a)}）

村民 B:
- 姓名: {villager_b['name']}
- 職業: {self._get_occupation_name(villager_b['occupation'])}
- 性格: {', '.join(villager_b['personality'])}
- 心情: {mood_b}
- 背包: {inv_b}
- 金錢: ${villager_b.get('money', 0)}
- 對 A 的好感: {aff_b}（{self._get_affection_desc(aff_b)}）
- 對 A 的熟悉度: {fam_b}（{self._get_familiarity_desc(fam_b)}）

【村莊資訊】
{sellers}

請模擬他們的相遇互動。對話要符合他們此刻的狀態（餓了會抱怨肚子，缺工具會煩惱）。
注意：穀物、麵粉、鐵礦等原料不可吃，餓了要找麵包師買麵包或屠夫買生肉。"""

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
        
        # 產出描述（列出所有產品）
        product_desc = ""
        if products:
            product_names = []
            for prod in products:
                item_type = ITEM_TYPES.get(prod)
                product_names.append(item_type.name if item_type else prod)
            product_desc = f"生產{'、'.join(product_names)}"
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
                return f"去買{food_name}吃 → 只恢復飽足度（需 ${price}）"
        return ""
    
    def _get_eat_info(self, villager: dict) -> str:
        """取得背包食物資訊"""
        from ..data.items import ITEM_TYPES
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") in ("bread", "meat"):
                item_type = ITEM_TYPES.get(slot.get("item_id"))
                name = item_type.name if item_type else slot.get("item_id")
                return f"吃{name} → 只恢復飽足度"
        return ""
    
    def _get_cook_info(self, villager: dict, game_state) -> str:
        """取得可煮食物資訊（背包有生肉且有灶台）"""
        has_stove = game_state.get_stove_by_residence(villager["id"]) is not None
        if not has_stove:
            return ""
        
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot and slot.get("item_id") == "meat_raw":
                return "回家煮生肉 → 只恢復飽足度"
        return ""
    
    def _get_pickup_info(self, villager: dict, game_state) -> str:
        """取得可撿地上物品資訊"""
        from ..data.items import ITEM_TYPES
        from ..data.item_categories import FOODS, TOOLS, RAW_MATERIALS
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

        # 產生描述（含類別標註，避免 AI 把原料當食物）
        item_names = []
        item_ids = []
        for item_id, qty in item_counts.items():
            item_type = ITEM_TYPES.get(item_id)
            name = item_type.name if item_type else item_id
            if item_id in FOODS:
                tag = "食物"
            elif item_id in TOOLS:
                tag = "工具"
            elif item_id in RAW_MATERIALS:
                tag = "原料,不可食"
            else:
                tag = ""
            tag_str = f"({tag})" if tag else ""
            item_names.append(f"{name}{tag_str} x{qty}")
            item_ids.append(item_id)

        items_desc = "、".join(item_names)
        ids_desc = "/".join(item_ids)
        return f"撿地上的 {items_desc}（需指定 item: {ids_desc}）"
    
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
        from ..game.production import get_material_price

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
            price = get_material_price(material)
            if money < price:
                continue
            
            supplier_occupation = MATERIAL_PRODUCERS.get(material)
            if supplier_occupation and self._check_supplier_stock(game_state, supplier_occupation, material):
                from ..data.items import ITEM_TYPES
                item_type = ITEM_TYPES.get(material)
                name = item_type.name if item_type else material
                return f"去買{name}（工作材料，需 ${price}）"
        
        return ""
    
    def _get_buy_goods_targets(self, villager: dict, game_state) -> List[dict]:
        """取得可收購物品的村民列表（商人專用）"""
        # 只有商人可以收購
        if villager.get("occupation") != "merchant":
            return []
        
        money = villager.get("money", 0)
        if money < 10:
            return []
        
        # 找所有有可收購物品的村民
        purchasable = []
        for v in game_state.villagers.values():
            if v["id"] == villager["id"]:
                continue
            
            # 檢查該村民的背包和地上物品
            items_to_buy = self._get_villager_purchasable_items(v, game_state)
            if items_to_buy:
                purchasable.append({
                    "villager_id": v["id"],
                    "villager_name": v["name"],
                    "items": items_to_buy
                })
        
        return purchasable
    
    def _get_buy_goods_info(self, villager: dict, game_state) -> str:
        """取得可收購物品資訊描述（商人專用）"""
        from ..data.items import ITEM_TYPES
        
        purchasable = self._get_buy_goods_targets(villager, game_state)
        if not purchasable:
            return ""
        
        # 生成描述（列出可收購的村民，格式：人名(ID)）
        desc_parts = []
        for p in purchasable[:3]:
            desc_parts.append(f"{p['villager_name']}({p['villager_id']})")
        
        return f"去收購物品賺錢（需指定 buy_target: {'; '.join(desc_parts)}）"
    
    def _get_villager_purchasable_items(self, villager: dict, game_state) -> List[tuple]:
        """取得某村民可被商人收購的物品列表"""
        from ..data.supply_chain import MERCHANT_BUY_PRICES, EXCESS_THRESHOLDS
        from ..data.item_categories import TOOLS
        
        money = villager.get("money", 0)
        stats = villager.get("stats", {})
        satiety = stats.get("satiety", 100)
        is_broke_and_hungry = money < 12 and satiety < 50
        
        # 統計所有物品（背包 + 地上）
        item_counts = {}
        
        # 背包物品
        inventory = villager.get("inventory", [])
        for slot in inventory:
            if slot:
                item_id = slot.get("item_id")
                if item_id and item_id not in TOOLS:
                    qty = slot.get("quantity", 1)
                    item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        # 地上物品
        ground_items = game_state.get_items_by_owner(villager["id"])
        for item in ground_items:
            item_id = item.get("item_id")
            if item_id and item_id not in TOOLS:
                qty = item.get("quantity", 1)
                item_counts[item_id] = item_counts.get(item_id, 0) + qty
        
        # 找出過剩或缺錢可賣的物品
        result = []
        for item_id, qty in item_counts.items():
            if item_id not in MERCHANT_BUY_PRICES:
                continue
            threshold = EXCESS_THRESHOLDS.get(item_id, 10)
            if qty >= threshold or (is_broke_and_hungry and qty >= 1):
                result.append((item_id, qty))
        
        return result
