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
        
        self.initialized = True
        print(f"🎮 遊戲初始化完成 (種子: {self.seed})")
    
    def _generate_map(self) -> dict:
        """生成地圖"""
        width = 96
        height = 96
        
        # 建築物定義（重新規劃位置，避免重疊）
        buildings = []
        
        # 工作建築（13種職業對應的建築）- 分區規劃
        work_buildings = [
            # === 左上區：食物生產 ===
            {"type": "farm", "name": "農田", "x": 4, "y": 4, "width": 12, "height": 10},          # 農夫
            {"type": "mill", "name": "磨坊", "x": 20, "y": 4, "width": 7, "height": 6},           # 磨坊主
            {"type": "bakery", "name": "麵包店", "x": 30, "y": 4, "width": 7, "height": 6},       # 麵包師
            
            # === 右上區：礦業 ===
            {"type": "mine", "name": "礦場", "x": 76, "y": 4, "width": 12, "height": 8},          # 礦工
            {"type": "blacksmith", "name": "鐵匠舖", "x": 60, "y": 4, "width": 8, "height": 7},   # 鐵匠
            
            # === 中央區：商業 ===
            {"type": "market", "name": "市集", "x": 40, "y": 40, "width": 16, "height": 10},      # 商人
            {"type": "tavern", "name": "酒館", "x": 40, "y": 54, "width": 10, "height": 7},       # 公共場所
            
            # === 左下區：木材 ===
            {"type": "lumber_camp", "name": "伐木場", "x": 4, "y": 76, "width": 12, "height": 10},# 伐木工
            {"type": "carpentry", "name": "木工坊", "x": 20, "y": 80, "width": 8, "height": 7},   # 木匠
            
            # === 右下區：畜牧 ===
            {"type": "pasture", "name": "牧場", "x": 72, "y": 72, "width": 16, "height": 12},     # 牧羊人
            {"type": "butcher_shop", "name": "肉舖", "x": 56, "y": 80, "width": 8, "height": 7},  # 屠夫
            
            # === 右中區：服飾 ===
            {"type": "weaver_shop", "name": "織坊", "x": 76, "y": 40, "width": 8, "height": 6},   # 織工
            {"type": "tannery", "name": "皮革坊", "x": 76, "y": 50, "width": 8, "height": 6},     # 皮革匠
            {"type": "tailor_shop", "name": "裁縫店", "x": 76, "y": 60, "width": 8, "height": 6}, # 裁縫
        ]
        
        for i, b in enumerate(work_buildings):
            b["id"] = f"building_{i}"
            # 門口在中間，2格寬
            b["doorX"] = b["x"] + b["width"] // 2
            b["doorY"] = b["y"] + b["height"] - 1
            b["doorWidth"] = 2  # 門口寬度
            buildings.append(b)
        
        # 民宅（13間，每個村民一間）- 隨機散落
        # 先建立已佔用區域
        occupied = [[False] * width for _ in range(height)]
        margin = 3  # 建築物間距
        
        for b in buildings:
            for dy in range(-margin, b["height"] + margin):
                for dx in range(-margin, b["width"] + margin):
                    nx, ny = b["x"] + dx, b["y"] + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        occupied[ny][nx] = True
        
        # 隨機生成 13 間房屋
        house_count = 0
        max_attempts = 500
        attempts = 0
        house_w, house_h = 6, 5
        
        while house_count < 13 and attempts < max_attempts:
            attempts += 1
            
            # 隨機位置（避開邊緣）
            x = random.randint(8, width - house_w - 8)
            y = random.randint(8, height - house_h - 8)
            
            # 檢查是否可以放置
            can_place = True
            for dy in range(-margin, house_h + margin):
                for dx in range(-margin, house_w + margin):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if occupied[ny][nx]:
                            can_place = False
                            break
                if not can_place:
                    break
            
            if can_place:
                # 標記為已佔用
                for dy in range(-margin, house_h + margin):
                    for dx in range(-margin, house_w + margin):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            occupied[ny][nx] = True
                
                buildings.append({
                    "id": f"building_{len(buildings)}",
                    "type": "house",
                    "name": f"民宅 {house_count + 1}",
                    "x": x, "y": y,
                    "width": house_w, "height": house_h,
                    "doorX": x + 3,
                    "doorY": y + house_h - 1,
                    "doorWidth": 2
                })
                house_count += 1
        
        print(f"🏠 生成了 {house_count} 間民宅")
        
        # 生成碰撞地圖
        collision = [[0] * width for _ in range(height)]
        terrain = [[0] * width for _ in range(height)]
        
        # 不需要圍牆的建築類型（戶外工作場所）
        open_buildings = ["farm", "mine", "lumber_camp", "pasture"]
        
        # 標記建築區域
        for b in buildings:
            door_width = b.get("doorWidth", 1)
            door_x_start = b["doorX"] - door_width // 2
            door_x_end = door_x_start + door_width
            is_open = b["type"] in open_buildings
            
            for dy in range(b["height"]):
                for dx in range(b["width"]):
                    x, y = b["x"] + dx, b["y"] + dy
                    
                    # 根據建築類型設定地形
                    if b["type"] == "farm":
                        terrain[y][x] = 4  # 農田
                    elif b["type"] == "mine":
                        terrain[y][x] = 5  # 礦場（石頭地面）
                    elif b["type"] == "lumber_camp":
                        terrain[y][x] = 6  # 伐木場（森林地面）
                    elif b["type"] == "pasture":
                        terrain[y][x] = 7  # 牧場（草地）
                    else:
                        terrain[y][x] = 3  # 一般地板
                    
                    # 開放式建築不產生圍牆
                    if is_open:
                        continue
                    
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
    
    def _get_social_target(self, villager: dict) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        """取得社交目標 - 找附近的村民聊天
        回傳: (座標, 目標村民ID) 或 (座標, None)
        """
        current_x = villager["x"]
        current_y = villager["y"]
        
        # 排除正在對話中或等待社交中的村民
        excluded_states = ["talking", "waiting_social"]
        
        # 找附近的村民（半徑 20 格內）
        candidates = []
        for other in self.villagers.values():
            if other["id"] == villager["id"]:
                continue
            if other.get("state") in excluded_states:
                continue
            
            dx = other["x"] - current_x
            dy = other["y"] - current_y
            dist = (dx**2 + dy**2) ** 0.5
            
            if dist < 20:
                # 計算優先度：熟悉度 + 好感度 - 距離
                rel = villager.get("relationships", {}).get(other["id"], {})
                familiarity = rel.get("familiarity", 0)
                affection = rel.get("affection", 0)
                priority = familiarity + affection - dist
                candidates.append((other, dist, priority))
        
        if candidates:
            # 按優先度排序，優先找熟悉的人
            candidates.sort(key=lambda x: x[2], reverse=True)
            target_villager = candidates[0][0]
            return ((target_villager["x"], target_villager["y"]), target_villager["id"])
        
        # 找不到人，去市集碰碰運氣
        return (self._get_building_target("market"), None)
    
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
