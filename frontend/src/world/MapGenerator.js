/**
 * 地圖生成器 - 隨機生成村莊
 */

export class MapGenerator {
  constructor(config) {
    this.width = config.width || 64;
    this.height = config.height || 64;
    this.tileSize = config.tileSize || 16;
    
    // 建築物定義
    this.buildingTypes = {
      tavern: { name: '酒館', width: 6, height: 5, required: true },
      church: { name: '教堂', width: 7, height: 6, required: true },
      market: { name: '市集', width: 5, height: 4, required: true },
      blacksmith: { name: '鐵匠舖', width: 5, height: 4, required: true },
      house: { name: '民宅', width: 4, height: 4, required: false },
      bakery: { name: '麵包坊', width: 4, height: 4, required: false },
      farm: { name: '農舍', width: 5, height: 5, required: false }
    };
  }
  
  /**
   * 生成完整地圖
   */
  generate() {
    console.log('開始生成地圖...');
    
    // 初始化地形陣列（全部是草地）
    const terrain = this.createEmptyTerrain();
    const collision = this.createEmptyCollision();
    const buildings = [];
    const objects = [];
    
    // 生成河流（在建築之前）
    this.generateRiver(terrain, collision);
    
    // 放置必要建築
    this.placeRequiredBuildings(buildings, terrain, collision);
    
    // 放置隨機建築（民宅等）
    this.placeRandomBuildings(buildings, terrain, collision, 5);
    
    // 生成道路連接建築物
    this.generateRoads(buildings, terrain);
    
    // 生成橋樑（跨越河流的道路）
    this.generateBridges(terrain, collision, objects);
    
    // 放置水井（公共設施）
    this.placeWell(objects, buildings, terrain, collision);
    
    // 放置裝飾物（樹木等）
    this.placeDecorations(objects, terrain, collision);
    
    // 在建築物內放置物件
    this.placeBuildingObjects(buildings, objects);
    
    return {
      width: this.width,
      height: this.height,
      terrain,
      collision,
      buildings,
      objects
    };
  }
  
  createEmptyTerrain() {
    const terrain = [];
    for (let y = 0; y < this.height; y++) {
      terrain[y] = [];
      for (let x = 0; x < this.width; x++) {
        terrain[y][x] = 0; // 草地
      }
    }
    return terrain;
  }
  
  createEmptyCollision() {
    const collision = [];
    for (let y = 0; y < this.height; y++) {
      collision[y] = [];
      for (let x = 0; x < this.width; x++) {
        collision[y][x] = 0; // 可通行
      }
    }
    return collision;
  }
  
  /**
   * 放置必要建築
   */
  placeRequiredBuildings(buildings, terrain, collision) {
    const requiredTypes = ['tavern', 'church', 'market', 'blacksmith'];
    
    // 將必要建築放在地圖中央區域
    const centerX = Math.floor(this.width / 2);
    const centerY = Math.floor(this.height / 2);
    
    const positions = [
      { x: centerX - 12, y: centerY - 8 },
      { x: centerX + 4, y: centerY - 8 },
      { x: centerX - 10, y: centerY + 4 },
      { x: centerX + 4, y: centerY + 4 }
    ];
    
    for (let i = 0; i < requiredTypes.length; i++) {
      const type = requiredTypes[i];
      const def = this.buildingTypes[type];
      const pos = positions[i];
      
      const building = {
        id: `building_${buildings.length}`,
        type: type,
        name: def.name,
        x: pos.x,
        y: pos.y,
        width: def.width,
        height: def.height,
        objects: []
      };
      
      buildings.push(building);
      this.markBuildingArea(building, terrain, collision);
    }
  }
  
