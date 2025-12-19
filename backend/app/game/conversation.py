"""
對話系統 - 管理村民對話、生成對話內容、記憶
"""

import asyncio
import time
import random
import json
import logging
import os
from typing import Dict, List, Optional, TYPE_CHECKING
from .villager_ai import format_memories
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .game_state import GameState

logger = logging.getLogger("Conversation")


@dataclass
class Conversation:
    """進行中的對話"""
    id: str
    villager_a: dict
    villager_b: dict
    history: List[Dict] = field(default_factory=list)
    current_speaker: str = "a"
    started_at: float = 0
    last_message_at: float = 0
    waiting_for_response: bool = False
    max_turns: int = 6
    
    def get_turn_count(self) -> int:
        return len(self.history)
    
    def is_finished(self) -> bool:
        return self.get_turn_count() >= self.max_turns
    
    def add_message(self, speaker: str, text: str, end: bool = False):
        self.history.append({"speaker": speaker, "text": text, "end": end})
        self.current_speaker = "b" if speaker == "a" else "a"
        self.last_message_at = time.time()
    
    def get_history_text(self) -> str:
        """取得對話歷史文字"""
        lines = []
        for msg in self.history[-10:]:
            name = self.villager_a["name"] if msg["speaker"] == "a" else self.villager_b["name"]
            lines.append(f"{name}: {msg['text']}")
        return "\n".join(lines)


