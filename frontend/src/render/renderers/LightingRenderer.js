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
    
    let darkness = 0;
    let tint = { r: 0, g: 0, b: 0 };
    
    if (timeValue >= 7 && timeValue < 17) {
      // 白天 07:00-17:00：無遮罩
      darkness = 0;
    } else if (timeValue >= 17 && timeValue < 19) {
      // 黃昏 17:00-19:00：漸暗，橙黃調
      const progress = (timeValue - 17) / 2; // 0 到 1
      darkness = progress * 0.5;
      tint = { r: 20, g: 10, b: 40 }; // 偏紫藍
    } else if (timeValue >= 19 || timeValue < 5) {
      // 夜晚 19:00-05:00：最暗，深藍調
      darkness = 0.6;
      tint = { r: 10, g: 15, b: 40 }; // 深藍
    } else if (timeValue >= 5 && timeValue < 7) {
      // 黎明 05:00-07:00：漸亮，粉橙調
      const progress = (timeValue - 5) / 2; // 0 到 1
      darkness = 0.6 * (1 - progress);
      tint = { r: 30, g: 15, b: 25 }; // 偏粉紫
    }
    
    return { darkness, tint };
  }
  
  /**
   * 繪製建築窗戶光源
   */
  _renderBuildingLights(buildings, villagers) {
    buildings.forEach(building => {
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
   * 檢查村民是否在室內
   */
  _isIndoor(villager, buildings) {
    return buildings.some(b => {
      return villager.x >= b.x && 
             villager.x < b.x + b.width &&
             villager.y >= b.y && 
             villager.y < b.y + b.height;
    });
  }
}