  /**
   * 放置隨機建築
   */
  placeRandomBuildings(buildings, terrain, collision, count) {
    const randomTypes = ['house', 'house', 'house', 'bakery', 'farm'];
    let placed = 0;
    let attempts = 0;
    const maxAttempts = 100;
    
    while (placed < count && attempts < maxAttempts) {
      attempts++;
      
      const type = randomTypes[Math.floor(Math.random() * randomTypes.length)];
      const def = this.buildingTypes[type];
      
      // 隨機位置
      const x = Math.floor(Math.random() * (this.width - def.width - 10)) + 5;
      const y = Math.floor(Math.random() * (this.height - def.height - 10)) + 5;
      
      // 檢查是否可放置
      if (this.canPlaceBuilding(x, y, def.width, def.height, collision)) {
        const building = {
          id: `building_${buildings.length}`,
          type: type,
          name: `${def.name} ${placed + 1}`,
          x: x,
          y: y,
          width: def.width,
          height: def.height,
          objects: []
        };
        
        buildings.push(building);
        this.markBuildingArea(building, terrain, collision);
        placed++;
      }
    }
  }
  
  /**
   * 檢查是否可放置建築
   */
  canPlaceBuilding(x, y, width, height, collision) {
    // 加上邊距
    const margin = 2;
    
    for (let dy = -margin; dy < height + margin; dy++) {
      for (let dx = -margin; dx < width + margin; dx++) {
        const tx = x + dx;
        const ty = y + dy;
        
        if (tx < 0 || tx >= this.width || ty < 0 || ty >= this.height) {
          return false;
        }
        
        if (collision[ty][tx] !== 0) {
          return false;
        }
      }
    }
    
    return true;
  }
  
  /**
   * 標記建築物區域
   */
  markBuildingArea(building, terrain, collision) {
    const doorX = building.x + Math.floor(building.width / 2);
    const doorY = building.y + building.height - 1;
    
    for (let dy = 0; dy < building.height; dy++) {
      for (let dx = 0; dx < building.width; dx++) {
        const x = building.x + dx;
        const y = building.y + dy;
        
        terrain[y][x] = 3; // 地板
        
        // 牆壁（邊緣）
        const isEdge = dx === 0 || dx === building.width - 1 || 
                       dy === 0 || dy === building.height - 1;
        
        // 門的位置可通行
        const isDoor = (x === doorX && y === doorY);
        
        if (isEdge && !isDoor) {
          collision[y][x] = 1; // 不可通行
        }
      }
    }
    
    // 門記錄
    building.doorX = doorX;
    building.doorY = doorY;
  }
  
  /**
   * 生成河流
   */
  generateRiver(terrain, collision) {
    // 河流從地圖上方流向下方，有蜿蜒效果
    const riverWidth = 2;
    let riverX = Math.floor(this.width * 0.7); // 河流起始 X 位置（偏右）
    
    for (let y = 0; y < this.height; y++) {
      // 蜿蜒效果
      if (y % 8 === 0) {
        const direction = Math.random() > 0.5 ? 1 : -1;
        riverX += direction * 2;
        // 確保河流不會太靠近邊緣或中心
        riverX = Math.max(this.width * 0.55, Math.min(this.width * 0.85, riverX));
      }
      
      // 繪製河流寬度
      for (let dx = 0; dx < riverWidth; dx++) {
        const x = Math.floor(riverX) + dx;
        if (x >= 0 && x < this.width) {
          terrain[y][x] = 2; // 水
          collision[y][x] = 1; // 不可通行
        }
      }
      
      // 河岸（淺色泥土）- 可選，暫時不加
    }
    
    // 記錄河流位置供橋樑使用
    this.riverX = Math.floor(riverX);
    this.riverWidth = riverWidth;
  }
  
