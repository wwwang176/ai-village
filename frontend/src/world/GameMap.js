/**
 * 遊戲地圖 - 管理地圖資料和查詢
 */

export class GameMap {
  constructor(mapData, tileSize) {
    this.width = mapData.width;
    this.height = mapData.height;
    this.tileSize = tileSize;
    
    this.terrain = mapData.terrain;
    this.collision = mapData.collision;
    this.buildings = mapData.buildings;
    this.objects = mapData.objects || [];
    this.trees = mapData.trees || [];      // 樹木
    this.bushes = mapData.bushes || [];    // 草叢
    this.crops = mapData.crops || [];      // 稻米
    this.ores = mapData.ores || [];        // 礦石
    this.worldItems = [];  // 地上物品（動態更新）
    this.sheep = [];       // 羊群（動態更新）
    
    // 建立物件查詢索引
    this.objectIndex = this.buildObjectIndex();
  }
  
  /**
   * 建立物件位置索引
   */
  buildObjectIndex() {
    const index = {};
    for (const obj of this.objects) {
      const key = `${obj.x},${obj.y}`;
      index[key] = obj;
    }
    return index;
  }
  
  /**
   * 取得地形類型
   */
  getTerrain(x, y) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
      return -1;
    }
    return this.terrain[y][x];
  }
  
  /**
   * 檢查是否可通行
   */
  isWalkable(x, y) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
      return false;
    }
    return this.collision[y][x] === 0;
  }
  
  /**
   * 取得指定位置的物件
   */
  getObjectAt(x, y) {
    const key = `${x},${y}`;
    return this.objectIndex[key] || null;
  }
  
  /**
   * 取得指定位置的建築物
   */
  getBuildingAt(x, y) {
    for (const building of this.buildings) {
      if (x >= building.x && x < building.x + building.width &&
          y >= building.y && y < building.y + building.height) {
        return building;
      }
    }
    return null;
  }
  
  /**
   * 取得玩家出生點
   */
  getPlayerSpawnPoint() {
    // 找到第一間民宅作為玩家住所
    const house = this.buildings.find(b => b.type === 'house');
    
    if (house) {
      return {
        x: house.doorX,
        y: house.doorY + 1
      };
    }
    
    // 備用：地圖中心
    return {
      x: Math.floor(this.width / 2),
      y: Math.floor(this.height / 2)
    };
  }
  
  /**
   * 取得隨機出生點（用於村民）
   */
  getRandomSpawnPoint() {
    // 從建築物門口隨機選擇
    const building = this.buildings[Math.floor(Math.random() * this.buildings.length)];
    return {
      x: building.doorX,
      y: building.doorY + 1
    };
  }
  
  /**
   * 取得附近的物件
   */
  getNearbyObjects(x, y, radius) {
    const nearby = [];
    for (const obj of this.objects) {
      const dist = Math.abs(obj.x - x) + Math.abs(obj.y - y);
      if (dist <= radius) {
        nearby.push(obj);
      }
    }
    return nearby;
  }
  
  /**
   * 取得特定類型的建築物
   */
  getBuildingsByType(type) {
    return this.buildings.filter(b => b.type === type);
  }
}