class ConversationSystem:
    """對話系統管理器"""
    
    def __init__(self, game_state: "GameState", villager_ai, connection_manager):
        self.game_state = game_state
        self.villager_ai = villager_ai
        self.manager = connection_manager
        
        self.active_conversations: Dict[str, Conversation] = {}
        self.conversation_id_counter = 0
        self.conversation_processing = False
    
    def check_social_encounters(self) -> list:
        """檢查村民相遇"""
        encounters = []
        villagers = list(self.game_state.villagers.values())
        
        for i, a in enumerate(villagers):
            for b in villagers[i+1:]:
                if a.get("state") not in ["idle", "walking"]:
                    continue
                if b.get("state") not in ["idle", "walking"]:
                    continue
                
                dx = a["x"] - b["x"]
                dy = a["y"] - b["y"]
                dist = (dx**2 + dy**2) ** 0.5
                
                # 在市集或酒吧範圍內，距離放寬為 3 格
                in_social_building = self._is_in_social_building(a["x"], a["y"])
                encounter_distance = 3.0 if in_social_building else 1.5
                
                if dist < encounter_distance:
                    encounters.append((a, b, in_social_building))
        
        return encounters
    
    def _is_in_social_building(self, x: float, y: float) -> bool:
        """檢查座標是否在市集或酒吧範圍內"""
        social_building_types = ["market", "tavern"]
        
        for building in self.game_state.map_data.get("buildings", []):
            if building["type"] not in social_building_types:
                continue
            
            bx, by = building["x"], building["y"]
            bw, bh = building.get("width", 3), building.get("height", 3)
            
            # 檢查是否在建築範圍內（包含門口周圍 1 格）
            if bx - 1 <= x <= bx + bw and by - 1 <= y <= by + bh:
                return True
        
        return False
    
    async def handle_encounter(self, encounter: tuple, ai_semaphore: asyncio.Semaphore):
        """處理村民相遇事件 - 開始新對話"""
        villager_a, villager_b, in_social_building = encounter
        
        # 檢查是否已在對話中
        for conv in self.active_conversations.values():
            if (conv.villager_a["id"] in [villager_a["id"], villager_b["id"]] or
                conv.villager_b["id"] in [villager_a["id"], villager_b["id"]]):
                return
        
        # 檢查冷卻時間
        last_chat_a = villager_a.get("last_chat_time", 0)
        last_chat_b = villager_b.get("last_chat_time", 0)
        current_time = time.time()
        
        if current_time - last_chat_a < 60 or current_time - last_chat_b < 60:
            return
        
        # 計算聊天觸發機率（基礎 30%，市集/酒吧內 × 2）
        chat_chance = 0.6 if in_social_building else 0.3
        personality_a = villager_a.get("personality", [])
        personality_b = villager_b.get("personality", [])
        
        # extrovert/introvert 影響聊天機率
        if "extrovert" in personality_a or "extrovert" in personality_b:
            chat_chance *= 2.0  # 外向者更容易觸發聊天
        if "introvert" in personality_a and "introvert" in personality_b:
            chat_chance *= 0.25  # 兩個內向者很難觸發
        elif "introvert" in personality_a or "introvert" in personality_b:
            chat_chance *= 0.5  # 一個內向者降低機率
        
        # brave/timid 對陌生人（熟悉度<30）的影響
        rel_a = villager_a.get("relationships", {}).get(villager_b["id"], {})
        rel_b = villager_b.get("relationships", {}).get(villager_a["id"], {})
        familiarity = max(rel_a.get("familiarity", 0), rel_b.get("familiarity", 0))
        
        if familiarity < 30:  # 陌生人
            if "brave" in personality_a or "brave" in personality_b:
                chat_chance *= 2.0
            if "timid" in personality_a and "timid" in personality_b:
                chat_chance *= 0.09  # 0.3 * 0.3
            elif "timid" in personality_a or "timid" in personality_b:
                chat_chance *= 0.3
        
        chat_chance = min(0.9, chat_chance)  # 上限 90%
        
        if random.random() > chat_chance:
            return
        
        # 建立新對話
        self.conversation_id_counter += 1
        conv_id = f"conv_{self.conversation_id_counter}"
        
        conversation = Conversation(
            id=conv_id,
            villager_a=villager_a,
            villager_b=villager_b,
            started_at=current_time,
            last_message_at=current_time
        )
        
        self.active_conversations[conv_id] = conversation
        
        villager_a["last_chat_time"] = current_time
        villager_b["last_chat_time"] = current_time
        villager_a["state"] = "talking"
        villager_b["state"] = "talking"
        
        # 生成第一句話
        first_message = await self.generate_message(conversation, "a", ai_semaphore)
        
        if first_message:
            conversation.add_message("a", first_message["text"], first_message.get("end", False))
            await self.broadcast_chat_message(conversation, "a", first_message["text"])
            logger.info(f"💬 對話開始: {villager_a['name']} 對 {villager_b['name']} 說：{first_message['text'][:30]}...")
    
    async def start_direct_conversation(self, villager_a: dict, villager_b: dict, ai_semaphore: asyncio.Semaphore):
        """直接發起對話（主動社交，100% 觸發）"""
        for conv in self.active_conversations.values():
            if (conv.villager_a["id"] in [villager_a["id"], villager_b["id"]] or
                conv.villager_b["id"] in [villager_a["id"], villager_b["id"]]):
                return
        
        current_time = time.time()
        
        self.conversation_id_counter += 1
        conv_id = f"conv_{self.conversation_id_counter}"
        
        conversation = Conversation(
            id=conv_id,
            villager_a=villager_a,
            villager_b=villager_b,
            started_at=current_time,
            last_message_at=current_time
        )
        
        self.active_conversations[conv_id] = conversation
        
        villager_a["last_chat_time"] = current_time
        villager_b["last_chat_time"] = current_time
        villager_a["state"] = "talking"
        villager_b["state"] = "talking"
        
        first_message = await self.generate_message(conversation, "a", ai_semaphore)
        
        if first_message:
            conversation.add_message("a", first_message["text"], first_message.get("end", False))
            await self.broadcast_chat_message(conversation, "a", first_message["text"])
            logger.info(f"💬 主動對話開始: {villager_a['name']} 對 {villager_b['name']} 說：{first_message['text'][:30]}...")
    
    async def process_conversations(self, ai_semaphore: asyncio.Semaphore):
        """處理所有進行中的對話"""
        if self.conversation_processing:
            return
        self.conversation_processing = True
        
        try:
            finished_conversations = []
            tasks_to_process = []
            
            for conv_id, conv in list(self.active_conversations.items()):
                if time.time() - conv.last_message_at > 30:
                    finished_conversations.append(conv_id)
                    continue
                
                if conv.is_finished():
                    finished_conversations.append(conv_id)
                    continue
                
                if conv.history and conv.history[-1].get("end", False):
                    finished_conversations.append(conv_id)
                    continue
                
                if conv.waiting_for_response:
                    continue
                
                tasks_to_process.append((conv_id, conv))
            
            async def process_single_conversation(conv_id, conv):
                conv.waiting_for_response = True
                try:
                    response = await self.generate_message(conv, conv.current_speaker, ai_semaphore)
                    
                    if response:
                        conv.add_message(conv.current_speaker, response["text"], response.get("end", False))
                        speaker = conv.villager_a if conv.history[-1]["speaker"] == "a" else conv.villager_b
                        await self.broadcast_chat_message(conv, conv.history[-1]["speaker"], response["text"])
                        logger.info(f"💬 {speaker['name']}: {response['text'][:30]}...")
                except Exception as e:
                    logger.error(f"❌ 對話處理失敗: {e}")
                finally:
                    conv.waiting_for_response = False
            
            if tasks_to_process:
                await asyncio.gather(*[process_single_conversation(cid, c) for cid, c in tasks_to_process])
            
            for conv_id in finished_conversations:
                await self.finish_conversation(conv_id, ai_semaphore)
        finally:
            self.conversation_processing = False
    
    async def generate_message(self, conv: Conversation, speaker: str, ai_semaphore: asyncio.Semaphore) -> Optional[dict]:
        """用 AI 生成對話回應"""
        villager = conv.villager_a if speaker == "a" else conv.villager_b
        other = conv.villager_b if speaker == "a" else conv.villager_a
        
        rel = villager.get("relationships", {}).get(other["id"], {})
        familiarity = rel.get("familiarity", 0)
        affection = rel.get("affection", 0)
        
        memories = villager.get("memories", [])
        memories_text = format_memories(memories, target_name=other["name"], limit=5, style="simple")
        other_memories_text = format_memories(memories, exclude_name=other["name"], limit=5, style="detailed")
        
        history_text = conv.get_history_text() or "（對話剛開始）"
        turn_count = conv.get_turn_count()
        
        game_time = self.game_state.get_time()
        weather_info = self.game_state.get_weather_info()
        weather_text = f"{weather_info['icon']} {weather_info['name']}"
        my_stats = villager.get("stats", {})
        
        def get_mood(stats):
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
        
        my_mood = get_mood(my_stats)
        
        from .game_state import get_affection_desc, get_familiarity_desc
        affection_text = f"{affection}（{get_affection_desc(affection)}）"
        familiarity_text = f"{familiarity}（{get_familiarity_desc(familiarity)}）"
        
        my_prefs = villager.get("preferences", {})
        other_prefs = other.get("preferences", {})
        
        # 根據熟悉度決定知道對方多少資訊
        other_info_lines = []
        if familiarity >= 1:
            other_info_lines.append(f"- 名字：{other['name']}")
        else:
            other_info_lines.append("- 名字：（不認識的人）")
        if familiarity >= 10:
            other_info_lines.append(f"- 職業：{other.get('occupation', '村民')}")
        if familiarity >= 20:
            other_info_lines.append(f"- 興趣：{', '.join(other_prefs.get('hobbies', ['不知道']))}")
        if familiarity >= 30:
            other_info_lines.append(f"- 喜歡的食物：{', '.join(other_prefs.get('favorite_foods', ['不知道']))}")
        if familiarity >= 40:
            other_info_lines.append(f"- 性格：{', '.join(other.get('personality', ['普通']))}")
            other_info_lines.append(f"- 討厭的事：{', '.join(other_prefs.get('dislikes', ['不知道']))}")
        other_info_text = "\n".join(other_info_lines)
        
        # 對方名稱（陌生人用「這個人」）
        other_name = other['name'] if familiarity >= 1 else "這個人"
        
        prompt = f"""你是中古世紀村莊的村民「{villager['name']}」，正在和「{other_name}」聊天。
根據你的性格、背景、記憶來聊天，保持對話自然、簡短；可以利用對方記憶、個人訊息、他人記憶等等所有資訊來當聊天內容。

【你的資訊】
- 年齡：{villager.get('age', 25)} 歲
- 職業：{villager.get('occupation', '村民')}
- 性格：{', '.join(villager.get('personality', ['普通']))}
- 興趣：{', '.join(my_prefs.get('hobbies', ['無']))}
- 目前心情：{my_mood}

【對方資訊】
{other_info_text}

【你們的關係】
- 熟悉度：{familiarity_text}
- 好感度：{affection_text}

【你對 {other_name} 的記憶】
{memories_text}

【你對其他人的記憶】
{other_memories_text}

【現在時間】第 {game_time['day']} 天 {game_time['hour']:02d}:{game_time['minute']:02d}
【天氣】{weather_text}

【目前對話】（第 {turn_count + 1} 輪，最多 6 輪）
{history_text}

請根據你的性格回應。只說一句話（20字以內）。
如果已經聊了3輪以上，可以說再見結束對話。

回傳 JSON：{{"text": "你要說的話", "end": false}}
結束對話時 end 設為 true。"""

        try:
            async with ai_semaphore:
                response = await self.villager_ai.client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.8
                )
            
            content = response.choices[0].message.content.strip()
            
            if "{" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                result = json.loads(json_str)
                return result
            else:
                return {"text": content[:50], "end": False}
                
        except Exception as e:
            logger.error(f"生成對話失敗: {e}")
            return {"text": "嗯...", "end": True}
    
    async def finish_conversation(self, conv_id: str, ai_semaphore: asyncio.Semaphore):
        """結束對話，生成總結並存入記憶"""
        if conv_id not in self.active_conversations:
            return
        
        conv = self.active_conversations[conv_id]
        villager_a = conv.villager_a
        villager_b = conv.villager_b
        
        if villager_a.get("state") == "talking":
            villager_a["state"] = "idle"
        if villager_b.get("state") == "talking":
            villager_b["state"] = "idle"
        
        # 增加社交值
        villager_a.get("stats", {})["social"] = min(100, villager_a.get("stats", {}).get("social", 50) + 45)
        villager_b.get("stats", {})["social"] = min(100, villager_b.get("stats", {}).get("social", 50) + 45)
        logger.info(f"💬 {villager_a['name']} 和 {villager_b['name']} 社交值 +45")
        
        # 生成總結並存入記憶，同時判斷好感變化
        if len(conv.history) >= 2:
            result = await self.generate_summary(conv, ai_semaphore)
            if result:
                summary = result.get("summary", "")
                base_affection = result.get("affection_change", 1)
                
                self.add_memory(villager_a, villager_b["name"], summary)
                self.add_memory(villager_b, villager_a["name"], summary)
                
                # 計算性格對好感度的影響
                personality_a = villager_a.get("personality", [])
                personality_b = villager_b.get("personality", [])
                
                # 計算 A 對 B 的好感變化
                affection_a_to_b = self._calc_affection_change(
                    base_affection, personality_a, villager_a, villager_b
                )
                # 計算 B 對 A 的好感變化
                affection_b_to_a = self._calc_affection_change(
                    base_affection, personality_b, villager_b, villager_a
                )
                
                # 計算熟悉度變化（trust 影響）
                familiarity_a = self._calc_familiarity_change(2, personality_a)
                familiarity_b = self._calc_familiarity_change(2, personality_b)
                
                # 根據對話內容更新好感度
                self.game_state.update_relationship(villager_a["id"], villager_b["id"], {"familiarity": familiarity_a, "affection": affection_a_to_b})
                self.game_state.update_relationship(villager_b["id"], villager_a["id"], {"familiarity": familiarity_b, "affection": affection_b_to_a})
                logger.info(f"💕 {villager_a['name']} 和 {villager_b['name']} 好感度 {'+' if affection_a_to_b >= 0 else ''}{affection_a_to_b}")
                
                # 好感度變化影響心情（每點好感 = ±5 心情）
                stats_a = villager_a.get("stats", {})
                stats_a["happiness"] = max(0, min(100, stats_a.get("happiness", 70) + affection_a_to_b * 5))
                stats_b = villager_b.get("stats", {})
                stats_b["happiness"] = max(0, min(100, stats_b.get("happiness", 70) + affection_b_to_a * 5))
        else:
            # 對話太短，只更新熟悉度
            personality_a = villager_a.get("personality", [])
            personality_b = villager_b.get("personality", [])
            familiarity_a = self._calc_familiarity_change(1, personality_a)
            familiarity_b = self._calc_familiarity_change(1, personality_b)
            self.game_state.update_relationship(villager_a["id"], villager_b["id"], {"familiarity": familiarity_a})
            self.game_state.update_relationship(villager_b["id"], villager_a["id"], {"familiarity": familiarity_b})
        
        # 廣播對話結束
        await self.manager.broadcast({
            "type": "conversation_end",
            "data": {
                "conversation_id": conv_id,
                "villager_a_id": villager_a["id"],
                "villager_b_id": villager_b["id"]
            }
        })
        
        logger.info(f"💬 對話結束: {villager_a['name']} 和 {villager_b['name']}")
        del self.active_conversations[conv_id]
    
    async def generate_summary(self, conv: Conversation, ai_semaphore: asyncio.Semaphore) -> Optional[dict]:
        """生成對話總結與好感變化判斷"""
        history_text = conv.get_history_text()
        
        prompt = f"""請分析以下對話，並回傳 JSON：

{history_text}

請判斷：
1. 用一句話總結對話內容、雙方情緒、獲得的資訊
2. 這次對話讓雙方好感度如何變化？（-3到+3之間的整數）
   - +3: 非常愉快、深入交流
   - +1~+2: 普通友好對話
   - 0: 中性、無特別感受
   - -1~-2: 有些不愉快、意見不合
   - -3: 吵架、嚴重衝突

回傳格式：{{"summary": "總結內容", "affection_change": 數字}}"""

        try:
            async with ai_semaphore:
                response = await self.villager_ai.client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600,
                    temperature=0.5
                )
            
            content = response.choices[0].message.content.strip()
            
            if "{" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                result = json.loads(json_str)
                result["summary"] = result.get("summary", "")[:150]
                result["affection_change"] = max(-3, min(3, result.get("affection_change", 1)))
                return result
            else:
                return {"summary": content[:50], "affection_change": 1}
            
        except Exception as e:
            logger.error(f"生成總結失敗: {e}")
            return None
    
    def add_memory(self, villager: dict, other_name: str, summary: str):
        """添加對話記憶（最多保留10條）"""
        if "memories" not in villager:
            villager["memories"] = []
        
        memory = {
            "type": "conversation",
            "with": other_name,
            "summary": summary,
            "day": self.game_state.game_time.day,
            "hour": self.game_state.game_time.hour
        }
        
        villager["memories"].append(memory)
        
        if len(villager["memories"]) > 10:
            villager["memories"] = villager["memories"][-10:]
    
    async def broadcast_chat_message(self, conv: Conversation, speaker: str, text: str):
        """廣播單條對話訊息"""
        villager = conv.villager_a if speaker == "a" else conv.villager_b
        target = conv.villager_b if speaker == "a" else conv.villager_a
        
        await self.manager.broadcast({
            "type": "villager_chat",
            "data": {
                "conversation_id": conv.id,
                "villager_id": villager["id"],
                "villager_name": villager["name"],
                "target_name": target["name"],
                "text": text,
                "turn": conv.get_turn_count()
            }
        })
    
    def _calc_affection_change(self, base: int, personality: list, me: dict, other: dict) -> int:
        """計算性格對好感度變化的影響"""
        result = float(base)
        
        # friendly/grumpy 影響好感度變化
        if "friendly" in personality:
            result += 2 if base > 0 else 1  # 友善者好感度提升更多
        elif "grumpy" in personality:
            result -= 1  # 暴躁者好感度提升較少
        
        # romantic/reserved 影響異性好感度
        my_gender = me.get("gender", "male")
        other_gender = other.get("gender", "male")
        if my_gender != other_gender:  # 異性
            if "romantic" in personality:
                result *= 1.5  # 浪漫者對異性好感度提升更多
            elif "reserved" in personality:
                result *= 0.7  # 矜持者對異性好感度提升較少
        
        return int(round(result))
    
    def _calc_familiarity_change(self, base: int, personality: list) -> int:
        """計算性格對熟悉度變化的影響"""
        result = float(base)
        
        # trusting/suspicious 影響熟悉度提升
        if "trusting" in personality:
            result *= 1.5  # 信任者熟悉度提升更快
        elif "suspicious" in personality:
            result *= 0.7  # 多疑者熟悉度提升較慢
        
        return int(round(result))
