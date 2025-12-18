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
from .models import GameTime, VillagerStats, Sheep, Furniture


# === 共用的關係描述函數 ===

def get_affection_desc(affection: int) -> str:
    """好感度文字描述"""
    if affection <= -60: return "仇視"
    if affection <= -30: return "厭惡"
    if affection <= -10: return "略有嫌隙"
    if affection <= 10: return "普通"
    if affection <= 30: return "有好感"
    if affection <= 60: return "友好"
    return "非常親近"

def get_familiarity_desc(familiarity: int) -> str:
    """熟悉度文字描述"""
    if familiarity <= 10: return "陌生人"
    if familiarity <= 30: return "見過幾面"
    if familiarity <= 50: return "認識"
    if familiarity <= 70: return "熟人"
    return "老朋友"


class GameState:
    def __init__(self):
        self.initialized = False
        self.seed = None
        
        # 時間系統
        self.game_time = GameTime()
        
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
        
        # 家具（灶台、床等）
        self.furniture: Dict[str, dict] = {}
        self.next_furniture_id = 0
        
        # 事件佇列
        self.events: List[dict] = []
        
        # 歷史數據（每小時快照）
        self.history: List[dict] = []
        self.last_history_hour = -1  # 上次記錄的小時
        
        # 天氣系統
        self.weather = "sunny"  # 當前天氣
        self.weather_end_hour = 0  # 天氣結束的遊戲小時
        
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
                "satiety": 100,
                "social": 50,
                "happiness": 70,
                "health": 100,
                "money": 50
            },
            "relationships": {}
        }
        
        # 生成村民（14種職業各1人）
        self._generate_villagers(14)
        
        # 生成羊群（牧場初始 4 隻羊）
        self._generate_sheep()
        
        # 生成房屋家具（灶台、床）
        self._generate_furniture()
        
        # 初始化目標解析器
        self.target_resolver = TargetResolver(self)
        
        # 初始化天氣
        self._init_weather()
        
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
        
        # 性格系統：從設定檔讀取 7 個維度
        from ..data.personalities import get_dimension_traits
        personality_dimensions = get_dimension_traits()
        
        # 喜好池
        hobbies = [
            "閱讀", "釣魚", "園藝", "烹飪", "唱歌", "跳舞", "下棋", "繪畫",
            "狩獵", "釀酒", "縫紉", "木工", "講故事", "觀星", "收集石頭", "養寵物",
            "射箭", "騎馬", "養蜂", "編織", "製陶", "草藥學", "養鴿", "飼養獵犬",
            "吹笛", "彈琴", "雕刻", "打鐵藝術", "石雕", "馴鷹", "賭博", "打獵"
        ]
        
        # 喜歡的食物
        favorite_foods = [
            "烤肉", "麵包", "乳酪", "蘋果派", "燉菜", "烤魚", "蜂蜜蛋糕", "葡萄酒",
            "烤雞", "羊肉湯", "燕麥粥", "鹹豬肉", "野味派", "蜂蜜酒", "黑麵包", "奶油濃湯"
        ]
        
        # 討厭的事物
        dislikes = [
            "下雨天", "早起", "吵雜", "蟲子", "寒冷", "炎熱", "說謊的人", "懶惰的人",
            "稅吏", "強盜", "瘟疫", "飢荒", "戰爭", "異端審判", "粗魯的人", "背叛者"
        ]
        
        # 14種職業（對應工作建築）- 使用新的職業 ID
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
            "bartender",    # 酒吧 - 酒保
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
            
            # 隨機性格：從 7 個維度中抽 6 個，每個維度抽一個正或反
            selected_dimensions = random.sample(list(personality_dimensions.keys()), 6)
            traits = [random.choice(personality_dimensions[dim]) for dim in selected_dimensions]
            
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
                "bartender": "tavern",
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
            
            # 初始化背包（5格）
            inventory = [None] * 5
            
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
            
            # 給予初始麵包（讓村民在供應鏈建立前不會餓死）
            bread_slot = 1 if inventory[0] else 0
            inventory[bread_slot] = {
                "item_id": "bread",
                "quantity": 10,
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
                "stats": VillagerStats(
                    energy=random.randint(30, 100),
                    satiety=random.randint(40, 100),
                    social=random.randint(20, 80),
                    happiness=random.randint(40, 90),
                    health=random.randint(70, 100)
                ).to_dict(),
                "preferences": {
                    "hobbies": villager_hobbies,        # 興趣愛好
                    "favorite_foods": villager_foods,   # 喜歡的食物
                    "dislikes": villager_dislikes       # 討厭的事物
                },
                "inventory": inventory,                 # 背包（5格）
                "money": 1000 if occupation == "merchant" else random.randint(100, 200),  # 商人有較多錢
                "state": "idle",
                "memories": [],
                "relationships": {},
                "last_decision_time": 0,
                "task_queue": []  # 任務排程
            }
            
            self.villagers[villager["id"]] = villager
            
            # # 在村民家裡地上放置麵包（1~10個，分流購買時間）
            # bread_count = random.randint(1, 10)
            # self.add_world_item(
            #     item_id="bread",
            #     quantity=bread_count,
            #     x=spawn["doorX"] -1,
            #     y=spawn["doorY"] -2,
            #     owner_id=villager["id"]
            # )
        
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
            x = pasture["x"] + random.randint(1, pasture["width"] - 2)
            y = pasture["y"] + random.randint(1, pasture["height"] - 2)
            
            sheep = Sheep(
                id=f"sheep_{self.next_sheep_id}",
                x=x,
                y=y,
                age_days=random.randint(5, 20),
                is_adult=True,
                wool_ready=random.choice([True, False]),
                owner_id=owner_id,
                pasture_id=pasture["id"]
            )
            
            self.sheep[sheep.id] = sheep.to_dict()
            self.next_sheep_id += 1
        
        print(f"🐑 生成了 {len(self.sheep)} 隻羊")
    
    def _generate_furniture(self):
        """為每個住宅生成灶台和床"""
        buildings = self.map_data.get("buildings", [])
        
        for building in buildings:
            # 只為住宅類建築生成家具
            if building.get("type") not in ["house", "cottage"]:
                continue
            
            building_id = building.get("id")
            bx = building.get("x", 0)
            by = building.get("y", 0)
            bw = building.get("width", 3)
            bh = building.get("height", 3)
            
            # 在建築內部放置灶台（左下角）
            stove = Furniture(
                id=f"furniture_{self.next_furniture_id}",
                type="stove",
                x=bx + 1,
                y=by + bh - 2,
                building_id=building_id
            )
            self.furniture[stove.id] = stove.to_dict()
            self.next_furniture_id += 1
            
            # 在建築內部放置床（右上角）
            bed = Furniture(
                id=f"furniture_{self.next_furniture_id}",
                type="bed",
                x=bx + bw - 2,
                y=by + 1,
                building_id=building_id
            )
            self.furniture[bed.id] = bed.to_dict()
            self.next_furniture_id += 1
        
        print(f"🏠 生成了 {len(self.furniture)} 件家具")
    
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
        
        sheep = Sheep(
            id=f"sheep_{self.next_sheep_id}",
            x=x,
            y=y,
            age_days=0 if not is_adult else 5,
            is_adult=is_adult,
            wool_ready=False,
            owner_id=owner_id,
            pasture_id=pasture_id
        )
        
        sheep_dict = sheep.to_dict()
        self.sheep[sheep.id] = sheep_dict
        self.next_sheep_id += 1
        return sheep_dict
    
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
    
    # ==================== 家具相關方法 ====================
    
    def get_furniture_by_building(self, building_id: str) -> List[dict]:
        """取得建築內的所有家具"""
        return [f for f in self.furniture.values() if f["building_id"] == building_id]
    
    def get_furniture_by_type(self, building_id: str, furniture_type: str) -> Optional[dict]:
        """取得建築內特定類型的家具"""
        for f in self.furniture.values():
            if f["building_id"] == building_id and f["type"] == furniture_type:
                return f
        return None
    
    def get_stove_by_residence(self, villager_id: str) -> Optional[dict]:
        """取得村民住所的灶台"""
        villager = self.villagers.get(villager_id)
        if not villager:
            return None
        residence_id = villager.get("residence")
        if not residence_id:
            return None
        return self.get_furniture_by_type(residence_id, "stove")
    
    def get_bed_by_residence(self, villager_id: str) -> Optional[dict]:
        """取得村民住所的床"""
        villager = self.villagers.get(villager_id)
        if not villager:
            return None
        residence_id = villager.get("residence")
        if not residence_id:
            return None
        return self.get_furniture_by_type(residence_id, "bed")
    
    def use_furniture(self, furniture_id: str, user_id: str) -> bool:
        """使用家具"""
        if furniture_id not in self.furniture:
            return False
        furniture = self.furniture[furniture_id]
        if furniture["in_use"]:
            return False  # 已被使用
        furniture["in_use"] = True
        furniture["user_id"] = user_id
        return True
    
    def release_furniture(self, furniture_id: str) -> bool:
        """釋放家具"""
        if furniture_id not in self.furniture:
            return False
        furniture = self.furniture[furniture_id]
        furniture["in_use"] = False
        furniture["user_id"] = None
        return True
    
    def update_time(self, delta_time: float):
        """更新遊戲時間"""
        self.game_time.update(delta_time)
    
    def get_time(self) -> dict:
        """取得當前時間"""
        return self.game_time.to_dict()
    
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
        """取得所有地上物品（含擁有者名稱）"""
        result = []
        for item in self.world_items:
            item_copy = item.copy()
            if item.get("owner_id"):
                owner = self.villagers.get(item["owner_id"])
                item_copy["owner_name"] = owner["name"] if owner else None
            else:
                item_copy["owner_name"] = None
            result.append(item_copy)
        return result
    
    def get_villagers_needing_decision(self) -> List[dict]:
        """取得需要 AI 決策的村民（task_queue 為空且閒置超過 3 秒）"""
        import time
        import logging
        logger = logging.getLogger("GameState")
        
        current_time = time.time()
        
        pending = []
        for v in self.villagers.values():
            # 排除正在對話或等待社交的村民
            if v.get("state") in ("talking", "waiting_social"):
                continue
            
            # 沒有任務且閒置超過 3 秒
            if not v.get("task_queue") and current_time - v["last_decision_time"] > 3:
                pending.append(v)
        
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
                "day": self.game_time.day,
                "seed": self.seed
            }, f, ensure_ascii=False, indent=2)
        
        with open(save_path / "game_state.json", "w", encoding="utf-8") as f:
            json.dump({
                "time": self.game_time.to_dict(),
                "seed": self.seed,
                "player": self.player,
                "villagers": self.villagers,
                "weather": self.weather,
                "weather_end_hour": self.weather_end_hour
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
                if "time" in data:
                    self.game_time = GameTime.from_dict(data["time"])
                else:
                    # 相容舊存檔格式
                    self.game_time = GameTime(
                        day=data.get("day", 1),
                        hour=data.get("hour", 8),
                        minute=data.get("minute", 0)
                    )
                self.seed = data["seed"]
                self.player = data["player"]
                self.villagers = data["villagers"]
                
                # 讀取天氣狀態（相容舊存檔）
                self.weather = data.get("weather", "sunny")
                self.weather_end_hour = data.get("weather_end_hour", self.game_time.total_hours + 4)
            
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
    
    def get_workplace(self, villager: dict) -> Optional[dict]:
        """取得村民的工作地點建築物"""
        workplace_id = villager.get("workplace")
        if not workplace_id:
            return None
        return self.get_building_by_id(workplace_id)
    
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
    
    def get_building_at_position(self, x: int, y: int) -> Optional[dict]:
        """取得指定座標所在的建築物"""
        for building in self.map_data.get("buildings", []):
            bx, by = building["x"], building["y"]
            bw, bh = building["width"], building["height"]
            if bx <= x < bx + bw and by <= y < by + bh:
                return building
        return None
    
    def is_outdoor_building(self, building_type: str) -> bool:
        """判斷建築物是否為開放式（室外）建築"""
        outdoor_types = {"pasture", "farm", "mine", "lumber_camp", "market"}
        return building_type in outdoor_types
    
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
    
    # ==================== 歷史數據記錄 ====================
    
    def record_history_snapshot(self):
        """記錄當前狀態快照（每遊戲小時呼叫一次）"""
        current_hour = self.game_time.hour
        current_day = self.game_time.day
        
        # 避免同一小時重複記錄
        time_key = current_day * 24 + current_hour
        if time_key == self.last_history_hour:
            return
        self.last_history_hour = time_key
        
        # 計算村民統計數據
        villager_list = list(self.villagers.values())
        if not villager_list:
            return
        
        # 計算平均值
        total_satiety = 0
        total_energy = 0
        total_social = 0
        total_money = 0
        
        # 個人數據
        individual_data = {}
        
        for v in villager_list:
            stats = v.get("stats", {})
            satiety = stats.get("satiety", 100)
            energy = stats.get("energy", 100)
            social = stats.get("social", 50)
            money = v.get("money", 0)
            
            total_satiety += satiety
            total_energy += energy
            total_social += social
            total_money += money
            
            individual_data[v["id"]] = {
                "name": v["name"],
                "satiety": round(satiety, 1),
                "energy": round(energy, 1),
                "social": round(social, 1),
                "money": money
            }
        
        count = len(villager_list)
        snapshot = {
            "day": current_day,
            "hour": current_hour,
            "time_key": time_key,  # 用於 X 軸排序
            "avg_satiety": round(total_satiety / count, 1),
            "avg_energy": round(total_energy / count, 1),
            "avg_social": round(total_social / count, 1),
            "total_money": total_money,
            "villagers": individual_data
        }
        
        self.history.append(snapshot)
        
        # 限制歷史記錄數量（最多保留 720 筆 = 30 天）
        if len(self.history) > 720:
            self.history = self.history[-720:]
    
    def get_history(self, hours: int = None, villager_id: str = None) -> List[dict]:
        """取得歷史數據
        
        Args:
            hours: 取最近幾小時的數據，None 表示全部
            villager_id: 指定村民 ID，None 表示全體平均
        
        Returns:
            歷史數據列表
        """
        data = self.history
        
        # 篩選時間範圍
        if hours and len(data) > hours:
            data = data[-hours:]
        
        # 如果指定村民，轉換格式
        if villager_id:
            result = []
            for snapshot in data:
                villager_data = snapshot.get("villagers", {}).get(villager_id)
                if villager_data:
                    result.append({
                        "day": snapshot["day"],
                        "hour": snapshot["hour"],
                        "time_key": snapshot["time_key"],
                        "satiety": villager_data["satiety"],
                        "energy": villager_data["energy"],
                        "social": villager_data["social"],
                        "money": villager_data["money"]
                    })
            return result
        
        # 全體平均數據（不含個人詳細）
        return [
            {
                "day": s["day"],
                "hour": s["hour"],
                "time_key": s["time_key"],
                "avg_satiety": s["avg_satiety"],
                "avg_energy": s["avg_energy"],
                "avg_social": s["avg_social"],
                "total_money": s["total_money"]
            }
            for s in data
        ]
    
    # ============================================================
    # 天氣系統
    # ============================================================
    
    def _init_weather(self):
        """初始化天氣"""
        from ..data.weather import WEATHER_DURATION_MIN, WEATHER_DURATION_MAX
        self.weather = "sunny"
        # 設定第一次天氣變化的時間
        duration = random.randint(WEATHER_DURATION_MIN, WEATHER_DURATION_MAX)
        self.weather_end_hour = self.game_time.total_hours + duration
    
    def update_weather(self):
        """更新天氣（每 tick 呼叫）"""
        from ..data.weather import (
            WEATHER_TYPES, WEATHER_TRANSITIONS,
            WEATHER_DURATION_MIN, WEATHER_DURATION_MAX
        )
        
        current_hour = self.game_time.total_hours
        
        # 還沒到變化時間
        if current_hour < self.weather_end_hour:
            return
        
        # 根據轉換機率決定下一個天氣
        transitions = WEATHER_TRANSITIONS.get(self.weather, {})
        if not transitions:
            return
        
        # 加權隨機選擇
        weather_ids = list(transitions.keys())
        weights = list(transitions.values())
        new_weather = random.choices(weather_ids, weights=weights, k=1)[0]
        
        if new_weather != self.weather:
            old_weather = WEATHER_TYPES[self.weather]
            new_weather_type = WEATHER_TYPES[new_weather]
            print(f"🌤️ 天氣變化: {old_weather.icon} {old_weather.name} → {new_weather_type.icon} {new_weather_type.name}")
        
        self.weather = new_weather
        
        # 設定下次變化時間
        duration = random.randint(WEATHER_DURATION_MIN, WEATHER_DURATION_MAX)
        self.weather_end_hour = current_hour + duration
    
    def is_villager_outdoor(self, villager: dict) -> bool:
        """檢查村民是否在室外"""
        from ..data.weather import OUTDOOR_BUILDINGS
        
        vx, vy = villager.get("x", 0), villager.get("y", 0)
        
        # 找村民所在的建築物
        for building in self.map_data.get("buildings", []):
            bx, by = building.get("x", 0), building.get("y", 0)
            bw, bh = building.get("width", 1), building.get("height", 1)
            
            # 村民在建築物範圍內
            if bx <= vx < bx + bw and by <= vy < by + bh:
                building_type = building.get("type", "")
                # 開放式建築 = 室外
                return building_type in OUTDOOR_BUILDINGS
        
        # 不在任何建築物內 = 室外（道路、空地）
        return True
    
    def get_weather_info(self) -> dict:
        """取得天氣資訊（供 API 和 AI 使用）"""
        from ..data.weather import get_weather_type
        
        weather_type = get_weather_type(self.weather)
        return {
            "id": weather_type.id,
            "name": weather_type.name,
            "icon": weather_type.icon,
            "stamina_drain": weather_type.stamina_drain,
            "darkness": weather_type.darkness
        }
