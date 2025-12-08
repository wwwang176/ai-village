"""
A* 路徑尋找演算法
"""

import heapq
from typing import List, Tuple, Optional, Set


class PathFinding:
    """A* 路徑尋找"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.collision: Set[Tuple[int, int]] = set()
    
    def set_collision_map(self, collision_data: List[List[int]]):
        """設定碰撞地圖 (1 = 不可通行)"""
        self.collision.clear()
        for y, row in enumerate(collision_data):
            for x, val in enumerate(row):
                if val == 1:
                    self.collision.add((x, y))
    
    def add_collision(self, x: int, y: int):
        """添加碰撞點"""
        self.collision.add((x, y))
    
    def remove_collision(self, x: int, y: int):
        """移除碰撞點"""
        self.collision.discard((x, y))
    
    def is_walkable(self, x: int, y: int) -> bool:
        """檢查是否可通行"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        return (x, y) not in self.collision
    
    def find_path(
        self, 
        start: Tuple[int, int], 
        goal: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """
        A* 尋路
        
        Args:
            start: 起點 (x, y)
            goal: 終點 (x, y)
            
        Returns:
            路徑列表 [(x1,y1), (x2,y2), ...] 或 None (無法到達)
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        
        # 如果終點不可通行，找最近的可通行點
        if not self.is_walkable(goal[0], goal[1]):
            goal = self._find_nearest_walkable(goal)
            if goal is None:
                return None
        
        # 如果起點不可通行，找最近的可通行點
        if not self.is_walkable(start[0], start[1]):
            start = self._find_nearest_walkable(start)
            if start is None:
                return None
        
        # 已經在目標位置
        if start == goal:
            return [goal]
        
        # A* 演算法
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, goal)}
        
        open_set_hash = {start}
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            open_set_hash.discard(current)
            
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self._get_neighbors(current):
                # 移動成本 (斜向移動成本較高)
                dx = abs(neighbor[0] - current[0])
                dy = abs(neighbor[1] - current[1])
                move_cost = 1.414 if dx + dy == 2 else 1.0
                
                tentative_g = g_score[current] + move_cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal)
                    
                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        open_set_hash.add(neighbor)
        
        # 無法到達
        return None
    
    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """啟發式函數 (曼哈頓距離)"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def _get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """取得相鄰可通行格子"""
        x, y = pos
        neighbors = []
        
        # 8 方向
        directions = [
            (-1, -1), (0, -1), (1, -1),
            (-1,  0),          (1,  0),
            (-1,  1), (0,  1), (1,  1)
        ]
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            
            if self.is_walkable(nx, ny):
                # 斜向移動需要檢查相鄰格是否可通行（防止穿牆角）
                if dx != 0 and dy != 0:
                    if not self.is_walkable(x + dx, y) or not self.is_walkable(x, y + dy):
                        continue
                
                neighbors.append((nx, ny))
        
        return neighbors
    
    def _reconstruct_path(
        self, 
        came_from: dict, 
        current: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """重建路徑"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def _find_nearest_walkable(
        self, 
        pos: Tuple[int, int], 
        max_radius: int = 5
    ) -> Optional[Tuple[int, int]]:
        """找最近的可通行點"""
        x, y = pos
        
        for radius in range(1, max_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = x + dx, y + dy
                        if self.is_walkable(nx, ny):
                            return (nx, ny)
        
        return None
