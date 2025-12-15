"""
地圖生成器 - 生成遊戲地圖、建築物、地形
"""

import random
from typing import List, Dict


# 河流設定（地圖右邊 1/3 位置）
RIVER_X = 64  # 河流中心 X 座標
RIVER_WIDTH = 4  # 河流寬度
BRIDGE_Y = 49  # 橋樑 Y 座標（主幹道位置，往南一格）
BRIDGE_HEIGHT = 4  # 橋樑高度（2 格寬）

# 工作建築定義（職業對應建築）
# 河流在 x=62~66，建築物需避開
WORK_BUILDINGS = [
    # === 左上區：食物生產 ===
    {"type": "farm", "name": "農田", "x": 4, "y": 4, "width": 12, "height": 10},
    {"type": "mill", "name": "磨坊", "x": 20, "y": 4, "width": 7, "height": 6},
    {"type": "bakery", "name": "麵包店", "x": 30, "y": 4, "width": 7, "height": 6},
    
    # === 河流右側：礦業 ===
    {"type": "mine", "name": "礦場", "x": 72, "y": 4, "width": 12, "height": 8},
    {"type": "blacksmith", "name": "鐵匠舖", "x": 72, "y": 16, "width": 8, "height": 7},
    
    # === 中央區：商業（河流左側）===
    {"type": "market", "name": "市集", "x": 38, "y": 40, "width": 16, "height": 10},
    
    # === 左下區：木材 ===
    {"type": "lumber_camp", "name": "伐木場", "x": 4, "y": 76, "width": 12, "height": 10},
    {"type": "carpentry", "name": "木工坊", "x": 20, "y": 80, "width": 8, "height": 7},
    
    # === 河流右側：畜牧 ===
    {"type": "pasture", "name": "牧場", "x": 72, "y": 72, "width": 16, "height": 12},
    {"type": "butcher_shop", "name": "肉舖", "x": 72, "y": 60, "width": 8, "height": 7},
    
    # === 河流右側：服飾 ===
    {"type": "weaver_shop", "name": "織坊", "x": 72, "y": 28, "width": 8, "height": 6},
    {"type": "tannery", "name": "皮革坊", "x": 82, "y": 28, "width": 8, "height": 6},
    {"type": "tailor_shop", "name": "裁縫店", "x": 82, "y": 38, "width": 8, "height": 6},
]

# 開放式建築（戶外，不需要圍牆）
OPEN_BUILDINGS = ["farm", "mine", "lumber_camp", "pasture", "market"]

# 地形類型對照
TERRAIN_TYPES = {
    "farm": 4,       # 農田
    "mine": 5,       # 礦場
    "lumber_camp": 6, # 伐木場
    "pasture": 7,    # 牧場
    "market": 8,     # 市集廣場
    "default": 3,    # 一般地板
    "river": 9,      # 河流
    "bridge": 10,    # 橋樑
}


def generate_map(seed: int, width: int = 96, height: int = 96) -> dict:
    """
    生成遊戲地圖
    
    Args:
        seed: 隨機種子
        width: 地圖寬度
        height: 地圖高度
        
    Returns:
        地圖資料字典
    """
    random.seed(seed)
    
    buildings = []
    
    # 添加工作建築
    for i, b in enumerate(WORK_BUILDINGS):
        building = b.copy()
        building["id"] = f"building_{i}"
        building["doorX"] = building["x"] + building["width"] // 2
        building["doorY"] = building["y"] + building["height"] - 1
        building["doorWidth"] = 2
        buildings.append(building)
    
    # 生成隨機散落的民宅
    houses = _generate_random_houses(
        buildings, width, height, 
        house_count=13, house_w=6, house_h=5, margin=3
    )
    buildings.extend(houses)
    
    # 生成地形和碰撞地圖
    terrain, collision = _generate_terrain_and_collision(
        buildings, width, height
    )
    
    # 添加河流和橋樑（避開建築物周圍 2 格）
    _add_river(terrain, collision, buildings, width, height)
    
    # 添加道路（連接所有建築）
    _add_roads(terrain, collision, buildings, width, height)
    
    # 物件
    objects = []
    
    return {
        "width": width,
        "height": height,
        "seed": seed,
        "terrain": terrain,
        "collision": collision,
        "buildings": buildings,
        "objects": objects
    }


