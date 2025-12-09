/**
 * 渲染器 - 處理所有遊戲畫面繪製
 */

export class Renderer {
  constructor(ctx, camera, tileSize) {
    this.ctx = ctx;
    this.camera = camera;
    this.tileSize = tileSize;
    
    // 地形顏色
    this.terrainColors = {
      grass: '#4a7c34',
      grass_dark: '#3d6b2a',
      road: '#8b7355',
      road_light: '#9c8465',
      water: '#3498db',
      water_dark: '#2980b9',
      floor: '#8b7355',
      wall: '#5d4e37',
      farmland: '#8b6914',       // 4 - 農田
      farmland_dark: '#7a5c10',
      mine: '#6b6b6b',           // 5 - 礦場（石頭地面）
      mine_dark: '#5a5a5a',
      lumber: '#5d4e37',         // 6 - 伐木場（森林地面）
      lumber_dark: '#4d3e27',
      pasture: '#6b9c4a',        // 7 - 牧場（草地）
      pasture_dark: '#5a8b3a'
    };
    
    // 建築物顏色（13 種職業建築）
    this.buildingColors = {
      // 食物鏈
      farm: { wall: '#9c8b6e', roof: '#8b7355' },           // 農田
      mill: { wall: '#c4a574', roof: '#8b6914' },           // 磨坊
      butcher_shop: { wall: '#a05050', roof: '#8b3030' },   // 肉舖
      bakery: { wall: '#deb887', roof: '#d2691e' },         // 麵包店
      
      // 器具鏈
      mine: { wall: '#6b6b6b', roof: '#4a4a4a' },           // 礦場
      lumber_camp: { wall: '#5d4e37', roof: '#4d3e27' },    // 伐木場
      blacksmith: { wall: '#4a4a4a', roof: '#2f2f2f' },     // 鐵匠舖
      carpentry: { wall: '#8b7355', roof: '#6b5335' },      // 木工坊
      
      // 服飾鏈
      pasture: { wall: '#6b9c4a', roof: '#5a8b3a' },        // 牧場
      weaver_shop: { wall: '#9c8b9c', roof: '#7b6b7b' },    // 織坊
      tannery: { wall: '#8b6b4a', roof: '#6b4b2a' },        // 皮革坊
      tailor_shop: { wall: '#b08080', roof: '#906060' },    // 裁縫店
      
      // 特殊
      market: { wall: '#deb887', roof: '#cd853f' },         // 市集
      
      // 其他
      house: { wall: '#c4a574', roof: '#8b4513' },          // 民宅
      well: { wall: '#696969' }
    };
  }
  
  /**
   * 渲染地圖
   */
  renderMap(map) {
    // 簡單方案：渲染整個地圖（讓 canvas transform 處理縮放）
    const startTileX = 0;
    const startTileY = 0;
    const tilesX = map.width;
    const tilesY = map.height;
    
    // 渲染地面
    for (let y = startTileY; y < startTileY + tilesY; y++) {
      for (let x = startTileX; x < startTileX + tilesX; x++) {
        if (x < 0 || x >= map.width || y < 0 || y >= map.height) continue;
        
        const terrain = map.getTerrain(x, y);
        this.renderTile(x, y, terrain);
      }
    }
    
    // 渲染建築物底部
    for (const building of map.buildings) {
      this.renderBuilding(building);
    }
    
    // 渲染物件
    for (const obj of map.objects) {
      this.renderObject(obj);
    }
    
    // 渲染地上物品
    if (map.worldItems) {
      for (const item of map.worldItems) {
        this.renderWorldItem(item);
      }
    }
  }
  
