"""
遊戲狀態管理
"""

import json
import random
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .pathfinding import PathFinding


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
        
        # 生成村民
        self._generate_villagers(29)
        
        self.initialized = True
        print(f"🎮 遊戲初始化完成 (種子: {self.seed})")
    
    def _generate_map(self) -> dict:
        """生成地圖"""
        width = 64
        height = 64
        
        # 建築物定義（加大尺寸，門口2格寬）
        buildings = []
        
        # 必要建築（加大）
        required = [
            {"type": "tavern", "name": "酒館", "x": 18, "y": 22, "width": 8, "height": 7},
            {"type": "church", "name": "教堂", "x": 34, "y": 20, "width": 10, "height": 8},
            {"type": "market", "name": "市集", "x": 20, "y": 38, "width": 8, "height": 6},
            {"type": "blacksmith", "name": "鐵匠舖", "x": 36, "y": 38, "width": 7, "height": 6},
        ]
        
        for i, b in enumerate(required):
            b["id"] = f"building_{i}"
            # 門口在中間，2格寬
            b["doorX"] = b["x"] + b["width"] // 2
            b["doorY"] = b["y"] + b["height"] - 1
            b["doorWidth"] = 2  # 門口寬度
            buildings.append(b)
        
        # 隨機民宅（加大）
        house_positions = [
            (8, 12), (48, 12), (8, 46), (48, 46), (28, 8)
        ]
        for i, (x, y) in enumerate(house_positions):
            buildings.append({
                "id": f"building_{len(buildings)}",
                "type": "house",
                "name": f"民宅 {i+1}",
                "x": x, "y": y,
                "width": 6, "height": 6,
                "doorX": x + 3,
                "doorY": y + 5,
                "doorWidth": 2
            })
        
        # 生成碰撞地圖
        collision = [[0] * width for _ in range(height)]
        terrain = [[0] * width for _ in range(height)]
        
        # 標記建築區域
        for b in buildings:
            door_width = b.get("doorWidth", 1)
            door_x_start = b["doorX"] - door_width // 2
            door_x_end = door_x_start + door_width
            
            for dy in range(b["height"]):
                for dx in range(b["width"]):
                    x, y = b["x"] + dx, b["y"] + dy
                    terrain[y][x] = 3  # 地板
                    
                    # 只有邊緣（牆壁）是碰撞區域
                    is_edge = dx == 0 or dx == b["width"]-1 or dy == 0 or dy == b["height"]-1
                    
                    # 檢查是否是門口（2格寬）
                    is_door = (y == b["doorY"] and door_x_start <= x < door_x_end)
                    
                    # 牆壁不可通行，門口可通行，內部可通行
                    if is_edge and not is_door:
                        collision[y][x] = 1
        
        # 道路
        center_y = 32
        for x in range(10, 54):
            terrain[center_y][x] = 1
            terrain[center_y+1][x] = 1
        
        # 物件
        objects = [
            {"id": "well_1", "type": "well", "name": "水井", "x": 31, "y": 30,
             "actions": [{"id": "draw_water", "name": "打水", "duration": 3000}]}
        ]
        
        return {
            "width": width,
            "height": height,
            "seed": self.seed,
            "terrain": terrain,
            "collision": collision,
            "buildings": buildings,
            "objects": objects
        }
    
    def _get_player_spawn(self) -> dict:
        """取得玩家出生點"""
        houses = [b for b in self.map_data["buildings"] if b["type"] == "house"]
        if houses:
            h = houses[0]
            return {"x": h["doorX"], "y": h["doorY"] + 1}
        return {"x": 32, "y": 32}
    
    def _generate_villagers(self, count: int):
        """生成村民"""
        names_male = ["艾德蒙", "約翰", "威廉", "亨利", "湯瑪斯", "羅伯特", "理查", "查爾斯"]
        names_female = ["瑪莉", "伊莉莎白", "安娜", "凱薩琳", "艾瑪", "露西", "克萊兒", "蘇菲"]
        
        personalities = {
            "positive": ["friendly", "hardworking", "generous", "optimistic", "curious"],
            "negative": ["greedy", "lazy", "suspicious", "grumpy", "gossip"],
            "neutral": ["introvert", "extrovert", "romantic", "religious"]
        }
        
        occupations = ["tavern", "church", "market", "blacksmith", "house"]
        
        for i in range(count):
            gender = random.choice(["male", "female"])
            name = random.choice(names_male if gender == "male" else names_female)
            
            # 隨機性格
            traits = [random.choice(personalities["positive"])]
            if random.random() > 0.5:
                traits.append(random.choice(personalities["negative"]))
            if random.random() > 0.5:
                traits.append(random.choice(personalities["neutral"]))
            
            # 分配職業和工作地點
            occupation = occupations[i % len(occupations)]
            
            # 根據職業找對應的建築物作為工作地點
            workplace = None
            for b in self.map_data["buildings"]:
                if b["type"] == occupation:
                    workplace = b["id"]
                    break
            
            # 分配住所（輪流分配到各民宅）
            houses = [b for b in self.map_data["buildings"] if b["type"] == "house"]
            residence = houses[i % len(houses)]["id"] if houses else None
            
            # 出生在住所門口
            spawn = self.get_building_by_id(residence) if residence else self.map_data["buildings"][0]
            
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
                    "energy": 70 + random.random() * 30,
                    "hunger": random.random() * 30,
                    "social": 40 + random.random() * 30,
                    "happiness": 50 + random.random() * 30,
                    "health": 80 + random.random() * 20
                },
                "state": "idle",
                "memories": [],
                "relationships": {},
                "last_decision_time": 0,
                "task_queue": []  # 任務排程
            }
            
            self.villagers[villager["id"]] = villager
    
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
        """
        根據 action 決定目標位置
        
        Args:
            villager: 村民資料
            action: AI 決定的行為
            
        Returns:
            目標座標 (x, y) 或 None
        """
        # 行為對應的目標類型
        action_targets = {
            "go_work": lambda v: self._get_work_target(v),
            "go_home": lambda v: self._get_home_target(v),
            "go_tavern": lambda v: self._get_building_target("tavern"),
            "go_church": lambda v: self._get_building_target("church"),
            "go_market": lambda v: self._get_building_target("market"),
            "go_blacksmith": lambda v: self._get_building_target("blacksmith"),
            "eat": lambda v: self._get_eat_target(v),
            "rest": lambda v: self._get_home_target(v),
            "sleep": lambda v: self._get_home_target(v),
            "socialize": lambda v: self._get_social_target(v),
            "wander": lambda v: self._get_wander_target(v),
        }
        
        resolver = action_targets.get(action)
        if resolver:
            return resolver(villager)
        
        # 未知行為，隨機閒逛
        return self._get_wander_target(villager)
    
    def _get_work_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得工作地點"""
        workplace_id = villager.get("workplace")
        if workplace_id:
            building = self.get_building_by_id(workplace_id)
            if building:
                return self.get_building_door(building)
        # 沒有工作地點的村民，去市集逛逛
        return self._get_building_target("market")
    
    def _get_home_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得住所"""
        residence_id = villager.get("residence")
        if residence_id:
            building = self.get_building_by_id(residence_id)
            if building:
                return self.get_building_door(building)
        # 沒有住所的村民，隨機找一間民宅
        house = self.get_random_building_of_type("house")
        if house:
            return self.get_building_door(house)
        return None
    
    def _get_building_target(self, building_type: str) -> Optional[Tuple[int, int]]:
        """取得特定類型建築物"""
        building = self.get_building_by_type(building_type)
        if building:
            return self.get_building_door(building)
        return None
    
    def _get_eat_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得吃東西的地點（酒館或家）"""
        # 優先去酒館
        target = self._get_building_target("tavern")
        if target:
            return target
        # 否則回家
        return self._get_home_target(villager)
    
    def _get_social_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """取得社交地點（市集、酒館或教堂）"""
        options = ["market", "tavern", "church"]
        building_type = random.choice(options)
        return self._get_building_target(building_type)
    
    def _get_wander_target(self, villager: dict) -> Optional[Tuple[int, int]]:
        """隨機閒逛目標"""
        current_x = int(villager["x"])
        current_y = int(villager["y"])
        
        # 在附近隨機找一個可走的點
        for _ in range(10):
            dx = random.randint(-8, 8)
            dy = random.randint(-8, 8)
            target_x = max(1, min(self.map_data["width"] - 2, current_x + dx))
            target_y = max(1, min(self.map_data["height"] - 2, current_y + dy))
            
            if self.pathfinder and self.pathfinder.is_walkable(target_x, target_y):
                return (target_x, target_y)
        
        return None
    
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