  /**
   * 生成橋樑
   */
  generateBridges(terrain, collision, objects) {
    if (!this.riverX) return;
    
    // 在主幹道位置建橋
    const centerY = Math.floor(this.height / 2);
    const bridgeYPositions = [centerY, centerY + 1]; // 橋的 Y 範圍
    
    for (const y of bridgeYPositions) {
      for (let dx = -1; dx <= this.riverWidth; dx++) {
        const x = this.riverX + dx;
        if (x >= 0 && x < this.width && y >= 0 && y < this.height) {
          terrain[y][x] = 9; // 新地形類型：橋
          collision[y][x] = 0; // 可通行
        }
      }
    }
    
    // 添加橋的裝飾物件
    objects.push({
      id: 'bridge_1',
      type: 'bridge_railing',
      name: '橋欄杆',
      x: this.riverX - 1,
      y: centerY - 1
    });
  }
  
  /**
   * 生成道路
   */
  generateRoads(buildings, terrain) {
    // 簡單實作：連接所有建築物的門到地圖中心
    const centerX = Math.floor(this.width / 2);
    const centerY = Math.floor(this.height / 2);
    
    // 主幹道（水平）
    for (let x = 10; x < this.width - 10; x++) {
      if (terrain[centerY][x] === 0) {
        terrain[centerY][x] = 1;
        terrain[centerY + 1][x] = 1;
      }
    }
    
    // 連接每棟建築到主幹道
    for (const building of buildings) {
      const doorX = building.doorX;
      const doorY = building.doorY + 1; // 門外一格
      
      // 垂直連接到主幹道
      const startY = Math.min(doorY, centerY);
      const endY = Math.max(doorY, centerY);
      
      for (let y = startY; y <= endY; y++) {
        if (terrain[y][doorX] === 0) {
          terrain[y][doorX] = 1;
        }
      }
    }
  }
  
  /**
   * 放置水井
   */
  placeWell(objects, buildings, terrain, collision) {
    const centerX = Math.floor(this.width / 2);
    const centerY = Math.floor(this.height / 2);
    
    // 在廣場中央放置水井
    objects.push({
      id: 'well_1',
      type: 'well',
      name: '水井',
      x: centerX - 1,
      y: centerY - 2,
      actions: [
        { id: 'draw_water', name: '打水', duration: 3000 },
        { id: 'rest', name: '休息', duration: 5000 }
      ],
      socialHotspot: true
    });
    
    collision[centerY - 2][centerX - 1] = 1;
  }
  