  /**
   * 渲染單一格子
   */
  renderTile(tileX, tileY, terrain) {
    const screenX = tileX * this.tileSize - this.camera.x + this.camera.offsetX;
    const screenY = tileY * this.tileSize - this.camera.y + this.camera.offsetY;
    
    // 根據地形類型選擇顏色
    let color = this.terrainColors.grass;
    
    switch (terrain) {
      case 0: // 草地
        // 棋盤格紋理
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.grass 
          : this.terrainColors.grass_dark;
        break;
      case 1: // 道路
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.road 
          : this.terrainColors.road_light;
        break;
      case 2: // 水
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.water 
          : this.terrainColors.water_dark;
        break;
      case 3: // 地板
        color = this.terrainColors.floor;
        break;
      case 4: // 農田
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.farmland 
          : this.terrainColors.farmland_dark;
        break;
      case 5: // 礦場（石頭地面）
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.mine 
          : this.terrainColors.mine_dark;
        break;
      case 6: // 伐木場（森林地面）
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.lumber 
          : this.terrainColors.lumber_dark;
        break;
      case 7: // 牧場（草地）
        color = (tileX + tileY) % 2 === 0 
          ? this.terrainColors.pasture 
          : this.terrainColors.pasture_dark;
        break;
    }
    
    this.ctx.fillStyle = color;
    this.ctx.fillRect(screenX, screenY, this.tileSize, this.tileSize);
  }
  
  /**
   * 渲染建築物
   */
  renderBuilding(building) {
    const screenX = building.x * this.tileSize - this.camera.x + this.camera.offsetX;
    const screenY = building.y * this.tileSize - this.camera.y + this.camera.offsetY;
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    
    // 開放式建築（戶外工作場所）不畫牆壁
    const openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture'];
    if (openBuildings.includes(building.type)) {
      // 只顯示名稱
      this.ctx.fillStyle = '#fff';
      this.ctx.font = '10px sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(building.name, screenX + width / 2, screenY - 4);
      return;
    }
    
    const colors = this.buildingColors[building.type] || this.buildingColors.house;
    
    // 建築物地板
    this.ctx.fillStyle = this.terrainColors.floor;
    this.ctx.fillRect(screenX, screenY, width, height);
    
    // 牆壁
    this.ctx.fillStyle = colors.wall;
    
    // 上牆
    this.ctx.fillRect(screenX, screenY, width, this.tileSize);
    // 下牆（留門）
    const doorX = screenX + Math.floor(width / 2) - this.tileSize / 2;
    this.ctx.fillRect(screenX, screenY + height - this.tileSize, width, this.tileSize);
    // 門
    this.ctx.fillStyle = '#4a3520';
    this.ctx.fillRect(doorX, screenY + height - this.tileSize, this.tileSize, this.tileSize);
    
    // 左右牆
    this.ctx.fillStyle = colors.wall;
    this.ctx.fillRect(screenX, screenY, this.tileSize, height);
    this.ctx.fillRect(screenX + width - this.tileSize, screenY, this.tileSize, height);
  }
  
