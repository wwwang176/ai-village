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
      market: { wall: '#deb887', wallDark: '#cea877', roof: '#cd853f', roofDark: '#bd752f' },
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
    this.openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture', 'market'];
    
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
    
    for (const building of sortedBuildings) {
      // 跳過戶外工作場所
      if (this.openBuildings.includes(building.type)) continue;
      
      // 檢查是否有村民在此建築內
      const hasOccupants = villagersInBuildings.some(v => v.buildingId === building.id);
      
      if (hasOccupants) {
        // 有村民時：完全透明，只畫北邊內部牆面
        this.renderInteriorNorthWall(building);
      } else {
        // 無村民時：正常渲染外部結構
        this.renderBuilding2_5D(building, 1.0);
      }
    }
  }
  
  /**
   * 渲染北邊內部牆面（村民在建築內時顯示）
   */
  renderInteriorNorthWall(building) {
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    const ts = this.tileSize;
    const colors = this.colors[building.type] || this.colors.house;
    
    const wallHeight = this.wallHeight;
    const gableHeight = this.roofHeight;
    
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
        this.ctx.fillRect(screenX + i, wallTop + row + 7, ts - 2, 1);
      }
    }
    
    // 牆壁底部陰影線
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.fillRect(screenX, wallBottom - 2, width, 2);
    
    // 窗戶（北邊內部牆面）
    if (building.width >= 4) {
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
      this.renderWindow(screenX + width - ts * 2, windowY);
    }
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
        this.ctx.fillRect(screenX + i, wallTop + row + 7, ts - 2, 1);
      }
    }
    
    // 正面牆壁陰影（底部）
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    this.ctx.fillRect(screenX, wallBottom - 3, width, 3);
    
    // 門（正面牆壁中央）
    const doorWidth = ts;
    const doorHeight = wallHeight - 4;
    const doorX = screenX + Math.floor(width / 2) - doorWidth / 2;
    this.renderDoor(doorX, wallTop + 2, doorWidth, doorHeight);
    
    // 窗戶（門兩側）
    if (building.width >= 4) {
      const windowY = wallTop + 4;
      this.renderWindow(screenX + ts, windowY);
      this.renderWindow(screenX + width - ts * 2, windowY);
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
    
    // 牆壁頂部位置
    const wallTop = screenY + height - wallHeight;
    
    const roofTop = screenY - 2; // 屋頂北側
    const roofBottom = wallTop; // 屋頂南側對齊牆壁頂部
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