def _generate_random_houses(
    existing_buildings: List[dict],
    width: int, height: int,
    house_count: int = 13,
    house_w: int = 6, house_h: int = 5,
    margin: int = 3
) -> List[dict]:
    """生成隨機散落的民宅"""
    
    # 河流區域（需要避開）
    river_start = RIVER_X - RIVER_WIDTH // 2 - margin
    river_end = RIVER_X + RIVER_WIDTH // 2 + margin
    
    # 建立已佔用區域
    occupied = [[False] * width for _ in range(height)]
    
    # 標記河流區域為已佔用
    for y in range(height):
        for x in range(river_start, river_end + 1):
            if 0 <= x < width:
                occupied[y][x] = True
    
    for b in existing_buildings:
        for dy in range(-margin, b["height"] + margin):
            for dx in range(-margin, b["width"] + margin):
                nx, ny = b["x"] + dx, b["y"] + dy
                if 0 <= nx < width and 0 <= ny < height:
                    occupied[ny][nx] = True
    
    houses = []
    max_attempts = 500
    attempts = 0
    
    while len(houses) < house_count and attempts < max_attempts:
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
            
            houses.append({
                "id": f"building_{len(existing_buildings) + len(houses)}",
                "type": "house",
                "name": f"民宅 {len(houses) + 1}",
                "x": x, "y": y,
                "width": house_w, "height": house_h,
                "doorX": x + 3,
                "doorY": y + house_h - 1,
                "doorWidth": 2
            })
    
    print(f"🏠 生成了 {len(houses)} 間民宅")
    return houses


def _generate_terrain_and_collision(
    buildings: List[dict],
    width: int, height: int
) -> tuple:
    """生成地形和碰撞地圖"""
    
    collision = [[0] * width for _ in range(height)]
    terrain = [[0] * width for _ in range(height)]
    
    for b in buildings:
        door_width = b.get("doorWidth", 1)
        door_x_start = b["doorX"] - door_width // 2
        door_x_end = door_x_start + door_width
        is_open = b["type"] in OPEN_BUILDINGS
        
        for dy in range(b["height"]):
            for dx in range(b["width"]):
                x, y = b["x"] + dx, b["y"] + dy
                
                # 設定地形類型
                terrain[y][x] = TERRAIN_TYPES.get(b["type"], TERRAIN_TYPES["default"])
                
                # 開放式建築不產生圍牆
                if is_open:
                    continue
                
                # 只有邊緣（牆壁）是碰撞區域
                is_edge = dx == 0 or dx == b["width"]-1 or dy == 0 or dy == b["height"]-1
                
                # 檢查是否是門口
                is_door = (y == b["doorY"] and door_x_start <= x < door_x_end)
                
                # 牆壁不可通行
                if is_edge and not is_door:
                    collision[y][x] = 1
    
    return terrain, collision


