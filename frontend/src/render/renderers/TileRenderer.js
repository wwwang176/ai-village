/**
 * 地形渲染器 - 像素風格
 */
import { BaseRenderer } from './BaseRenderer.js';

export class TileRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 河流動畫時間
    this.riverTime = 0;
    
    // 草地顏色變體（多層次）
    this.grassColors = [
      '#4a7c34', // 基礎綠
      '#3d6b2a', // 深綠
      '#5a8c44', // 亮綠
      '#456b2e', // 暗綠
      '#528a3a', // 中綠
    ];
    
    // 草地裝飾顏色
    this.grassDecoColors = {
      darkGrass: '#2d5a1e',
      lightGrass: '#6b9c4a',
      flower1: '#e74c3c',  // 紅花
      flower2: '#f39c12',  // 黃花
      flower3: '#9b59b6',  // 紫花
      flower4: '#3498db',  // 藍花
      flower5: '#ecf0f1',  // 白花
    };
    
    // 地形顏色
    this.colors = {
      grass: '#4a7c34',
      grass_dark: '#3d6b2a',
      road: '#8b7355',
      road_light: '#9c8465',
      road_stone: '#6b5a45',
      water: '#3498db',
      water_dark: '#2980b9',
      water_light: '#5dade2',
      floor: '#8b7355',
      wall: '#5d4e37',
      farmland: '#8b6914',
      farmland_dark: '#7a5c10',
      mine: '#6b6b6b',
      mine_dark: '#5a5a5a',
      lumber: '#5d4e37',
      lumber_dark: '#4d3e27',
      pasture: '#6b9c4a',
      pasture_dark: '#5a8b3a',
      plaza: '#a0937d',
      plaza_dark: '#8f8270'
    };
  }
  
  /**
   * Seeded random - 確保同座標產生相同隨機值
   */
  seededRandom(x, y, seed = 0) {
    const n = Math.sin(x * 12.9898 + y * 78.233 + seed) * 43758.5453;
    return n - Math.floor(n);
  }
  
  /**
   * 渲染所有地形
   */
  render(map) {
    for (let y = 0; y < map.height; y++) {
      for (let x = 0; x < map.width; x++) {
        const terrain = map.getTerrain(x, y);
        this.renderTile(x, y, terrain);
      }
    }
  }
  
  /**
   * 渲染單一格子
   */
  renderTile(tileX, tileY, terrain) {
    const { x: screenX, y: screenY } = this.toScreen(tileX, tileY);
    const size = this.tileSize;
    
    switch (terrain) {
      case 0: // 草地
        this.renderGrass(screenX, screenY, tileX, tileY);
        break;
      case 1: // 道路
        this.renderRoad(screenX, screenY, tileX, tileY);
        break;
      case 2: // 水
        this.renderWater(screenX, screenY, tileX, tileY);
        break;
      case 3: // 地板
        this.ctx.fillStyle = this.colors.floor;
        this.ctx.fillRect(screenX, screenY, size, size);
        break;
      case 4: // 農田
        this.renderFarmland(screenX, screenY, tileX, tileY);
        break;
      case 5: // 礦場
        this.renderMine(screenX, screenY, tileX, tileY);
        break;
      case 6: // 伐木場
        this.renderLumber(screenX, screenY, tileX, tileY);
        break;
      case 7: // 牧場
        this.renderPasture(screenX, screenY, tileX, tileY);
        break;
      case 8: // 市集廣場
        this.renderPlaza(screenX, screenY, tileX, tileY);
        break;
      case 9: // 河流
        this.renderRiver(screenX, screenY, tileX, tileY);
        break;
      case 10: // 橋樑
        this.renderBridge(screenX, screenY, tileX, tileY);
        break;
      default:
        this.ctx.fillStyle = this.colors.grass;
        this.ctx.fillRect(screenX, screenY, size, size);
    }
  }
  
  /**
   * 渲染草地 - 多層次像素風格
   */
  renderGrass(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 基底顏色（從多種綠色中選擇）
    const colorIndex = Math.floor(rand * this.grassColors.length);
    this.ctx.fillStyle = this.grassColors[colorIndex];
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 添加草地紋理變化（小色塊）
    const rand2 = this.seededRandom(tileX, tileY, 1);
    const rand3 = this.seededRandom(tileX, tileY, 2);
    
    // 深色斑點
    if (rand2 > 0.3) {
      this.ctx.fillStyle = this.grassColors[1]; // 深綠
      const spotX = Math.floor(rand2 * (size - 4));
      const spotY = Math.floor(rand3 * (size - 4));
      this.ctx.fillRect(screenX + spotX, screenY + spotY, 3, 3);
    }
    
    // 亮色斑點
    if (rand3 > 0.5) {
      this.ctx.fillStyle = this.grassColors[2]; // 亮綠
      const spotX = Math.floor(rand3 * (size - 3));
      const spotY = Math.floor(rand2 * (size - 3));
      this.ctx.fillRect(screenX + spotX, screenY + spotY, 2, 2);
    }
    
    // 小草裝飾（約 30% 機率）
    if (rand > 0.7) {
      this.renderGrassBlades(screenX, screenY, tileX, tileY);
    }
    
    // 野花裝飾（約 8% 機率）
    if (rand2 > 0.92) {
      this.renderFlower(screenX, screenY, tileX, tileY);
    }
  }
  
  /**
   * 渲染小草
   */
  renderGrassBlades(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY, 3);
    
    // 深色小草
    this.ctx.fillStyle = this.grassDecoColors.darkGrass;
    const x1 = screenX + Math.floor(rand * (size - 2));
    const y1 = screenY + Math.floor(this.seededRandom(tileX, tileY, 4) * (size - 4));
    this.ctx.fillRect(x1, y1, 1, 3);
    this.ctx.fillRect(x1 + 1, y1 + 1, 1, 2);
    
    // 亮色小草
    if (rand > 0.5) {
      this.ctx.fillStyle = this.grassDecoColors.lightGrass;
      const x2 = screenX + Math.floor(this.seededRandom(tileX, tileY, 5) * (size - 2));
      const y2 = screenY + Math.floor(this.seededRandom(tileX, tileY, 6) * (size - 3));
      this.ctx.fillRect(x2, y2, 1, 2);
    }
  }
  
  /**
   * 渲染野花
   */
  renderFlower(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY, 7);
    
    // 選擇花色
    const flowerColors = [
      this.grassDecoColors.flower1,
      this.grassDecoColors.flower2,
      this.grassDecoColors.flower3,
      this.grassDecoColors.flower4,
      this.grassDecoColors.flower5,
    ];
    const flowerColor = flowerColors[Math.floor(rand * flowerColors.length)];
    
    // 花的位置
    const fx = screenX + 2 + Math.floor(this.seededRandom(tileX, tileY, 8) * (size - 5));
    const fy = screenY + 2 + Math.floor(this.seededRandom(tileX, tileY, 9) * (size - 5));
    
    // 莖
    this.ctx.fillStyle = this.grassDecoColors.darkGrass;
    this.ctx.fillRect(fx + 1, fy + 2, 1, 2);
    
    // 花瓣（十字形）
    this.ctx.fillStyle = flowerColor;
    this.ctx.fillRect(fx + 1, fy, 1, 1);     // 上
    this.ctx.fillRect(fx, fy + 1, 1, 1);     // 左
    this.ctx.fillRect(fx + 2, fy + 1, 1, 1); // 右
    this.ctx.fillRect(fx + 1, fy + 1, 1, 1); // 中心（花蕊）
  }
  
  /**
   * 渲染道路 - 泥土紋理
   */
  renderRoad(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 基底
    this.ctx.fillStyle = rand > 0.5 ? this.colors.road : this.colors.road_light;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 小石子紋理
    const stoneCount = 2 + Math.floor(rand * 3);
    this.ctx.fillStyle = this.colors.road_stone;
    
    for (let i = 0; i < stoneCount; i++) {
      const sx = Math.floor(this.seededRandom(tileX, tileY, i + 10) * (size - 2));
      const sy = Math.floor(this.seededRandom(tileX, tileY, i + 20) * (size - 2));
      const sw = 1 + Math.floor(this.seededRandom(tileX, tileY, i + 30) * 2);
      this.ctx.fillRect(screenX + sx, screenY + sy, sw, 1);
    }
    
    // 亮色斑點
    if (rand > 0.6) {
      this.ctx.fillStyle = '#a89878';
      const lx = Math.floor(this.seededRandom(tileX, tileY, 40) * (size - 3));
      const ly = Math.floor(this.seededRandom(tileX, tileY, 41) * (size - 3));
      this.ctx.fillRect(screenX + lx, screenY + ly, 2, 2);
    }
  }
  
  /**
   * 渲染水 - 波紋效果
   */
  renderWater(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 基底
    this.ctx.fillStyle = rand > 0.5 ? this.colors.water : this.colors.water_dark;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 波光（亮色條紋）
    this.ctx.fillStyle = this.colors.water_light;
    const waveOffset = Math.floor(rand * size);
    this.ctx.fillRect(screenX + waveOffset % size, screenY + 2, 3, 1);
    this.ctx.fillRect(screenX + (waveOffset + 5) % size, screenY + size - 4, 2, 1);
  }
  
  /**
   * 渲染農田
   */
  renderFarmland(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 基底
    this.ctx.fillStyle = rand > 0.5 ? this.colors.farmland : this.colors.farmland_dark;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 犁溝紋理
    this.ctx.fillStyle = '#6b5510';
    for (let i = 2; i < size - 2; i += 4) {
      this.ctx.fillRect(screenX + 1, screenY + i, size - 2, 1);
    }
  }
  
  /**
   * 渲染礦場
   */
  renderMine(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    this.ctx.fillStyle = rand > 0.5 ? this.colors.mine : this.colors.mine_dark;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 礦石紋理
    this.ctx.fillStyle = '#4a4a4a';
    const rx = Math.floor(rand * (size - 3));
    const ry = Math.floor(this.seededRandom(tileX, tileY, 1) * (size - 3));
    this.ctx.fillRect(screenX + rx, screenY + ry, 2, 2);
  }
  
  /**
   * 渲染伐木場
   */
  renderLumber(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    this.ctx.fillStyle = rand > 0.5 ? this.colors.lumber : this.colors.lumber_dark;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 木屑紋理
    this.ctx.fillStyle = '#7d6e57';
    const cx = Math.floor(rand * (size - 2));
    const cy = Math.floor(this.seededRandom(tileX, tileY, 1) * (size - 2));
    this.ctx.fillRect(screenX + cx, screenY + cy, 1, 1);
  }
  
  /**
   * 渲染牧場
   */
  renderPasture(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 基底（較亮的草地）
    this.ctx.fillStyle = rand > 0.5 ? this.colors.pasture : this.colors.pasture_dark;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 草地紋理
    if (rand > 0.6) {
      this.ctx.fillStyle = '#7bac5a';
      const gx = Math.floor(rand * (size - 2));
      const gy = Math.floor(this.seededRandom(tileX, tileY, 1) * (size - 3));
      this.ctx.fillRect(screenX + gx, screenY + gy, 1, 2);
    }
  }
  
  /**
   * 渲染市集廣場
   */
  renderPlaza(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 石板基底
    this.ctx.fillStyle = rand > 0.5 ? this.colors.plaza : this.colors.plaza_dark;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 石板縫隙
    this.ctx.fillStyle = '#7f7265';
    this.ctx.fillRect(screenX, screenY + size - 1, size, 1);
    this.ctx.fillRect(screenX + size - 1, screenY, 1, size);
  }
  
  /**
   * 更新河流動畫時間
   */
  updateRiverAnimation(deltaTime) {
    this.riverTime += deltaTime * 8; // deltaTime 是秒，增大倍率讓流動更明顯
  }
  
  /**
   * 渲染河流（南北向，帶流動動畫）
   */
  renderRiver(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    const rand = this.seededRandom(tileX, tileY);
    
    // 水面基底
    this.ctx.fillStyle = this.colors.water;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 流動偏移（往南流動）
    const flowOffset = Math.floor(this.riverTime + tileY * 0.5) % size;
    
    // // 水波紋理（深色，南北向垂直線條，帶流動）
    // this.ctx.fillStyle = this.colors.water_dark;
    // const baseOffset = Math.floor(rand * 4);
    // for (let i = baseOffset; i < size; i += 5) {
    //   const y1 = (flowOffset) % size;
    //   const lineHeight = Math.floor(size * 0.6);
    //   // 繪製流動線條
    //   if (y1 + lineHeight <= size) {
    //     this.ctx.fillRect(screenX + i, screenY + y1, 1, lineHeight);
    //   } else {
    //     // 分段繪製（循環）
    //     this.ctx.fillRect(screenX + i, screenY + y1, 1, size - y1);
    //     this.ctx.fillRect(screenX + i, screenY, 1, lineHeight - (size - y1));
    //   }
    // }
    
    // 流動高光點
    this.ctx.fillStyle = this.colors.water_light;
    const sparkleOffset = Math.floor(this.riverTime * 1.5 + rand * 10) % size;
    const sx = Math.floor(rand * (size - 2));
    this.ctx.fillRect(screenX + sx, screenY + sparkleOffset, 2, 2);
    
    // 額外的流動光點
    if (rand > 0.5) {
      this.ctx.fillStyle = '#7ec8e3';
      const sparkle2 = Math.floor(this.riverTime * 2 + rand * 20) % size;
      const sx2 = Math.floor(this.seededRandom(tileX, tileY, 1) * (size - 1));
      this.ctx.fillRect(screenX + sx2, screenY + sparkle2, 1, 1);
    }
  }
  
  /**
   * 渲染橋樑
   */
  renderBridge(screenX, screenY, tileX, tileY) {
    const size = this.tileSize;
    
    // 先繪製水面作為底層
    this.ctx.fillStyle = this.colors.water;
    this.ctx.fillRect(screenX, screenY, size, size);
    
    // 橋面（木板）
    this.ctx.fillStyle = '#8b7355';
    this.ctx.fillRect(screenX, screenY + 2, size, size - 4);
    
    // 木板紋理
    this.ctx.fillStyle = '#6b5335';
    for (let i = 0; i < size; i += 4) {
      this.ctx.fillRect(screenX + i, screenY + 2, 1, size - 4);
    }
    
    // 木板高光
    this.ctx.fillStyle = '#9b8365';
    this.ctx.fillRect(screenX + 2, screenY + 4, size - 4, 2);
    
    // 橋邊緣
    this.ctx.fillStyle = '#5d4037';
    this.ctx.fillRect(screenX, screenY + 1, size, 2);
    this.ctx.fillRect(screenX, screenY + size - 3, size, 2);
  }
}
