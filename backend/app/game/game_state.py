"""
遊戲狀態管理
"""

import json
import random
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .pathfinding import PathFinding
from .map_generator import generate_map
from .target_resolver import TargetResolver


class GameState:
    def __init__(self):
        self.initialized = False
        self.seed = None
        
        # 時間系統
        self.day = 1
        self.hour = 8
        self.minute = 0
        self.time_scale = 60  # 1 現實秒 = 60 遊戲秒
        
        # 地圖資料
        self.map_data = None
        
        # 路徑尋找
        self.pathfinder: Optional[PathFinding] = None
        
        # 玩家
        self.player = None
        
        # 村民
        self.villagers: Dict[str, dict] = {}
        
        # 地上物品
        self.world_items: List[dict] = []
        self.next_item_id = 0
        
        # 羊群
        self.sheep: Dict[str, dict] = {}
        self.next_sheep_id = 0
        
        # 事件佇列
        self.events: List[dict] = []
        
        # 存檔路徑
        self.save_dir = Path("saves")
        self.save_dir.mkdir(exist_ok=True)
    
    def initialize(self, player_name: str = "玩家", seed: Optional[int] = None):
        """初始化新遊戲"""
        self.seed = seed or random.randint(0, 999999)
        random.seed(self.seed)
        
        # 生成地圖
        self.map_data = self._generate_map()
        
        # 初始化路徑尋找
        self.pathfinder = PathFinding(
            self.map_data["width"], 
            self.map_data["height"]
        )
        self.pathfinder.set_collision_map(self.map_data["collision"])
        
        # 建立玩家
        spawn = self._get_player_spawn()
        self.player = {
            "id": "player",
            "name": player_name,
            "x": spawn["x"],
            "y": spawn["y"],
            "stats": {
                "energy": 100,
                "hunger": 0,
                "social": 50,
                "happiness": 70,
                "health": 100,
                "money": 50
            },
            "relationships": {}
        }
        
        # 生成村民（13種職業各1人）
        self._generate_villagers(13)
        
        # 生成羊群（牧場初始 4 隻羊）
        self._generate_sheep()
        
        # 初始化目標解析器
        self.target_resolver = TargetResolver(self)
        
        self.initialized = True
        print(f"🎮 遊戲初始化完成 (種子: {self.seed})")
    
    def _generate_map(self) -> dict:
        """生成地圖"""
        return generate_map(self.seed)
    
    def _get_player_spawn(self) -> dict:
        """取得玩家出生點"""
        houses = [b for b in self.map_data["buildings"] if b["type"] == "house"]
        if houses:
            h = houses[0]
            return {"x": h["doorX"], "y": h["doorY"] + 1}
        return {"x": 32, "y": 32}
    
    def _generate_villagers(self, count: int):
        """生成村民"""
        names_male = ["艾德蒙", "約翰", "威廉", "亨利", "湯瑪斯", "羅伯特", "理查", "查爾斯",
                      "喬治", "愛德華", "法蘭克", "亞瑟", "雷蒙", "奧利佛", "賽乃斯", "馬可"]
        names_female = ["瑪莉", "伊莉莎白", "安娜", "凱薩琳", "艾瑪", "露西", "克萊兒", "蘇菲",
                        "夏洛特", "愛麗絲", "維多莉亞", "艾蓮娜", "羅莎", "貝蒂", "海倫", "伊芙"]
        
        personalities = {
            "positive": ["friendly", "hardworking", "generous", "optimistic", "curious"],
            "negative": ["greedy", "lazy", "suspicious", "grumpy", "gossip"],
            "neutral": ["introvert", "extrovert", "romantic", "religious"]
        }
        
        # 喜好池
        hobbies = [
            "閱讀", "釣魚", "園藝", "烹飪", "唱歌", "跳舞", "下棋", "繪畫",
            "狩獵", "釀酒", "縫紉", "木工", "講故事", "觀星", "收集石頭", "養寵物"
        ]
        
        # 喜歡的食物
        favorite_foods = [
            "烤肉", "麵包", "乳酪", "蘋果派", "燉菜", "烤魚", "蜂蜜蛋糕", "葡萄酒"
        ]
        
        # 討厭的事物
        dislikes = [
            "下雨天", "早起", "吵雜", "蟲子", "寒冷", "炎熱", "說謊的人", "懶惰的人"
        ]
        
        # 13種職業（對應工作建築）- 使用新的職業 ID
        occupations = [
            # 食物鏈
            "farmer",       # 農田 - 農夫
            "miller",       # 磨坊 - 磨坊主
            "butcher",      # 肉舖 - 屠夫
            "baker",        # 麵包店 - 麵包師
            # 器具鏈
            "miner",        # 礦場 - 礦工
            "lumberjack",   # 伐木場 - 伐木工
            "blacksmith",   # 鐵匠舖 - 鐵匠
            "carpenter",    # 木工坊 - 木匠
            # 服飾鏈
            "shepherd",     # 牧場 - 牧羊人
            "weaver",       # 織坊 - 織工
            "tanner",       # 皮革坊 - 皮革匠
            "tailor",       # 裁縫店 - 裁縫
            # 特殊
            "merchant",     # 市集 - 商人
        ]
        
        # 打亂名字順序，確保不重複
        random.shuffle(names_male)
        random.shuffle(names_female)
        used_names = set()
        male_index = 0
        female_index = 0
        
        for i in range(count):
            gender = random.choice(["male", "female"])
            
            # 從對應性別的名字池中取出不重複的名字
            if gender == "male":
                if male_index < len(names_male):
                    name = names_male[male_index]
                    male_index += 1
                else:
                    # 男性名字用完，改用女性
                    gender = "female"
                    name = names_female[female_index]
                    female_index += 1
            else:
                if female_index < len(names_female):
                    name = names_female[female_index]
                    female_index += 1
                else:
                    # 女性名字用完，改用男性
                    gender = "male"
                    name = names_male[male_index]
                    male_index += 1
            
            # 隨機性格
            traits = [random.choice(personalities["positive"])]
            if random.random() > 0.5:
                traits.append(random.choice(personalities["negative"]))
            if random.random() > 0.5:
                traits.append(random.choice(personalities["neutral"]))
            
            # 分配職業和工作地點
            occupation = occupations[i % len(occupations)]
            
            # 職業對應的建築類型
            occupation_to_building = {
                "farmer": "farm",
                "miller": "mill",
                "butcher": "butcher_shop",
                "baker": "bakery",
                "miner": "mine",
                "lumberjack": "lumber_camp",
                "blacksmith": "blacksmith",
                "carpenter": "carpentry",
                "shepherd": "pasture",
                "weaver": "weaver_shop",
                "tanner": "tannery",
                "tailor": "tailor_shop",
                "merchant": "market",
            }
            
            # 根據職業找對應的建築物作為工作地點
            building_type = occupation_to_building.get(occupation, occupation)
            workplace = None
            for b in self.map_data["buildings"]:
                if b["type"] == building_type:
                    workplace = b["id"]
                    break
            
            # 分配住所（輪流分配到各民宅）
            houses = [b for b in self.map_data["buildings"] if b["type"] == "house"]
            residence = houses[i % len(houses)]["id"] if houses else None
            
            # 出生在住所門口
            spawn = self.get_building_by_id(residence) if residence else self.map_data["buildings"][0]
            
            # 隨機選擇喜好（1-3個）
            num_hobbies = random.randint(1, 3)
            villager_hobbies = random.sample(hobbies, num_hobbies)
            
            # 隨機喜歡的食物（1-2個）
            villager_foods = random.sample(favorite_foods, random.randint(1, 2))
            
            # 隨機討厭的事物（1-2個）
            villager_dislikes = random.sample(dislikes, random.randint(1, 2))
            
            # 根據職業決定初始工具
            occupation_tools = {
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
            
            # 初始化背包（3格）
            inventory = [None, None, None]
            
            # 如果職業需要工具，給予初始工具
            required_tool = occupation_tools.get(occupation)
            if required_tool:
                # 工具資料結構
                tool_durability = {
                    "hoe": 100, "pickaxe": 80, "axe": 90, "shears": 120,
                    "cleaver": 100, "hammer": 100, "saw": 70, "scraper": 80
                }
                inventory[0] = {
                    "item_id": required_tool,
                    "quantity": 1,
                    "durability": tool_durability.get(required_tool, 100),
                    "owner_id": f"villager_{i}"
                }
            
            villager = {
                "id": f"villager_{i}",
                "name": name,
                "gender": gender,
                "age": random.randint(18, 60),
                "occupation": occupation,
                "workplace": workplace,
                "residence": residence,
                "personality": traits,
                "x": spawn["doorX"],
                "y": spawn["doorY"] + 1,
                "stats": {
                    "energy": random.randint(30, 100),  # 更隨機的體力
                    "hunger": random.randint(0, 60),    # 更隨機的飢餓
                    "social": random.randint(20, 80),   # 更隨機的社交
                    "happiness": random.randint(40, 90),
                    "health": random.randint(70, 100)
                },
                "preferences": {
                    "hobbies": villager_hobbies,        # 興趣愛好
                    "favorite_foods": villager_foods,   # 喜歡的食物
                    "dislikes": villager_dislikes       # 討厭的事物
                },
                "inventory": inventory,                 # 背包（3格）
                "money": random.randint(30, 80),        # 初始金錢
                "state": "idle",
                "memories": [],
                "relationships": {},
                "last_decision_time": 0,
                "task_queue": []  # 任務排程
            }
            
            self.villagers[villager["id"]] = villager
        
        # 生成村民後，建立初始關係
        self._generate_initial_relationships()
    
    def _generate_initial_relationships(self):
        """為村民建立初始關係（喜歡/討厭/暗戀等）"""
        villager_ids = list(self.villagers.keys())
        
        # 關係類型
        relationship_types = [
            {"type": "好友", "affection": (30, 60), "familiarity": (50, 80)},
            {"type": "討厭", "affection": (-50, -20), "familiarity": (20, 50)},
            {"type": "暗戀", "affection": (40, 80), "familiarity": (10, 40)},
            {"type": "競爭對手", "affection": (-30, 0), "familiarity": (40, 70)},
            {"type": "崇拜", "affection": (50, 90), "familiarity": (30, 60)},
            {"type": "普通認識", "affection": (-10, 20), "familiarity": (20, 40)},
        ]
        
        for villager_id in villager_ids:
            villager = self.villagers[villager_id]
            other_ids = [vid for vid in villager_ids if vid != villager_id]
            
            # 每個村民隨機對 2-4 個人有特殊關係
            num_relationships = random.randint(2, min(4, len(other_ids)))
            targets = random.sample(other_ids, num_relationships)
            
            for target_id in targets:
                target = self.villagers[target_id]
                
                # 隨機選擇關係類型
                rel_type = random.choice(relationship_types)
                
                affection = random.randint(rel_type["affection"][0], rel_type["affection"][1])
                familiarity = random.randint(rel_type["familiarity"][0], rel_type["familiarity"][1])
                
                villager["relationships"][target_id] = {
                    "affection": affection,
                    "familiarity": familiarity,
                    "type": rel_type["type"],
                    "tags": [rel_type["type"]]
                }
                
                # 記錄到日誌
                if rel_type["type"] in ["好友", "暗戀", "崇拜"]:
                    print(f"💕 {villager['name']} {rel_type['type']} {target['name']}")
                elif rel_type["type"] in ["討厭", "競爭對手"]:
                    print(f"💢 {villager['name']} {rel_type['type']} {target['name']}")
    
    def _generate_sheep(self):
        """生成羊群（每個牧場初始 4 隻羊）"""
        # 找到牧場
        pasture = self.get_building_by_type("pasture")
        if not pasture:
            print("⚠️ 找不到牧場，無法生成羊群")
            return
        
        # 找到牧羊人（羊的擁有者）
        shepherd = None
        for v in self.villagers.values():
            if v.get("occupation") == "shepherd":
                shepherd = v
                break
        
        owner_id = shepherd["id"] if shepherd else None
        
        # 生成 4 隻初始羊
        for i in range(4):
            # 隨機位置（牧場內）
            x = pasture["x"] + random.randint(1, pasture["width"] - 2)
            y = pasture["y"] + random.randint(1, pasture["height"] - 2)
            
            sheep = {
                "id": f"sheep_{self.next_sheep_id}",
                "x": x,
                "y": y,
                "age_days": random.randint(5, 20),  # 隨機年齡
                "is_adult": True,                    # 初始都是成羊
                "wool_ready": random.choice([True, False]),  # 隨機是否可剪毛
                "owner_id": owner_id,
                "pasture_id": pasture["id"],
                "last_move_time": 0,
                "last_breed_check": 0
            }
            
            self.sheep[sheep["id"]] = sheep
            self.next_sheep_id += 1
        
        print(f"🐑 生成了 {len(self.sheep)} 隻羊")
    
    def add_sheep(self, pasture_id: str, owner_id: str, is_adult: bool = False) -> Optional[dict]:
        """新增一隻羊"""
        pasture = self.get_building_by_id(pasture_id)
        if not pasture:
            return None
        
        # 檢查牧場羊數上限（8隻）
        sheep_in_pasture = [s for s in self.sheep.values() if s["pasture_id"] == pasture_id]
        if len(sheep_in_pasture) >= 8:
            return None
        
        # 隨機位置（牧場內）
        x = pasture["x"] + random.randint(1, pasture["width"] - 2)
        y = pasture["y"] + random.randint(1, pasture["height"] - 2)
        
        sheep = {
            "id": f"sheep_{self.next_sheep_id}",
            "x": x,
            "y": y,
            "age_days": 0 if not is_adult else 5,
            "is_adult": is_adult,
            "wool_ready": False,
            "owner_id": owner_id,
            "pasture_id": pasture_id,
            "last_move_time": 0,
            "last_breed_check": 0
        }
        
        self.sheep[sheep["id"]] = sheep
        self.next_sheep_id += 1
        return sheep
    
    def remove_sheep(self, sheep_id: str) -> Optional[dict]:
        """移除一隻羊"""
        if sheep_id in self.sheep:
            return self.sheep.pop(sheep_id)
        return None
    
    def get_sheep_by_owner(self, owner_id: str) -> List[dict]:
        """取得某人擁有的所有羊"""
        return [s for s in self.sheep.values() if s["owner_id"] == owner_id]
    
    def get_sheep_in_pasture(self, pasture_id: str) -> List[dict]:
        """取得牧場內的所有羊"""
        return [s for s in self.sheep.values() if s["pasture_id"] == pasture_id]
    
    def get_sheep_ready_for_shearing(self, owner_id: str) -> List[dict]:
        """取得可以剪毛的羊"""
        return [s for s in self.sheep.values() 
                if s["owner_id"] == owner_id and s["is_adult"] and s["wool_ready"]]
    
    def get_adult_sheep_for_sale(self, owner_id: str) -> List[dict]:
        """取得可以賣的成羊"""
        return [s for s in self.sheep.values() 
                if s["owner_id"] == owner_id and s["is_adult"]]
    
    def update_time(self, delta_time: float):
        """更新遊戲時間"""
        game_seconds = delta_time * self.time_scale
        self.minute += game_seconds / 60
        
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1
    
    def get_time(self) -> dict:
        """取得當前時間"""
        return {
            "day": self.day,
            "hour": int(self.hour),
            "minute": int(self.minute)
        }
    
    def get_villager(self, villager_id: str) -> Optional[dict]:
        """取得村民資料"""
        return self.villagers.get(villager_id)
    
    def get_villagers_summary(self) -> List[dict]:
        """取得所有村民摘要"""
        return [
            {
                "id": v["id"],
                "name": v["name"],
                "occupation": v["occupation"],
                "x": v["x"],
                "y": v["y"],
                "state": v["state"],
                "stats": v.get("stats", {})
            }
            for v in self.villagers.values()
        ]
    
    # ========== 物品管理方法 ==========
    
    def add_world_item(self, item_id: str, quantity: int, x: int, y: int, 
                       owner_id: str = None, durability: int = None) -> dict:
        """在地上放置物品"""
        item = {
            "id": f"world_item_{self.next_item_id}",
            "item_id": item_id,
            "quantity": quantity,
            "x": x,
            "y": y,
            "owner_id": owner_id,
            "durability": durability
        }
        self.world_items.append(item)
        self.next_item_id += 1
        return item
    
    def remove_world_item(self, world_item_id: str) -> Optional[dict]:
        """移除地上物品"""
        for i, item in enumerate(self.world_items):
            if item["id"] == world_item_id:
                return self.world_items.pop(i)
        return None
    
    def get_items_at(self, x: int, y: int) -> List[dict]:
        """取得某位置的所有物品"""
        return [item for item in self.world_items if item["x"] == x and item["y"] == y]
    
    def get_items_by_owner(self, owner_id: str) -> List[dict]:
        """取得某村民擁有的所有地上物品"""
        return [item for item in self.world_items if item["owner_id"] == owner_id]
    
    def get_pickable_items_for(self, villager_id: str, x: int, y: int) -> List[dict]:
        """取得村民在某位置可以撿起的物品"""
        return [
            item for item in self.world_items
            if item["x"] == x and item["y"] == y
            and (item["owner_id"] is None or item["owner_id"] == villager_id)
        ]
    
    def transfer_item_ownership(self, world_item_id: str, new_owner_id: str):
        """轉移物品擁有權"""
        for item in self.world_items:
            if item["id"] == world_item_id:
                item["owner_id"] = new_owner_id
                return True
        return False
    
    def get_all_world_items(self) -> List[dict]:
        """取得所有地上物品"""
        return self.world_items
    
    def get_villagers_needing_decision(self) -> List[dict]:
        """取得需要 AI 決策的村民（task_queue 為空且閒置超過 3 秒）"""
        import time
        import logging
        logger = logging.getLogger("GameState")
        
        current_time = time.time()
        
        pending = []
        for v in self.villagers.values():
            # 沒有任務且閒置超過 3 秒
            if not v.get("task_queue") and current_time - v["last_decision_time"] > 3:
                pending.append(v)
            # 調試：檢查蘇菲為什麼沒被選中
            elif v["name"] == "蘇菲":
                tasks = [t.get("type") for t in v.get("task_queue", [])]
                idle_time = current_time - v["last_decision_time"]
                logger.info(f"🔍 蘇菲狀態: 任務={tasks}, 閒置={idle_time:.1f}秒, 狀態={v.get('state')}")
        
        return pending
    
    def add_tasks(self, villager_id: str, tasks: List[dict]):
        """添加任務到村民的排程"""
        import time
        villager = self.villagers.get(villager_id)
        if not villager:
            return
        
        villager["last_decision_time"] = time.time()
        villager["task_queue"] = tasks
        
        # 如果有任務，開始執行
        if tasks:
            first_task = tasks[0]
            if first_task["type"] == "move":
                villager["state"] = "walking"
            else:
                villager["state"] = first_task["type"]  # eating, working, etc.
    
    def update_relationship(self, from_id: str, to_id: str, changes: dict):
        """更新關係"""
        if from_id == "player":
            entity = self.player
        else:
            entity = self.villagers.get(from_id)
        
        if not entity:
            return
        
        if to_id not in entity["relationships"]:
            entity["relationships"][to_id] = {
                "affection": 0,
                "trust": 0,
                "familiarity": 0
            }
        
        rel = entity["relationships"][to_id]
        for key, value in changes.items():
            if key in rel:
                rel[key] = max(-100, min(100, rel[key] + value))
    
    def add_memory(self, villager_id: str, memory: dict):
        """新增記憶"""
        villager = self.villagers.get(villager_id)
        if not villager:
            return
        
        memory["timestamp"] = datetime.now().isoformat()
        villager["memories"].append(memory)
        
        # 限制記憶數量
        if len(villager["memories"]) > 20:
            villager["memories"] = villager["memories"][-20:]
    
    def pop_events(self) -> List[dict]:
        """取出並清空事件佇列"""
        events = self.events.copy()
        self.events.clear()
        return events
    
    def get_visible_state(self) -> dict:
        """取得可見的遊戲狀態"""
        return {
            "initialized": self.initialized,
            "time": self.get_time(),
            "player": self.player,
            "villagers": self.get_villagers_summary()
        }
    
    def save(self) -> str:
        """儲存遊戲"""
        save_id = f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_path = self.save_dir / save_id
        save_path.mkdir(exist_ok=True)
        
        # 儲存各部分資料
        with open(save_path / "meta.json", "w", encoding="utf-8") as f:
            json.dump({
                "save_id": save_id,
                "timestamp": datetime.now().isoformat(),
                "day": self.day,
                "seed": self.seed
            }, f, ensure_ascii=False, indent=2)
        
        with open(save_path / "game_state.json", "w", encoding="utf-8") as f:
            json.dump({
                "day": self.day,
                "hour": self.hour,
                "minute": self.minute,
                "seed": self.seed,
                "player": self.player,
                "villagers": self.villagers
            }, f, ensure_ascii=False, indent=2)
        
        with open(save_path / "map.json", "w", encoding="utf-8") as f:
            json.dump(self.map_data, f, ensure_ascii=False)
        
        print(f"💾 遊戲已儲存: {save_id}")
        return str(save_path)
    
    def load(self, save_id: str) -> bool:
        """讀取遊戲"""
        save_path = self.save_dir / save_id
        
        if not save_path.exists():
            return False
        
        try:
            with open(save_path / "game_state.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.day = data["day"]
                self.hour = data["hour"]
                self.minute = data["minute"]
                self.seed = data["seed"]
                self.player = data["player"]
                self.villagers = data["villagers"]
            
            with open(save_path / "map.json", "r", encoding="utf-8") as f:
                self.map_data = json.load(f)
            
            self.initialized = True
            print(f"📂 遊戲已讀取: {save_id}")
            return True
        except Exception as e:
            print(f"❌ 讀取失敗: {e}")
            return False
    
    def update_player_position(self, x: float, y: float):
        """更新玩家位置"""
        if self.player:
            self.player["x"] = x
            self.player["y"] = y
    
    def player_interact(self, target_id: str, action_id: str) -> dict:
        """玩家與物件互動"""
        # 找到目標物件
        target = None
        for obj in self.map_data.get("objects", []):
            if obj["id"] == target_id:
                target = obj
                break
        
        if not target:
            return {"success": False, "error": "找不到目標"}
        
        # 找到動作
        action = None
        for act in target.get("actions", []):
            if act["id"] == action_id:
                action = act
                break
        
        if not action:
            return {"success": False, "error": "找不到動作"}
        
        # 執行動作效果
        result = {
            "success": True,
            "action": action_id,
            "target": target_id,
            "message": f"你{action.get('name', action_id)}了"
        }
        
        # 應用效果到玩家
        if "effects" in action:
            for stat, value in action["effects"].items():
                if stat in self.player["stats"]:
                    self.player["stats"][stat] = max(0, min(100, 
                        self.player["stats"][stat] + value
                    ))
        
        return result
    
    # ==================== 建築物查詢 ====================
    
    def get_building_by_type(self, building_type: str) -> Optional[dict]:
        """根據類型取得建築物"""
        for building in self.map_data.get("buildings", []):
            if building["type"] == building_type:
                return building
        return None
    
    def get_building_by_id(self, building_id: str) -> Optional[dict]:
        """根據 ID 取得建築物"""
        for building in self.map_data.get("buildings", []):
            if building["id"] == building_id:
                return building
        return None
    
    def get_building_by_type(self, building_type: str) -> Optional[dict]:
        """根據類型取得建築物（返回第一個符合的）"""
        for building in self.map_data.get("buildings", []):
            if building["type"] == building_type:
                return building
        return None
    
    def get_building_door(self, building: dict) -> Tuple[int, int]:
        """取得建築物內部座標（讓村民進入建築物內）"""
        # 建築物內部範圍（排除牆壁）
        inner_x = building["x"] + 1
        inner_y = building["y"] + 1
        inner_w = building["width"] - 2
        inner_h = building["height"] - 2
        
        # 返回內部的隨機位置
        import random
        target_x = inner_x + random.randint(0, max(0, inner_w - 1))
        target_y = inner_y + random.randint(0, max(0, inner_h - 1))
        return (target_x, target_y)
    
    def get_random_building_of_type(self, building_type: str) -> Optional[dict]:
        """隨機取得某類型的建築物"""
        buildings = [b for b in self.map_data.get("buildings", []) 
                     if b["type"] == building_type]
        return random.choice(buildings) if buildings else None
    
    # ==================== 目標位置解析 ====================
    
    def resolve_action_target(
        self, 
        villager: dict, 
        action: str
    ) -> Optional[Tuple[int, int]]:
        """根據 action 決定目標位置（委託給 TargetResolver）"""
        return self.target_resolver.resolve(villager, action)
    
    # ==================== 路徑計算 ====================
    
    def find_path(
        self, 
        start: Tuple[int, int], 
        goal: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """計算 A* 路徑"""
        if not self.pathfinder:
            return None
        return self.pathfinder.find_path(start, goal)
