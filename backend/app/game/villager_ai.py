"""
村民 AI 系統 - GPT 整合
"""

import os
import json
import logging
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
        
        if not self.client:
            logger.warning("⚠️ OpenAI API Key 未設定，使用規則系統")
        else:
            logger.info(f"✅ OpenAI 已初始化，模型: {self.model}")
    
    async def make_decision(self, villager: dict, game_state) -> dict:
        """為村民做出行為決策"""
        
        # 如果沒有 API Key，使用規則系統
        if not self.client:
            return self._rule_based_decision(villager, game_state)
        
        try:
            # 建構提示詞
            prompt = self._build_decision_prompt(villager, game_state)
            system_prompt = self._get_system_prompt()
            
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
    
    def _get_system_prompt(self) -> str:
        return """你是一個中古世紀村莊模擬遊戲的 AI 系統。
你需要根據村民的性格、狀態和環境，決定他們的下一步行為。

【重要】需求優先順序（由高到低）：
1. 飽足度 < 30% → 必須去酒館吃東西 (go_tavern)
2. 體力 < 30% → 必須回家休息 (go_home) 或睡覺 (sleep)
3. 其他需求可以根據性格和時間自由選擇

可用的行為類型：
- go_tavern: 去酒館（吃東西、喝酒）← 餓了要來這裡！
- go_home: 回家休息
- go_work: 去工作地點工作
- go_church: 去教堂祈禱
- go_market: 去市集逛逛（社交）
- sleep: 睡覺（晚上）
- wander: 隨意閒逛

回應必須是 JSON 格式:
{
  "action": "行為類型",
  "reason": "簡短的理由（村民心中所想，用繁體中文，10字以內）",
  "mood": "當前心情"
}

注意：不需要提供座標，系統會自動處理移動。
保持角色性格一致，做出合理的決策。"""

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
        
        # 很餓
        if stats["hunger"] > 70:
            return {"action": "eat", "target": None, "reason": "肚子餓了", "mood": "hungry"}
        
        # 工作時間
        if 8 <= hour < 12 or 14 <= hour < 18:
            if villager["occupation"] != "house":
                return {"action": "go_work", "target": None, "reason": "該工作了", "mood": "neutral"}
        
        # 社交需求 - 主動找人聊天
        if stats["social"] < 30:
            return {"action": "socialize", "target": None, "reason": "想找人聊聊", "mood": "lonely"}
        
        # 隨機閒逛
        actions = ["wander", "rest", "go_church", "go_market"]
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