def _add_river(terrain: List[List[int]], collision: List[List[int]], buildings: List[dict], width: int, height: int):
    """添加彎曲河流和橋樑（避開建築物周圍 2 格）"""
    
    bridge_start = BRIDGE_Y - 1
    bridge_end = bridge_start + BRIDGE_HEIGHT
    
    # 建立建築物保護區（建築物 + 周圍 2 格）
    protected = set()
    margin = 2
    for b in buildings:
        bx, by, bw, bh = b["x"], b["y"], b["width"], b["height"]
        for dy in range(-margin, bh + margin):
            for dx in range(-margin, bw + margin):
                protected.add((bx + dx, by + dy))
    
    # 河流從地圖上方流向下方，有蜿蜒效果
    river_x = RIVER_X  # 河流起始 X 位置
    river_positions = []  # 記錄每個 Y 座標的河流 X 位置
    
    for y in range(height):
        # 蜿蜒效果：每隔 8 格隨機左右偏移
        if y % 8 == 0 and y > 0:
            direction = 1 if random.random() > 0.5 else -1
            river_x += direction * 2
            # 確保河流不會太靠近邊緣或中心
            river_x = max(width * 0.55, min(width * 0.85, river_x))
        
        river_positions.append(int(river_x))
        
        # 繪製河流寬度
        for dx in range(RIVER_WIDTH):
            x = int(river_x) + dx
            if 0 <= x < width:
                # 跳過建築物保護區
                if (x, y) in protected:
                    continue
                # 檢查是否是橋樑區域
                if bridge_start <= y < bridge_end:
                    terrain[y][x] = TERRAIN_TYPES["bridge"]
                    collision[y][x] = 0  # 橋樑可通行
                else:
                    terrain[y][x] = TERRAIN_TYPES["river"]
                    collision[y][x] = 1  # 河流不可通行
    
    print(f"🌊 彎曲河流生成完成 (起始 x={RIVER_X}, 寬度={RIVER_WIDTH}, 橋樑 y={bridge_start}~{bridge_end})")


def _add_roads(terrain: List[List[int]], collision: List[List[int]], buildings: List[dict], width: int, height: int):
    """添加道路：中央主幹道 + 建築連接最近支線"""
    
    center_x = width // 2
    center_y = height // 2
    
    # 河流相關常數
    river_start = RIVER_X - RIVER_WIDTH // 2
    river_end = RIVER_X + RIVER_WIDTH // 2
    bridge_y = BRIDGE_Y  # 橋樑 Y 座標（水平主幹道經過這裡）
    
    # 主幹道位置（十字）- 水平主幹道改為經過橋樑
    main_roads_x = [center_x, center_x + 1]  # 垂直主幹道（河流左側）
    main_roads_y = [bridge_y, bridge_y + 1]  # 水平主幹道（經過橋樑）
    
    # 畫主幹道（水平方向穿越整個地圖，包括橋樑）
    for x in range(4, width - 4):
        for y in main_roads_y:
            _set_road(terrain, x, y, width, height)
    
    # 畫垂直主幹道（河流左側）
    for y in range(4, height - 4):
        for x in main_roads_x:
            _set_road(terrain, x, y, width, height)
    
    # 河流右側也需要一條垂直主幹道
    right_main_x = [RIVER_X + RIVER_WIDTH // 2 + 8, RIVER_X + RIVER_WIDTH // 2 + 9]
    for y in range(4, height - 4):
        for x in right_main_x:
            _set_road(terrain, x, y, width, height)
    
    # 每個建築門口用最短路徑連到主幹道
    for b in buildings:
        door_x = b.get("doorX", b["x"] + b["width"] // 2)
        door_y = b.get("doorY", b["y"] + b["height"] - 1) + 1
        
        # 判斷建築在河流哪一側
        is_right_side = door_x > river_end
        
        # 選擇對應的垂直主幹道
        target_main_x = right_main_x[0] if is_right_side else center_x
        
        # 判斷連接水平還是垂直主幹道（選最近的）
        dist_to_h = abs(door_y - bridge_y)  # 到水平主幹道的距離
        dist_to_v = abs(door_x - target_main_x)  # 到垂直主幹道的距離
        
        if dist_to_h <= dist_to_v:
            # 垂直連接到水平主幹道
            y_start, y_end = (door_y, bridge_y) if door_y < bridge_y else (bridge_y + 1, door_y)
            for y in range(y_start, y_end + 1):
                _set_road(terrain, door_x, y, width, height)
        else:
            # 水平連接到垂直主幹道
            x_start, x_end = (door_x, target_main_x) if door_x < target_main_x else (target_main_x + 1, door_x)
            for x in range(x_start, x_end + 1):
                _set_road(terrain, x, door_y, width, height)


def _set_road(terrain: List[List[int]], x: int, y: int, width: int, height: int):
    """設定道路地磚（只在草地上畫）"""
    if 0 <= x < width and 0 <= y < height:
        # 只有草地(0)才變成道路(1)，不覆蓋其他地形
        if terrain[y][x] == 0:
            terrain[y][x] = 1
