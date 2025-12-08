/**
 * A* 路徑尋找系統
 */

export class PathFinding {
  constructor() {
    // 方向：上、下、左、右
    this.directions = [
      { x: 0, y: -1 },
      { x: 0, y: 1 },
      { x: -1, y: 0 },
      { x: 1, y: 0 }
    ];
  }
  
  /**
   * 尋找從起點到終點的路徑
   * @param {number} startX - 起點 X
   * @param {number} startY - 起點 Y
   * @param {number} goalX - 終點 X
   * @param {number} goalY - 終點 Y
   * @param {GameMap} map - 遊戲地圖
   * @returns {Array} 路徑點陣列，或 null 如果無法到達
   */
  findPath(startX, startY, goalX, goalY, map) {
    // 如果起點或終點不可通行，直接返回
    if (!map.isWalkable(startX, startY) || !map.isWalkable(goalX, goalY)) {
      return null;
    }
    
    // 如果起點就是終點
    if (startX === goalX && startY === goalY) {
      return [];
    }
    
    // 開放列表和關閉列表
    const openList = [];
    const closedSet = new Set();
    
    // 節點資料結構
    const createNode = (x, y, g, parent) => ({
      x,
      y,
      g,  // 從起點到此節點的成本
      h: this.heuristic(x, y, goalX, goalY),  // 啟發函數
      f: 0,  // f = g + h
      parent
    });
    
    // 起點節點
    const startNode = createNode(startX, startY, 0, null);
    startNode.f = startNode.g + startNode.h;
    openList.push(startNode);
    
    // 節點查詢表
    const nodeMap = {};
    nodeMap[`${startX},${startY}`] = startNode;
    
    let iterations = 0;
    const maxIterations = 1000;
    
    while (openList.length > 0 && iterations < maxIterations) {
      iterations++;
      
      // 找 f 值最小的節點
      openList.sort((a, b) => a.f - b.f);
      const current = openList.shift();
      
      const currentKey = `${current.x},${current.y}`;
      closedSet.add(currentKey);
      
      // 到達目標
      if (current.x === goalX && current.y === goalY) {
        return this.reconstructPath(current);
      }
      
      // 檢查相鄰節點
      for (const dir of this.directions) {
        const nx = current.x + dir.x;
        const ny = current.y + dir.y;
        const neighborKey = `${nx},${ny}`;
        
        // 跳過已關閉的節點
        if (closedSet.has(neighborKey)) continue;
        
        // 跳過不可通行的節點
        if (!map.isWalkable(nx, ny)) continue;
        
        const g = current.g + 1;
        
        // 檢查是否已在開放列表中
        let neighbor = nodeMap[neighborKey];
        
        if (!neighbor) {
          // 新節點
          neighbor = createNode(nx, ny, g, current);
          neighbor.f = neighbor.g + neighbor.h;
          nodeMap[neighborKey] = neighbor;
          openList.push(neighbor);
        } else if (g < neighbor.g) {
          // 找到更好的路徑
          neighbor.g = g;
          neighbor.f = neighbor.g + neighbor.h;
          neighbor.parent = current;
        }
      }
    }
    
    // 無法找到路徑
    return null;
  }
  
  /**
   * 啟發函數 - 曼哈頓距離
   */
  heuristic(x1, y1, x2, y2) {
    return Math.abs(x2 - x1) + Math.abs(y2 - y1);
  }
  
  /**
   * 重建路徑
   */
  reconstructPath(node) {
    const path = [];
    let current = node;
    
    while (current.parent) {
      path.unshift({ x: current.x, y: current.y });
      current = current.parent;
    }
    
    return path;
  }
  
  /**
   * 尋找到最近可用物件的路徑
   * @param {number} startX - 起點 X
   * @param {number} startY - 起點 Y
   * @param {string} objectType - 物件類型
   * @param {GameMap} map - 遊戲地圖
   * @returns {Object} { path, object } 或 null
   */
  findPathToNearestObject(startX, startY, objectType, map) {
    const objects = map.objects.filter(o => o.type === objectType);
    
    if (objects.length === 0) return null;
    
    let bestPath = null;
    let bestObject = null;
    let bestLength = Infinity;
    
    for (const obj of objects) {
      // 尋找物件周圍可站立的位置
      for (const dir of this.directions) {
        const tx = obj.x + dir.x;
        const ty = obj.y + dir.y;
        
        if (!map.isWalkable(tx, ty)) continue;
        
        const path = this.findPath(startX, startY, tx, ty, map);
        
        if (path && path.length < bestLength) {
          bestPath = path;
          bestObject = obj;
          bestLength = path.length;
        }
      }
    }
    
    if (bestPath) {
      return { path: bestPath, object: bestObject };
    }
    
    return null;
  }
}
