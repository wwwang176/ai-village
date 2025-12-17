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
    this.smoothing = 0.3;     // 平滑跟隨係數（更快跟隨）
    this.tileSize = 16;
    
    // 縮放
    this.zoom = 1.0;
    this.minZoom = 0.5;
    this.maxZoom = 3.0;
    this.zoomStep = 0.25;
  }
  
  /**
   * 放大
   */
  zoomIn() {
    this.zoom = Math.min(this.maxZoom, this.zoom + this.zoomStep);
    console.log(`🔍 縮放: ${(this.zoom * 100).toFixed(0)}%`);
  }
  
  /**
   * 縮小
   */
  zoomOut() {
    this.zoom = Math.max(this.minZoom, this.zoom - this.zoomStep);
    console.log(`🔍 縮放: ${(this.zoom * 100).toFixed(0)}%`);
  }
  
  /**
   * 重置縮放
   */
  resetZoom() {
    this.zoom = 1.0;
    console.log(`🔍 縮放: 100%`);
  }
  
  /**
   * 設定跟隨目標
   */
  follow(entity) {
    this.target = entity;
  }
  
  /**
   * 手動移動鏡頭
   * @param {number} dx - X 方向移動量（像素）
   * @param {number} dy - Y 方向移動量（像素）
   */
  move(dx, dy) {
    // 有跟隨目標時不允許手動移動
    if (this.target) return;
    
    this.x += dx;
    this.y += dy;
    this.clamp();
  }
  
  /**
   * 立即定位鏡頭到目標（不使用平滑）
   */
  centerOn(entity) {
    if (!entity) return;
    
    // 不考慮縮放，讓目標在未縮放的視窗中居中
    this.x = entity.x * this.tileSize - this.viewportWidth / 2 + this.tileSize / 2;
    this.y = entity.y * this.tileSize - this.viewportHeight / 2 + this.tileSize / 2;
    
    this.clamp();
  }
  
  /**
   * 更新鏡頭位置
   */
  update() {
    if (!this.target) return;
    
    // 相機不考慮縮放，只讓目標在未縮放的視窗中居中
    // 縮放會在渲染時以畫面中心為中心進行
    const targetX = this.target.x * this.tileSize - this.viewportWidth / 2 + this.tileSize / 2;
    const targetY = this.target.y * this.tileSize - this.viewportHeight / 2 + this.tileSize / 2;
    
    // 平滑移動
    this.x += (targetX - this.x) * this.smoothing;
    this.y += (targetY - this.y) * this.smoothing;
    
    // 限制在地圖範圍內
    this.clamp();
  }
  
  /**
   * 限制鏡頭：畫面中央不超過地圖邊界
   * 如果有跟隨目標，則不限制範圍（讓村民始終居中）
   */
  clamp() {
    // 如果有跟隨目標，不限制鏡頭範圍（讓目標始終居中）
    if (this.target) {
      this.offsetX = 0;
      this.offsetY = 0;
      return;
    }
    
    const halfWidth = this.viewportWidth / 2;
    const halfHeight = this.viewportHeight / 2;
    
    // 計算當前畫面中央的世界座標
    let centerX = this.x + halfWidth;
    let centerY = this.y + halfHeight;
    
    // 限制畫面中央在地圖範圍內 [0, mapWidth] x [0, mapHeight]
    centerX = Math.max(0, Math.min(centerX, this.mapWidth));
    centerY = Math.max(0, Math.min(centerY, this.mapHeight));
    
    // 反算 camera 位置
    this.x = centerX - halfWidth;
    this.y = centerY - halfHeight;
    
    // 不需要 offset
    this.offsetX = 0;
    this.offsetY = 0;
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
