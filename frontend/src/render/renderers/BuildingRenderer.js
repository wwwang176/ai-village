/**
 * 建築渲染器 - 2.5D 像素風格
 */
import { BaseRenderer } from './BaseRenderer.js';

export class BuildingRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 建築物顏色（增加細節色）
    this.colors = {
      // 食物鏈
      farm: { wall: '#9c8b6e', wallDark: '#8c7b5e', roof: '#8b7355', roofDark: '#7b6345' },
      mill: { wall: '#c4a574', wallDark: '#b49564', roof: '#8b6914', roofDark: '#7b5904' },
      butcher_shop: { wall: '#a05050', wallDark: '#903040', roof: '#8b3030', roofDark: '#7b2020' },
      bakery: { wall: '#deb887', wallDark: '#cea877', roof: '#d2691e', roofDark: '#c2590e' },
      
      // 器具鏈
      mine: { wall: '#6b6b6b', wallDark: '#5b5b5b', roof: '#4a4a4a', roofDark: '#3a3a3a' },
      lumber_camp: { wall: '#5d4e37', wallDark: '#4d3e27', roof: '#4d3e27', roofDark: '#3d2e17' },
      blacksmith: { wall: '#4a4a4a', wallDark: '#3a3a3a', roof: '#2f2f2f', roofDark: '#1f1f1f' },
      carpentry: { wall: '#8b7355', wallDark: '#7b6345', roof: '#6b5335', roofDark: '#5b4325' },
      
      // 服飾鏈
      pasture: { wall: '#6b9c4a', wallDark: '#5b8c3a', roof: '#5a8b3a', roofDark: '#4a7b2a' },
      weaver_shop: { wall: '#9c8b9c', wallDark: '#8c7b8c', roof: '#7b6b7b', roofDark: '#6b5b6b' },
      tannery: { wall: '#8b6b4a', wallDark: '#7b5b3a', roof: '#6b4b2a', roofDark: '#5b3b1a' },
      tailor_shop: { wall: '#b08080', wallDark: '#a07070', roof: '#906060', roofDark: '#805050' },
      
      // 特殊
      plaza: { wall: '#deb887', wallDark: '#cea877', roof: '#cd853f', roofDark: '#bd752f' },
      tavern: { wall: '#8b7355', wallDark: '#7b6345', roof: '#6b4423', roofDark: '#5b3413' },
      church: { wall: '#d4c4a8', wallDark: '#c4b498', roof: '#8b8b8b', roofDark: '#7b7b7b' },
      
      // 其他
      house: { wall: '#c4a574', wallDark: '#b49564', roof: '#8b4513', roofDark: '#7b3503' },
      well: { wall: '#696969', wallDark: '#595959' }
    };
    
    // 門窗顏色
    this.doorColor = '#4a3520';
    this.doorFrameColor = '#3a2510';
    this.windowColor = '#87ceeb';
    this.windowFrameColor = '#5d4037';
    
    // 開放式建築（不畫牆壁和屋頂）
    this.openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture', 'plaza'];
    
    // 2.5D 設定
    this.wallHeight = 24; // 正面牆壁高度（像素）
    this.roofHeight = 20; // 屋頂高度（像素）
  }
  
  /**
   * 渲染所有建築物底部（只畫地板）
   */
  render(buildings) {
    for (const building of buildings) {
      this.renderBuildingFloor(building);
    }
  }
  
  /**
   * 渲染建築物頂部（2.5D：正面牆壁 + 屋頂）
   * @param {Array} buildings - 建築物列表
   * @param {Array} villagersInBuildings - 在建築內的村民 ID 列表
   */
  renderTops(buildings, villagersInBuildings = []) {
    // 按 Y 座標排序（Y 小的先畫，Y 大的後畫覆蓋）
    const sortedBuildings = [...buildings].sort((a, b) => a.y - b.y);
    
    // 漸變速度（每幀變化量）
    const fadeSpeed = 0.08;
    
    for (const building of sortedBuildings) {
      // 跳過戶外工作場所
      if (this.openBuildings.includes(building.type)) continue;
      
      // 檢查是否有村民在此建築內
      const hasOccupants = villagersInBuildings.some(v => v.buildingId === building.id);
      
      // 初始化 currentOpacity（1.0 = 外部完全顯示，0.0 = 內部完全顯示）
      if (building.currentOpacity === undefined) {
        building.currentOpacity = 1.0;
      }
      
      // 計算目標透明度
      const targetOpacity = hasOccupants ? 0.0 : 1.0;
      
      // 漸變更新 currentOpacity
      if (building.currentOpacity < targetOpacity) {
        building.currentOpacity = Math.min(building.currentOpacity + fadeSpeed, targetOpacity);
      } else if (building.currentOpacity > targetOpacity) {
        building.currentOpacity = Math.max(building.currentOpacity - fadeSpeed, targetOpacity);
      }
      
      const opacity = building.currentOpacity;
      
      // 內部北牆（透明度 = 1 - opacity）
      if (opacity < 1.0) {
        this.renderInteriorNorthWall(building, 1.0 - opacity);
      }
      
      // 外部建築（透明度 = opacity）
      if (opacity > 0.0) {
        this.renderBuilding2_5D(building, opacity);
      }
    }
  }
  
  /**
   * 渲染北邊內部牆面（村民在建築內時顯示）
   * @param {Object} building - 建築物
   * @param {number} opacity - 透明度 (0.0 ~ 1.0)
   */
  renderInteriorNorthWall(building, opacity = 1.0) {
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    const ts = this.tileSize;
    const colors = this.colors[building.type] || this.colors.house;
    
    const wallHeight = this.wallHeight;
    const gableHeight = this.roofHeight;
    
    // 設置透明度
    this.ctx.globalAlpha = opacity;
    
    // 北邊牆壁位置（建築物地板北端，向上延伸）
    const wallBottom = screenY; // 牆壁底部對齊地板北端
    const wallTop = wallBottom - wallHeight; // 牆壁頂部
    
    // 北邊牆壁主體（矩形部分）- 使用較暗的顏色表示內部
    this.ctx.fillStyle = colors.wallDark || colors.wall;
    this.ctx.fillRect(screenX, wallTop, width, wallHeight);
    
    // 山牆（三角形部分，在矩形牆壁上方）
    this.ctx.fillStyle = colors.wallDark || colors.wall;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX, wallTop);
    this.ctx.lineTo(screenX + width / 2, wallTop - gableHeight);
    this.ctx.lineTo(screenX + width, wallTop);
    this.ctx.closePath();
    this.ctx.fill();
    
    // 山牆邊框線
    this.ctx.strokeStyle = '#3a2a1a';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX, wallTop);
    this.ctx.lineTo(screenX + width / 2, wallTop - gableHeight);
    this.ctx.lineTo(screenX + width, wallTop);
    this.ctx.stroke();
    
    // 牆壁磚塊紋理
    this.ctx.fillStyle = '#3a2a1a';
    for (let row = 0; row < wallHeight; row += 8) {
      const offset = (row / 8) % 2 === 0 ? 0 : ts / 2;
      for (let i = offset; i < width; i += ts) {
        const lineWidth = Math.min(ts - 2, width - i);
        if (lineWidth > 0) {
          this.ctx.fillRect(screenX + i, wallTop + row + 7, lineWidth, 1);
        }
      }
    }
    
    // 牆壁底部陰影線
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.fillRect(screenX, wallBottom - 2, width, 2);
    
    // 窗戶（北邊內部牆面）
    if (building.width >= 5) {
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
      this.renderWindow(screenX + width - ts * 2, windowY);
    } else if (building.width >= 4) {
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
    }
    
    // 恢復透明度
    this.ctx.globalAlpha = 1.0;
  }
  
  /**
   * 渲染北邊內部牆面（不含矮牆，矮牆由 Y-sort 單獨處理）
   */
  renderInteriorNorthWallOnly(building) {
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    const ts = this.tileSize;
    const colors = this.colors[building.type] || this.colors.house;
    
    const wallHeight = this.wallHeight;
    const gableHeight = this.roofHeight;
    
    // 北邊牆壁位置（建築物地板北端，向上延伸）
    const wallBottom = screenY;
    const wallTop = wallBottom - wallHeight;
    
    // 北邊牆壁主體
    this.ctx.fillStyle = colors.wallDark || colors.wall;
    this.ctx.fillRect(screenX, wallTop, width, wallHeight);
    
    // 山牆
    this.ctx.fillStyle = colors.wallDark || colors.wall;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX, wallTop);
    this.ctx.lineTo(screenX + width / 2, wallTop - gableHeight);
    this.ctx.lineTo(screenX + width, wallTop);
    this.ctx.closePath();
    this.ctx.fill();
    
    // 山牆邊框線
    this.ctx.strokeStyle = '#3a2a1a';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX, wallTop);
    this.ctx.lineTo(screenX + width / 2, wallTop - gableHeight);
    this.ctx.lineTo(screenX + width, wallTop);
    this.ctx.stroke();
    
    // 牆壁磚塊紋理
    this.ctx.fillStyle = '#3a2a1a';
    for (let row = 0; row < wallHeight; row += 8) {
      const offset = (row / 8) % 2 === 0 ? 0 : ts / 2;
      for (let i = offset; i < width; i += ts) {
        const lineWidth = Math.min(ts - 2, width - i);
        if (lineWidth > 0) {
          this.ctx.fillRect(screenX + i, wallTop + row + 7, lineWidth, 1);
        }
      }
    }
    
    // 牆壁底部陰影線
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.fillRect(screenX, wallBottom - 2, width, 2);
    
    // 窗戶
    if (building.width >= 5) {
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
      this.renderWindow(screenX + width - ts * 2, windowY);
    } else if (building.width >= 4) {
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
    }
  }
  
  /**
   * 取得建築物內部矮牆位置列表（用於 Y-sort）
   */
  getLowWallPositions(building) {
    const positions = [];
    const doorX = building.x + Math.floor(building.width / 2);
    const doorY = building.y + building.height - 1;
    
    for (let y = building.y; y < building.y + building.height; y++) {
      for (let x = building.x; x < building.x + building.width; x++) {
        const isEdge = (
          x === building.x || 
          x === building.x + building.width - 1 ||
          y === building.y || 
          y === building.y + building.height - 1
        );
        
        if (!isEdge) continue;
        if (x === doorX && y === doorY) continue;
        
        const isNorthRow = (y === building.y);
        const isSouthRow = (y === building.y + building.height - 1);
        
        positions.push({
          x: x,
          y: y,
          building: building,
          isNorthRow: isNorthRow,
          isSouthRow: isSouthRow
        });
      }
    }
    
    return positions;
  }
  
  /**
   * 渲染單一矮牆（用於 Y-sort）
   * @param {Object} wallData - 矮牆資料
   * @param {number} opacity - 透明度 (0.0 ~ 1.0)
   */
  renderSingleLowWall(wallData, opacity = 1.0) {
    const { x, y, building, isNorthRow, isSouthRow } = wallData;
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const ts = this.tileSize;
    const lowWallHeight = 6;
    const colors = this.colors[building.type] || this.colors.house;
    const wallColor = colors.wallDark || '#6b5b4b';
    const wallColorDark = '#4b3b2b';
    
    // 設置透明度
    this.ctx.globalAlpha = opacity;
    
    const blockScreenX = screenX + (x - building.x) * ts;
    // 往北移動 lowWallHeight 像素，讓南面牆壁底部對齊格子底部
    const blockScreenY = screenY + (y - building.y) * ts - lowWallHeight;
    
    // 頂部（正方形）
    this.ctx.fillStyle = wallColor;
    this.ctx.fillRect(blockScreenX, blockScreenY, ts, ts);
    
    // 頂部邊框（畫在矩形內部）
    this.ctx.strokeStyle = wallColorDark;
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(blockScreenX + 0.5, blockScreenY + 0.5, ts - 1, ts - 1);
    
    // 南面牆壁（最南排 或 北端第一排）
    if (isSouthRow || isNorthRow) {
      const wallTop = blockScreenY + ts;
      this.ctx.fillStyle = wallColor;
      this.ctx.fillRect(blockScreenX, wallTop, ts, lowWallHeight);
      
      // 南面牆壁陰影
      this.ctx.fillStyle = wallColorDark;
      this.ctx.fillRect(blockScreenX, wallTop + lowWallHeight - 2, ts, 2);
      
      // 南面牆壁左右邊線
      this.ctx.fillRect(blockScreenX, wallTop, 1, lowWallHeight);
      this.ctx.fillRect(blockScreenX + ts - 1, wallTop, 1, lowWallHeight);
    }
    
    // 恢復透明度
    this.ctx.globalAlpha = 1.0;
  }
  
  /**
   * 渲染建築物地板
   */
  renderBuildingFloor(building) {
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    const ts = this.tileSize;
    
    // 開放式建築只顯示名稱
    if (this.openBuildings.includes(building.type)) {
      this.ctx.fillStyle = '#fff';
      this.ctx.font = '10px sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(building.name, screenX + width / 2, screenY - 4);
      return;
    }
    
    // 建築物地板
    this.ctx.fillStyle = '#8b7355';
    this.ctx.fillRect(screenX, screenY, width, height);
    
    // 地板紋理
    this.ctx.fillStyle = '#7b6345';
    for (let i = 0; i < width; i += ts) {
      for (let j = 0; j < height; j += ts) {
        if ((i + j) % (ts * 2) === 0) {
          this.ctx.fillRect(screenX + i + 2, screenY + j + 2, ts - 4, ts - 4);
        }
      }
    }
  }
  
  /**
   * 渲染 2.5D 建築物（正面牆壁 + 山牆 + 屋頂）
   */
  renderBuilding2_5D(building, opacity = 1.0) {
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    const ts = this.tileSize;
    const colors = this.colors[building.type] || this.colors.house;
    
    // 設置透明度
    this.ctx.globalAlpha = opacity;
    
    const wallHeight = this.wallHeight;
    const gableHeight = this.roofHeight; // 山牆三角形高度
    
    // === 正面牆壁（底部對齊地板南端，向上延伸） ===
    const wallBottom = screenY + height; // 牆壁底部對齊地板南端
    const wallTop = wallBottom - wallHeight; // 牆壁頂部
    
    // 正面牆壁主體（矩形部分）
    this.ctx.fillStyle = colors.wall;
    this.ctx.fillRect(screenX, wallTop, width, wallHeight);
    
    // 山牆（三角形部分，在矩形牆壁上方）
    this.ctx.fillStyle = colors.wall;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX, wallTop);
    this.ctx.lineTo(screenX + width / 2, wallTop - gableHeight);
    this.ctx.lineTo(screenX + width, wallTop);
    this.ctx.closePath();
    this.ctx.fill();
    
    // 山牆邊框線
    this.ctx.strokeStyle = colors.wallDark || '#5a4a3a';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX, wallTop);
    this.ctx.lineTo(screenX + width / 2, wallTop - gableHeight);
    this.ctx.lineTo(screenX + width, wallTop);
    this.ctx.stroke();
    
    // 牆壁磚塊紋理
    this.ctx.fillStyle = colors.wallDark || colors.wall;
    for (let row = 0; row < wallHeight; row += 8) {
      const offset = (row / 8) % 2 === 0 ? 0 : ts / 2;
      for (let i = offset; i < width; i += ts) {
        const lineWidth = Math.min(ts - 2, width - i);
        if (lineWidth > 0) {
          this.ctx.fillRect(screenX + i, wallTop + row + 7, lineWidth, 1);
        }
      }
    }
    
    // 正面牆壁陰影（底部）
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    this.ctx.fillRect(screenX, wallBottom - 3, width, 3);
    
    // 門和窗戶
    const doorWidth = ts;
    const doorHeight = wallHeight - 4;
    
    if (building.width >= 5) {
      // 雙窗戶：門在中央，窗戶在兩側
      const doorX = screenX + Math.floor(width / 2) - doorWidth / 2;
      this.renderDoor(doorX, wallTop + 2, doorWidth, doorHeight);
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
      this.renderWindow(screenX + width - ts * 2, windowY);
    } else if (building.width >= 4) {
      // 單窗戶：窗戶靠左，門靠右
      const doorX = screenX + width - ts * 1.5;
      this.renderDoor(doorX, wallTop + 2, doorWidth, doorHeight);
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts * 0.5, windowY);
    } else {
      // 小房子：只有門在中央
      const doorX = screenX + Math.floor(width / 2) - doorWidth / 2;
      this.renderDoor(doorX, wallTop + 2, doorWidth, doorHeight);
    }
    
    // === 屋頂（東西向雙坡） ===
    this.renderRoof2_5D(building, screenX, screenY, width, height, colors);
    
    // 恢復透明度
    this.ctx.globalAlpha = 1.0;
  }
  
  /**
   * 渲染 2.5D 屋頂（東西向雙坡屋頂）
   */
  renderRoof2_5D(building, screenX, screenY, width, height, colors) {
    const roofOverhang = 3; // 屋頂左右突出量
    const roofPeakHeight = this.roofHeight; // 屋脊高度
    const wallHeight = this.wallHeight;
    
    // 屋頂覆蓋在建築物上方（牆壁頂部以上）
    // 屋脊在中央（南北向），左右兩片斜面向東西傾斜
    
    // 屋頂覆蓋整個建築物地板區域（往北移動一格）
    const ts = this.tileSize;
    const roofTop = screenY - 2 - ts; // 屋頂北側（往北一格）
    const roofBottom = screenY + height - ts * 1.5; // 屋頂南側（往北縮，避免蓋過正面牆）
    const roofLeft = screenX - roofOverhang;
    const roofRight = screenX + width + roofOverhang;
    const roofCenterX = screenX + width / 2;
    
    // 左側屋頂斜面（較亮）
    this.ctx.fillStyle = colors.roof;
    this.ctx.beginPath();
    this.ctx.moveTo(roofLeft, roofTop);
    this.ctx.lineTo(roofCenterX, roofTop - roofPeakHeight);
    this.ctx.lineTo(roofCenterX, roofBottom - roofPeakHeight);
    this.ctx.lineTo(roofLeft, roofBottom);
    this.ctx.closePath();
    this.ctx.fill();
    
    // 右側屋頂斜面（較暗）
    this.ctx.fillStyle = colors.roofDark || colors.roof;
    this.ctx.beginPath();
    this.ctx.moveTo(roofCenterX, roofTop - roofPeakHeight);
    this.ctx.lineTo(roofRight, roofTop);
    this.ctx.lineTo(roofRight, roofBottom);
    this.ctx.lineTo(roofCenterX, roofBottom - roofPeakHeight);
    this.ctx.closePath();
    this.ctx.fill();
    
    // 屋頂瓦片紋理（左側）
    this.ctx.fillStyle = colors.roofDark || colors.roof;
    const roofLength = roofBottom - roofTop;
    for (let row = 0; row < roofLength; row += 6) {
      const y = roofTop + row;
      for (let col = 0; col < width / 2 + roofOverhang; col += 8) {
        if ((Math.floor(row / 6) + Math.floor(col / 8)) % 2 === 0) {
          const x = roofLeft + col;
          this.ctx.fillRect(x, y + (col / (width / 2 + roofOverhang)) * (-roofPeakHeight), 6, 2);
        }
      }
    }
    
    // 屋脊線（中央）
    this.ctx.strokeStyle = colors.roofDark || '#5a4a3a';
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.moveTo(roofCenterX, roofTop - roofPeakHeight);
    this.ctx.lineTo(roofCenterX, roofBottom - roofPeakHeight);
    this.ctx.stroke();
    
    // 屋頂邊緣線（只畫左右斜邊，不畫水平邊）
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    // 北側（上方）V 形
    this.ctx.moveTo(roofLeft, roofTop);
    this.ctx.lineTo(roofCenterX, roofTop - roofPeakHeight);
    this.ctx.lineTo(roofRight, roofTop);
    this.ctx.stroke();
    
    // 屋頂前緣（南側，面向玩家）- V 形線
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.moveTo(roofLeft, roofBottom);
    this.ctx.lineTo(roofCenterX, roofBottom - roofPeakHeight);
    this.ctx.lineTo(roofRight, roofBottom);
    this.ctx.stroke();
    
    // 煙囪
    if (['house', 'bakery', 'blacksmith', 'tavern'].includes(building.type)) {
      this.renderChimney(roofCenterX + width * 0.2, roofTop - roofPeakHeight + 4);
    }
    
    // 建築名稱（屋頂上方）
    if (building.type !== 'house') {
      this.ctx.fillStyle = '#fff';
      this.ctx.strokeStyle = '#000';
      this.ctx.lineWidth = 2;
      this.ctx.font = 'bold 10px sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      const nameY = roofTop - roofPeakHeight - 8;
      this.ctx.strokeText(building.name, screenX + width / 2, nameY);
      this.ctx.fillText(building.name, screenX + width / 2, nameY);
    }
  }
  
  // 保留舊方法供相容性
  renderBuilding(building) {
    this.renderBuildingFloor(building);
  }
  
  /**
   * 渲染門
   */
  renderDoor(x, y, w, h) {
    // 門框
    this.ctx.fillStyle = this.doorFrameColor;
    this.ctx.fillRect(x, y, w, h);
    
    // 門板
    this.ctx.fillStyle = this.doorColor;
    this.ctx.fillRect(x + 2, y + 2, w - 4, h - 2);
    
    // 門板紋理（木紋）
    this.ctx.fillStyle = '#3a2510';
    this.ctx.fillRect(x + 4, y + 3, 1, h - 5);
    this.ctx.fillRect(x + w - 5, y + 3, 1, h - 5);
    
    // 門把
    this.ctx.fillStyle = '#ffd700';
    this.ctx.fillRect(x + w - 6, y + h / 2, 2, 2);
  }
  
  /**
   * 渲染窗戶
   */
  renderWindow(x, y) {
    const size = this.tileSize - 4;
    
    // 窗框
    this.ctx.fillStyle = this.windowFrameColor;
    this.ctx.fillRect(x, y, size, size);
    
    // 玻璃
    this.ctx.fillStyle = this.windowColor;
    this.ctx.fillRect(x + 2, y + 2, size - 4, size - 4);
    
    // 窗格（十字）
    this.ctx.fillStyle = this.windowFrameColor;
    this.ctx.fillRect(x + size / 2 - 1, y + 2, 2, size - 4);
    this.ctx.fillRect(x + 2, y + size / 2 - 1, size - 4, 2);
    
    // 高光
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    this.ctx.fillRect(x + 3, y + 3, 3, 3);
  }
  
  /**
   * 渲染煙囪（2.5D 風格 - 參考 Stardew Valley）
   */
  renderChimney(x, y) {
    const width = 10;         // 煙囪寬度
    const depth = 6;          // 頂部深度
    const wallHeight = 16;    // 正面牆壁高度
    
    // 頂部位置
    const topY = y;
    
    // === 頂部正方形（俯視） ===
    this.ctx.fillStyle = '#4a4a4a';
    this.ctx.fillRect(x, topY, width, depth);
    
    // 煙囪洞口（黑色）
    this.ctx.fillStyle = '#1a1a1a';
    this.ctx.fillRect(x + 2, topY + 1, width - 4, depth - 2);
    
    // === 正面牆壁（矩形磚牆） ===
    const wallTop = topY + depth;
    
    // 磚牆背景
    this.ctx.fillStyle = '#5a5a5a';
    this.ctx.fillRect(x, wallTop, width, wallHeight);
    
    // 磚塊紋理（水平磚縫）
    this.ctx.fillStyle = '#3a3a3a';
    for (let row = 0; row < wallHeight; row += 4) {
      // 水平磚縫
      this.ctx.fillRect(x, wallTop + row, width, 1);
      // 垂直磚縫（交錯）
      const offset = (row / 4) % 2 === 0 ? 0 : width / 2;
      this.ctx.fillRect(x + offset, wallTop + row, 1, 4);
      if (offset === 0) {
        this.ctx.fillRect(x + width / 2, wallTop + row, 1, 4);
      }
    }
    
    // 右側陰影
    this.ctx.fillStyle = '#4a4a4a';
    this.ctx.fillRect(x + width - 2, wallTop, 2, wallHeight);
  }
}
