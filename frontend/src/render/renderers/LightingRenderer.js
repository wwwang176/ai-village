/**
 * 光照渲染器 - 處理晝夜光照效果
 */
import { BaseRenderer } from './BaseRenderer.js';

export class LightingRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 離屏 canvas 用於光照貼圖
    this.lightCanvas = document.createElement('canvas');
    this.lightCtx = this.lightCanvas.getContext('2d');
    
    // 縮放和畫面中心（會在 render 時更新）
    this.zoom = 1;
    this.canvasCenterX = 0;
    this.canvasCenterY = 0;
    
    // 開放式建築（不渲染光源，村民在內視為室外）
    this.openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture', 'plaza'];
    
    // 火焰閃爍效果的時間變數
    this.flickerTime = 0;
  }
  
  /**
   * 將世界座標轉換為螢幕座標（考慮縮放）
   */
  toScreenWithZoom(worldX, worldY) {
    // 先計算未縮放的螢幕座標
    const baseX = worldX * this.tileSize - this.camera.x + this.camera.offsetX;
    const baseY = worldY * this.tileSize - this.camera.y + this.camera.offsetY;
    
    // 應用縮放（以畫面中心為縮放中心）
    const scaledX = this.canvasCenterX + (baseX - this.canvasCenterX) * this.zoom;
    const scaledY = this.canvasCenterY + (baseY - this.canvasCenterY) * this.zoom;
    
    return { x: scaledX, y: scaledY };
  }
  
  /**
   * 渲染光照層
   * @param {Object} timeSystem - 時間系統
   * @param {Array} buildings - 建築物列表
   * @param {Array} villagers - 村民列表
   * @param {Array} furniture - 家具列表
   * @param {number} canvasWidth - 畫布寬度
   * @param {number} canvasHeight - 畫布高度
   * @param {number} zoom - 縮放比例
   */
  render(timeSystem, buildings, villagers, furniture, canvasWidth, canvasHeight, zoom = 1) {
    this.zoom = zoom;
    this.canvasCenterX = canvasWidth / 2;
    this.canvasCenterY = canvasHeight / 2;
    // 計算光照參數
    const { darkness, tint } = this._getAmbientLight(timeSystem);
    
    // 白天不需要渲染光照層
    if (darkness <= 0.01) return;
    
    // 調整離屏 canvas 大小
    if (this.lightCanvas.width !== canvasWidth || this.lightCanvas.height !== canvasHeight) {
      this.lightCanvas.width = canvasWidth;
      this.lightCanvas.height = canvasHeight;
    }
    
    // 清除並填滿暗色
    this.lightCtx.clearRect(0, 0, canvasWidth, canvasHeight);
    this.lightCtx.fillStyle = `rgba(${tint.r}, ${tint.g}, ${tint.b}, ${darkness})`;
    this.lightCtx.fillRect(0, 0, canvasWidth, canvasHeight);
    
    // 使用 destination-out 模式繪製光源（挖洞）
    this.lightCtx.globalCompositeOperation = 'destination-out';
    
    // 繪製建築窗戶光源
    this._renderBuildingLights(buildings, villagers);
    
    // 繪製灶台光源
    this._renderStoveLights(furniture);
    
    // 繪製戶外村民光源
    this._renderVillagerLights(villagers, buildings);
    
    // 還原混合模式
    this.lightCtx.globalCompositeOperation = 'source-over';
    
    // 將光照層疊加到主畫面
    this.ctx.drawImage(this.lightCanvas, 0, 0);
  }
  
  /**
   * 根據時間計算環境光照參數
   */
  _getAmbientLight(timeSystem) {
    const hour = timeSystem.hour;
    const minute = timeSystem.minute;
    const timeValue = hour + minute / 60; // 小數形式的時間
    
    // 定義各時段的光照參數
    const phases = {
      night:  { darkness: 0.6, tint: { r: 10, g: 15, b: 40 } },   // 深藍夜晚
      dawn:   { darkness: 0.3, tint: { r: 30, g: 15, b: 25 } },   // 粉紫黎明
      day:    { darkness: 0,   tint: { r: 0,  g: 0,  b: 0 } },    // 明亮白天
      dusk:   { darkness: 0.3, tint: { r: 25, g: 15, b: 35 } },   // 橙紫黃昏
    };
    
    // 線性插值函數
    const lerp = (a, b, t) => a + (b - a) * t;
    const lerpPhase = (from, to, t) => ({
      darkness: lerp(from.darkness, to.darkness, t),
      tint: {
        r: lerp(from.tint.r, to.tint.r, t),
        g: lerp(from.tint.g, to.tint.g, t),
        b: lerp(from.tint.b, to.tint.b, t),
      }
    });
    
    // 時段定義（每個過渡持續 1 小時）
    // 04:00-05:00：夜晚 → 黎明
    // 05:00-06:00：黎明
    // 06:00-07:00：黎明 → 白天
    // 07:00-17:00：白天
    // 17:00-18:00：白天 → 黃昏
    // 18:00-19:00：黃昏
    // 19:00-20:00：黃昏 → 夜晚
    // 20:00-04:00：夜晚
    
    if (timeValue >= 7 && timeValue < 17) {
      // 白天 07:00-17:00
      return phases.day;
    } else if (timeValue >= 17 && timeValue < 18) {
      // 白天 → 黃昏 17:00-18:00
      const progress = timeValue - 17;
      return lerpPhase(phases.day, phases.dusk, progress);
    } else if (timeValue >= 18 && timeValue < 19) {
      // 黃昏 18:00-19:00
      return phases.dusk;
    } else if (timeValue >= 19 && timeValue < 20) {
      // 黃昏 → 夜晚 19:00-20:00
      const progress = timeValue - 19;
      return lerpPhase(phases.dusk, phases.night, progress);
    } else if (timeValue >= 20 || timeValue < 4) {
      // 夜晚 20:00-04:00
      return phases.night;
    } else if (timeValue >= 4 && timeValue < 5) {
      // 夜晚 → 黎明 04:00-05:00
      const progress = timeValue - 4;
      return lerpPhase(phases.night, phases.dawn, progress);
    } else if (timeValue >= 5 && timeValue < 6) {
      // 黎明 05:00-06:00
      return phases.dawn;
    } else if (timeValue >= 6 && timeValue < 7) {
      // 黎明 → 白天 06:00-07:00
      const progress = timeValue - 6;
      return lerpPhase(phases.dawn, phases.day, progress);
    }
    
    return phases.day;
  }
  
  /**
   * 繪製建築窗戶光源
   */
  _renderBuildingLights(buildings, villagers) {
    buildings.forEach(building => {
      // 開放式建築不渲染光源
      if (this.openBuildings.includes(building.type)) return;
      
      // 檢查是否有村民在家
      const hasOccupant = this._hasSomeoneHome(building, villagers);
      if (!hasOccupant) return;
      
      // 建築中心位置
      const centerX = building.x + building.width / 2;
      const centerY = building.y + building.height / 2;
      
      // 轉換為螢幕座標（考慮縮放）
      const screen = this.toScreenWithZoom(centerX, centerY);
      
      // 繪製光源（半徑也要縮放）
      this._drawLight(screen.x, screen.y, this.tileSize * 2.5 * this.zoom, 0.9);
    });
  }
  
  /**
   * 繪製灶台光源（恆亮）
   */
  _renderStoveLights(furniture) {
    furniture.forEach(item => {
      if (item.type !== 'stove') return;
      
      const screen = this.toScreenWithZoom(item.x + 0.5, item.y + 0.5);
      this._drawLight(screen.x, screen.y, this.tileSize * 1.5 * this.zoom, 0.7);
    });
  }
  
  /**
   * 繪製戶外村民光源
   */
  _renderVillagerLights(villagers, buildings) {
    villagers.forEach(villager => {
      // 檢查村民是否在室內
      if (this._isIndoor(villager, buildings)) return;
      
      const screen = this.toScreenWithZoom(villager.x, villager.y - 0.5);
      this._drawLight(screen.x, screen.y, this.tileSize * 2 * this.zoom, 0.8);
    });
  }
  
  /**
   * 繪製單個光源（徑向漸變）
   */
  _drawLight(x, y, radius, intensity) {
    const gradient = this.lightCtx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, `rgba(255, 255, 255, ${intensity})`);
    gradient.addColorStop(0.3, `rgba(255, 255, 255, ${intensity * 0.6})`);
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
    
    this.lightCtx.fillStyle = gradient;
    this.lightCtx.beginPath();
    this.lightCtx.arc(x, y, radius, 0, Math.PI * 2);
    this.lightCtx.fill();
  }
  
  /**
   * 檢查建築內是否有人
   */
  _hasSomeoneHome(building, villagers) {
    return villagers.some(v => {
      return v.x >= building.x && 
             v.x < building.x + building.width &&
             v.y >= building.y && 
             v.y < building.y + building.height;
    });
  }
  
  /**
   * 檢查村民是否在室內（開放式建築不算室內）
   */
  _isIndoor(villager, buildings) {
    return buildings.some(b => {
      // 開放式建築不算室內
      if (this.openBuildings.includes(b.type)) return false;
      
      return villager.x >= b.x && 
             villager.x < b.x + b.width &&
             villager.y >= b.y && 
             villager.y < b.y + b.height;
    });
  }
}