  /**
   * 放置裝飾物
   */
  placeDecorations(objects, terrain, collision) {
    // 在地圖邊緣放置樹木
    for (let i = 0; i < 40; i++) {
      const edge = Math.floor(Math.random() * 4);
      let x, y;
      
      switch (edge) {
        case 0: // 上
          x = Math.floor(Math.random() * (this.width - 4)) + 2;
          y = Math.floor(Math.random() * 6) + 1;
          break;
        case 1: // 下
          x = Math.floor(Math.random() * (this.width - 4)) + 2;
          y = this.height - Math.floor(Math.random() * 6) - 2;
          break;
        case 2: // 左
          x = Math.floor(Math.random() * 6) + 1;
          y = Math.floor(Math.random() * (this.height - 4)) + 2;
          break;
        case 3: // 右
          x = this.width - Math.floor(Math.random() * 6) - 2;
          y = Math.floor(Math.random() * (this.height - 4)) + 2;
          break;
      }
      
      if (collision[y][x] === 0 && terrain[y][x] === 0) {
        objects.push({
          id: `tree_${i}`,
          type: 'tree',
          name: '樹',
          x: x,
          y: y
        });
        collision[y][x] = 1;
      }
    }
    
    // 放置小石頭（不影響碰撞）
    for (let i = 0; i < 25; i++) {
      const x = Math.floor(Math.random() * (this.width - 4)) + 2;
      const y = Math.floor(Math.random() * (this.height - 4)) + 2;
      
      if (terrain[y][x] === 0) { // 只在草地上
        objects.push({
          id: `rock_${i}`,
          type: 'rock',
          name: '石頭',
          x: x,
          y: y
        });
      }
    }
    
    // 放置灌木
    for (let i = 0; i < 15; i++) {
      const x = Math.floor(Math.random() * (this.width - 4)) + 2;
      const y = Math.floor(Math.random() * (this.height - 4)) + 2;
      
      if (collision[y][x] === 0 && terrain[y][x] === 0) {
        objects.push({
          id: `bush_${i}`,
          type: 'bush',
          name: '灌木',
          x: x,
          y: y
        });
        collision[y][x] = 1; // 灌木有碰撞
      }
    }
    
    // 放置高草（不影響碰撞）
    for (let i = 0; i < 20; i++) {
      const x = Math.floor(Math.random() * (this.width - 4)) + 2;
      const y = Math.floor(Math.random() * (this.height - 4)) + 2;
      
      if (terrain[y][x] === 0) {
        objects.push({
          id: `tallgrass_${i}`,
          type: 'tallgrass',
          name: '草叢',
          x: x,
          y: y
        });
      }
    }
    
    // 放置樹樁（少量）
    for (let i = 0; i < 5; i++) {
      const x = Math.floor(Math.random() * (this.width - 6)) + 3;
      const y = Math.floor(Math.random() * (this.height - 6)) + 3;
      
      if (collision[y][x] === 0 && terrain[y][x] === 0) {
        objects.push({
          id: `stump_${i}`,
          type: 'stump',
          name: '樹樁',
          x: x,
          y: y
        });
        collision[y][x] = 1;
      }
    }
    
    // 放置蘑菇（少量，通常在樹旁）
    for (let i = 0; i < 8; i++) {
      const x = Math.floor(Math.random() * (this.width - 4)) + 2;
      const y = Math.floor(Math.random() * (this.height - 4)) + 2;
      
      if (terrain[y][x] === 0) {
        objects.push({
          id: `mushroom_${i}`,
          type: 'mushroom',
          name: '蘑菇',
          x: x,
          y: y
        });
      }
    }
  }
  
  /**
   * 在建築物內放置物件
   */
  placeBuildingObjects(buildings, objects) {
    for (const building of buildings) {
      const innerX = building.x + 1;
      const innerY = building.y + 1;
      const innerW = building.width - 2;
      const innerH = building.height - 2;
      
      switch (building.type) {
        case 'tavern':
          // 吧台
          objects.push({
            id: `${building.id}_bar`,
            type: 'table',
            name: '吧台',
            x: innerX + 1,
            y: innerY,
            buildingId: building.id,
            actions: [
              { id: 'buy_drink', name: '買酒 (5金幣)', duration: 3000, cost: 5 },
              { id: 'chat_bartender', name: '與酒保聊天', duration: 5000 }
            ]
          });
          // 桌椅
          objects.push({
            id: `${building.id}_table`,
            type: 'table',
            name: '酒桌',
            x: innerX + innerW - 2,
            y: innerY + 1,
            buildingId: building.id,
            actions: [
              { id: 'sit', name: '坐下休息', duration: 5000 }
            ]
          });
          break;
          
        case 'church':
          // 祭壇
          objects.push({
            id: `${building.id}_altar`,
            type: 'table',
            name: '祭壇',
            x: innerX + Math.floor(innerW / 2),
            y: innerY,
            buildingId: building.id,
            actions: [
              { id: 'pray', name: '祈禱', duration: 8000 }
            ]
          });
          break;
          
        case 'house':
          // 床
          objects.push({
            id: `${building.id}_bed`,
            type: 'bed',
            name: '床',
            x: innerX,
            y: innerY,
            buildingId: building.id,
            actions: [
              { id: 'sleep', name: '睡覺', duration: 10000 }
            ]
          });
          break;
          
        case 'blacksmith':
          // 鐵砧
          objects.push({
            id: `${building.id}_anvil`,
            type: 'table',
            name: '鐵砧',
            x: innerX + 1,
            y: innerY,
            buildingId: building.id,
            actions: [
              { id: 'work', name: '工作', duration: 10000 }
            ]
          });
          break;
      }
    }
  }
}
