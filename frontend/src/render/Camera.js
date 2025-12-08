/**
 * 鏡頭系統 - 控制視野位置
 */

export class Camera {
  constructor(config) {
    this.x = 0;
    this.y = 0;
    
    this.viewportWidth = config.viewportWidth;
    this.viewportHeight = config.viewportHeight;
    this.mapWidth = config.mapWidth;
    this.mapHeight = config.mapHeight;
    
    // 視窗大於地圖時的偏移量（用於置中）
    this.offsetX = 0;
    this.offsetY = 0;
    
    this.target = null;       // 跟隨目標
    this.smoothing = 0.1;     // 平滑跟隨係數
    this.tileSize = 16;
  }
  
  /**
   * 設定跟隨目標
   */
  follow(entity) {
    this.target = entity;
  }
  
  /**
   * 更新鏡頭位置
   */
  update() {
    if (!this.target) return;
    
    // 目標螢幕中心位置
    const targetX = this.target.x * this.tileSize - this.viewportWidth / 2 + this.tileSize / 2;
    const targetY = this.target.y * this.tileSize - this.viewportHeight / 2 + this.tileSize / 2;
    
    // 平滑移動
    this.x += (targetX - this.x) * this.smoothing;
    this.y += (targetY - this.y) * this.smoothing;
    
    // 限制在地圖範圍內
    this.clamp();
  }
  
  /**
   * 限制鏡頭在地圖範圍內，視窗大於地圖時置中
   */
  clamp() {
    // 計算偏移量（視窗大於地圖時用於置中）
    if (this.viewportWidth > this.mapWidth) {
      this.offsetX = (this.viewportWidth - this.mapWidth) / 2;
      this.x = 0;
    } else {
      this.offsetX = 0;
      this.x = Math.max(0, Math.min(this.x, this.mapWidth - this.viewportWidth));
    }
    
    if (this.viewportHeight > this.mapHeight) {
      this.offsetY = (this.viewportHeight - this.mapHeight) / 2;
      this.y = 0;
    } else {
      this.offsetY = 0;
      this.y = Math.max(0, Math.min(this.y, this.mapHeight - this.viewportHeight));
    }
  }
  
  /**
   * 螢幕座標轉世界座標
   */
  screenToWorld(screenX, screenY) {
    return {
      x: screenX - this.offsetX + this.x,
      y: screenY - this.offsetY + this.y
    };
  }
  
  /**
   * 世界座標轉螢幕座標
   */
  worldToScreen(worldX, worldY) {
    return {
      x: worldX - this.x + this.offsetX,
      y: worldY - this.y + this.offsetY
    };
  }
}