  /**
   * 渲染物件
   */
  renderObject(obj) {
    const screenX = obj.x * this.tileSize - this.camera.x + this.camera.offsetX;
    const screenY = obj.y * this.tileSize - this.camera.y + this.camera.offsetY;
    const size = this.tileSize;
    
    this.ctx.fillStyle = obj.color || '#8b4513';
    
    switch (obj.type) {
      case 'well':
        // 水井 - 圓形
        this.ctx.beginPath();
        this.ctx.arc(screenX + size / 2, screenY + size / 2, size / 2, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = '#3498db';
        this.ctx.beginPath();
        this.ctx.arc(screenX + size / 2, screenY + size / 2, size / 3, 0, Math.PI * 2);
        this.ctx.fill();
        break;
        
      case 'tree':
        // 樹 - 樹幹 + 樹冠
        this.ctx.fillStyle = '#5d4037';
        this.ctx.fillRect(screenX + size * 0.35, screenY + size * 0.5, size * 0.3, size * 0.5);
        this.ctx.fillStyle = '#2e7d32';
        this.ctx.beginPath();
        this.ctx.arc(screenX + size / 2, screenY + size * 0.4, size * 0.45, 0, Math.PI * 2);
        this.ctx.fill();
        break;
        
      case 'table':
        this.ctx.fillStyle = '#8d6e63';
        this.ctx.fillRect(screenX + 2, screenY + 2, size - 4, size - 4);
        break;
        
      case 'bed':
        this.ctx.fillStyle = '#795548';
        this.ctx.fillRect(screenX + 1, screenY + 1, size - 2, size - 2);
        this.ctx.fillStyle = '#bcaaa4';
        this.ctx.fillRect(screenX + 2, screenY + 2, size - 4, size / 2);
        break;
        
      case 'chair':
        this.ctx.fillStyle = '#6d4c41';
        this.ctx.fillRect(screenX + 3, screenY + 3, size - 6, size - 6);
        break;
        
      default:
        this.ctx.fillRect(screenX + 2, screenY + 2, size - 4, size - 4);
    }
  }
  
  /**
   * 渲染地上物品
   */
  renderWorldItem(item) {
    const screenX = item.x * this.tileSize - this.camera.x + this.camera.offsetX;
    const screenY = item.y * this.tileSize - this.camera.y + this.camera.offsetY;
    const size = this.tileSize;
    
    // 物品圖示對應表
    const itemIcons = {
      'hoe': '⛏️', 'pickaxe': '⛏️', 'axe': '🪓', 'shears': '✂️',
      'cleaver': '🔪', 'hammer': '🔨', 'saw': '🪚', 'scraper': '🔪',
      'grain': '🌾', 'livestock': '🐄', 'ore': '🪨', 'wood': '🪵',
      'wool': '🧶', 'hide': '🐑', 'flour': '🌫️', 'meat_raw': '🥩',
      'iron': '🔩', 'plank': '📏', 'cloth': '🧵', 'leather': '🟤',
      'bread': '🍞', 'meat': '🍖', 'clothes': '👕', 'furniture': '🪑'
    };
    
    const icon = itemIcons[item.item_id] || '📦';
    
    // 繪製背景
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.beginPath();
    this.ctx.roundRect(screenX + 2, screenY + 2, size - 4, size - 4, 4);
    this.ctx.fill();
    
    // 繪製物品圖示
    this.ctx.font = `${size * 0.6}px sans-serif`;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(icon, screenX + size / 2, screenY + size / 2 - 2);
    
    // 繪製數量（如果大於 1）
    if (item.quantity > 1) {
      this.ctx.font = 'bold 10px sans-serif';
      this.ctx.fillStyle = '#fff';
      this.ctx.textAlign = 'right';
      this.ctx.fillText(`${item.quantity}`, screenX + size - 4, screenY + size - 4);
    }
    
    // 如果有擁有者，繪製小標記
    if (item.owner_id) {
      this.ctx.fillStyle = '#ffd700';
      this.ctx.beginPath();
      this.ctx.arc(screenX + size - 6, screenY + 6, 3, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }
  
  /**
   * 渲染村民
   */
  renderVillagers(villagers, selectedVillager = null) {
    // 按 Y 座標排序（下方的後渲染，遮擋上方的）
    const sorted = [...villagers].sort((a, b) => a.y - b.y);
    
    for (const villager of sorted) {
      const isSelected = selectedVillager && selectedVillager.id === villager.id;
      this.renderVillager(villager, isSelected);
    }
  }
  
  /**
   * 渲染選中村民的路徑
   */
  renderVillagerPath(villager) {
    if (!villager.moveTarget) return;
    
    const [targetX, targetY] = villager.moveTarget;
    const tileSize = this.tileSize;
    
    // 當前位置
    const startX = villager.x * tileSize - this.camera.x + this.camera.offsetX;
    const startY = villager.y * tileSize - this.camera.y + this.camera.offsetY;
    
    // 目標位置
    const endX = targetX * tileSize - this.camera.x + this.camera.offsetX;
    const endY = targetY * tileSize - this.camera.y + this.camera.offsetY;
    
    // 畫虛線路徑
    this.ctx.save();
    this.ctx.setLineDash([4, 4]);
    this.ctx.strokeStyle = 'rgba(255, 255, 100, 0.6)';
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.moveTo(startX + tileSize / 2, startY + tileSize / 2);
    this.ctx.lineTo(endX + tileSize / 2, endY + tileSize / 2);
    this.ctx.stroke();
    this.ctx.restore();
    
    // 畫目標點
    this.ctx.fillStyle = 'rgba(255, 255, 100, 0.8)';
    this.ctx.beginPath();
    this.ctx.arc(endX + tileSize / 2, endY + tileSize / 2, 6, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 目標點外圈
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.arc(endX + tileSize / 2, endY + tileSize / 2, 8, 0, Math.PI * 2);
    this.ctx.stroke();
  }
  
  /**
   * 渲染單一村民
   */
  renderVillager(villager, isSelected = false) {
    const screenX = villager.x * this.tileSize - this.camera.x + this.camera.offsetX;
    const screenY = villager.y * this.tileSize - this.camera.y + this.camera.offsetY;
    const size = this.tileSize;
    
    // 選中效果：發光圈
    if (isSelected) {
      this.ctx.fillStyle = 'rgba(255, 255, 100, 0.3)';
      this.ctx.beginPath();
      this.ctx.arc(screenX + size / 2, screenY + size / 2, size * 0.8, 0, Math.PI * 2);
      this.ctx.fill();
      
      this.ctx.strokeStyle = 'rgba(255, 255, 100, 0.8)';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.arc(screenX + size / 2, screenY + size / 2, size * 0.8, 0, Math.PI * 2);
      this.ctx.stroke();
    }
    
    // 身體
    this.ctx.fillStyle = villager.color || '#e0c080';
    this.ctx.fillRect(screenX + 3, screenY + 4, size - 6, size - 4);
    
    // 頭
    this.ctx.fillStyle = '#ffd5b4';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + 4, 4, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 永遠顯示名字（在身體下方）
    this.ctx.fillStyle = isSelected ? '#ffff66' : '#fff';
    this.ctx.font = isSelected ? 'bold 9px sans-serif' : '8px sans-serif';
    this.ctx.textAlign = 'center';
    // 添加陰影讓文字更清晰
    this.ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
    this.ctx.shadowBlur = 2;
    this.ctx.shadowOffsetX = 1;
    this.ctx.shadowOffsetY = 1;
    this.ctx.fillText(villager.name, screenX + size / 2, screenY + size + 8);
    // 重置陰影
    this.ctx.shadowColor = 'transparent';
    this.ctx.shadowBlur = 0;
    this.ctx.shadowOffsetX = 0;
    this.ctx.shadowOffsetY = 0;
    
    // 對話泡泡
    if (villager.bubble) {
      this.renderBubble(screenX + size / 2, screenY - 8, villager.bubble);
    }
  }
  
  /**
   * 渲染對話泡泡（支援多行和自動換行）
   */
  renderBubble(x, y, bubble) {
    const text = bubble.text || '';
    const type = bubble.type || 'speech'; // speech, thought, action
    
    if (!text) return;
    
    const fontSize = 12;
    this.ctx.font = `bold ${fontSize}px sans-serif`;
    const maxWidth = 180; // 最大文字寬度
    const padding = 10;
    const lineHeight = fontSize + 6;
    
    // 自動換行處理
    const wrapText = (text, maxWidth) => {
      const result = [];
      // 先按換行符分割
      const paragraphs = text.split('\n');
      
      for (const paragraph of paragraphs) {
        if (this.ctx.measureText(paragraph).width <= maxWidth) {
          result.push(paragraph);
        } else {
          // 需要換行
          let line = '';
          for (const char of paragraph) {
            const testLine = line + char;
            if (this.ctx.measureText(testLine).width > maxWidth) {
              if (line) result.push(line);
              line = char;
            } else {
              line = testLine;
            }
          }
          if (line) result.push(line);
        }
      }
      return result;
    };
    
    const lines = wrapText(text, maxWidth);
    
    // 計算泡泡大小
    const lineWidths = lines.map(line => this.ctx.measureText(line).width);
    const maxLineWidth = Math.max(...lineWidths);
    
    const bubbleWidth = maxLineWidth + padding * 2;
    const bubbleHeight = lines.length * lineHeight + padding * 2;
    const bubbleX = x - bubbleWidth / 2;
    const bubbleY = y - bubbleHeight - 12;
    
    // 泡泡背景
    this.ctx.fillStyle = type === 'thought' ? 'rgba(200, 200, 255, 0.95)' : 
                         type === 'action' ? 'rgba(255, 240, 200, 0.95)' : 
                         'rgba(255, 255, 255, 0.95)';
    
    // 圓角矩形
    this.roundRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight, 6);
    this.ctx.fill();
    
    // 泡泡邊框
    this.ctx.strokeStyle = type === 'thought' ? '#8888cc' : 
                           type === 'action' ? '#ccaa55' : 
                           '#888';
    this.ctx.lineWidth = 2;
    this.roundRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight, 6);
    this.ctx.stroke();
    
    // 小三角（指向角色）
    if (type === 'speech') {
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      this.ctx.beginPath();
      this.ctx.moveTo(x - 6, bubbleY + bubbleHeight);
      this.ctx.lineTo(x, bubbleY + bubbleHeight + 8);
      this.ctx.lineTo(x + 6, bubbleY + bubbleHeight);
      this.ctx.closePath();
      this.ctx.fill();
      this.ctx.stroke();
    } else if (type === 'thought') {
      // 思考泡泡用小圓點
      this.ctx.fillStyle = 'rgba(200, 200, 255, 0.95)';
      this.ctx.beginPath();
      this.ctx.arc(x, bubbleY + bubbleHeight + 5, 4, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.beginPath();
      this.ctx.arc(x - 3, bubbleY + bubbleHeight + 12, 3, 0, Math.PI * 2);
      this.ctx.fill();
    }
    
    // 繪製多行文字
    this.ctx.fillStyle = '#333';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'top';
    
    for (let i = 0; i < lines.length; i++) {
      const lineY = bubbleY + padding + i * lineHeight;
      this.ctx.fillText(lines[i], x, lineY);
    }
  }
  
  /**
   * 繪製圓角矩形
   */
  roundRect(x, y, width, height, radius) {
    this.ctx.beginPath();
    this.ctx.moveTo(x + radius, y);
    this.ctx.lineTo(x + width - radius, y);
    this.ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    this.ctx.lineTo(x + width, y + height - radius);
    this.ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    this.ctx.lineTo(x + radius, y + height);
    this.ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    this.ctx.lineTo(x, y + radius);
    this.ctx.quadraticCurveTo(x, y, x + radius, y);
    this.ctx.closePath();
  }
  
  /**
   * 渲染玩家
   */
  renderPlayer(player) {
    const screenX = player.x * this.tileSize - this.camera.x + this.camera.offsetX;
    const screenY = player.y * this.tileSize - this.camera.y + this.camera.offsetY;
    const size = this.tileSize;
    
    // 玩家高亮邊框
    this.ctx.strokeStyle = '#ffd700';
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(screenX + 1, screenY + 1, size - 2, size - 2);
    
    // 身體
    this.ctx.fillStyle = '#4a90d9';
    this.ctx.fillRect(screenX + 3, screenY + 4, size - 6, size - 4);
    
    // 頭
    this.ctx.fillStyle = '#ffd5b4';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + 4, 4, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 名字
    this.ctx.fillStyle = '#ffd700';
    this.ctx.font = 'bold 9px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(player.name, screenX + size / 2, screenY - 2);
  }
  
  /**
   * 渲染建築物頂部（遮擋效果）
   */
  renderBuildingTops(map) {
    // 開放式建築不畫屋頂
    const openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture'];
    
    for (const building of map.buildings) {
      // 跳過戶外工作場所
      if (openBuildings.includes(building.type)) continue;
      
      const colors = this.buildingColors[building.type] || this.buildingColors.house;
      const screenX = building.x * this.tileSize - this.camera.x + this.camera.offsetX;
      const screenY = building.y * this.tileSize - this.camera.y + this.camera.offsetY;
      const width = building.width * this.tileSize;
      
      if (colors.roof) {
        // 屋頂
        this.ctx.fillStyle = colors.roof;
        this.ctx.beginPath();
        this.ctx.moveTo(screenX - 4, screenY);
        this.ctx.lineTo(screenX + width / 2, screenY - 16);
        this.ctx.lineTo(screenX + width + 4, screenY);
        this.ctx.closePath();
        this.ctx.fill();
        
        // 屋頂中央顯示建築名稱（民宅除外）
        if (building.type !== 'house') {
          this.ctx.fillStyle = '#fff';
          this.ctx.font = 'bold 10px sans-serif';
          this.ctx.textAlign = 'center';
          this.ctx.textBaseline = 'middle';
          this.ctx.fillText(building.name, screenX + width / 2, screenY - 6);
        }
      }
    }
  }
}
