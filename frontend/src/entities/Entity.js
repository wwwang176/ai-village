/**
 * 實體基類 - 所有遊戲物件的基礎
 */

export class Entity {
  constructor(config) {
    this.id = config.id || `entity_${Date.now()}`;
    this.x = config.x || 0;
    this.y = config.y || 0;
    this.name = config.name || '未知';
    
    this.velocity = { x: 0, y: 0 };
    this.path = [];         // A* 路徑
    this.pathIndex = 0;     // 當前路徑索引
    this.moveSpeed = 2;     // 每秒移動格數
  }
  
  /**
   * 更新實體
   */
  update(deltaTime, map) {
    // 如果有路徑，沿路徑移動
    if (this.path.length > 0) {
      this.moveAlongPath(deltaTime, map);
    } 
    // 否則使用速度移動
    else if (this.velocity.x !== 0 || this.velocity.y !== 0) {
      this.moveWithVelocity(deltaTime, map);
    }
  }
  
  /**
   * 沿路徑移動
   */
  moveAlongPath(deltaTime, map) {
    if (this.pathIndex >= this.path.length) {
      this.path = [];
      this.pathIndex = 0;
      this.onPathComplete();
      return;
    }
    
    const target = this.path[this.pathIndex];
    const dx = target.x - this.x;
    const dy = target.y - this.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    if (dist < 0.1) {
      // 到達該路徑點
      this.x = target.x;
      this.y = target.y;
      this.pathIndex++;
    } else {
      // 移動向該點
      const moveAmount = this.moveSpeed * deltaTime;
      this.x += (dx / dist) * Math.min(moveAmount, dist);
      this.y += (dy / dist) * Math.min(moveAmount, dist);
    }
  }
  
  /**
   * 使用速度移動
   */
  moveWithVelocity(deltaTime, map) {
    const newX = this.x + this.velocity.x * deltaTime;
    const newY = this.y + this.velocity.y * deltaTime;
    
    // 碰撞檢測
    const tileX = Math.floor(newX);
    const tileY = Math.floor(newY);
    
    if (map.isWalkable(tileX, tileY)) {
      this.x = newX;
      this.y = newY;
    } else {
      // 嘗試只移動一個軸
      const tileXOnly = Math.floor(this.x + this.velocity.x * deltaTime);
      const tileYOnly = Math.floor(this.y + this.velocity.y * deltaTime);
      
      if (map.isWalkable(tileXOnly, Math.floor(this.y))) {
        this.x = this.x + this.velocity.x * deltaTime;
      } else if (map.isWalkable(Math.floor(this.x), tileYOnly)) {
        this.y = this.y + this.velocity.y * deltaTime;
      }
    }
  }
  
  /**
   * 設定路徑
   */
  setPath(path) {
    this.path = path;
    this.pathIndex = 0;
  }
  
  /**
   * 設定速度
   */
  setVelocity(vx, vy) {
    this.velocity.x = vx;
    this.velocity.y = vy;
    // 清除路徑
    this.path = [];
    this.pathIndex = 0;
  }
  
  /**
   * 路徑完成回調
   */
  onPathComplete() {
    // 子類覆寫
  }
  
  /**
   * 取得格子座標
   */
  getTilePosition() {
    return {
      x: Math.floor(this.x),
      y: Math.floor(this.y)
    };
  }
  
  /**
   * 與另一個實體的距離
   */
  distanceTo(other) {
    const dx = other.x - this.x;
    const dy = other.y - this.y;
    return Math.sqrt(dx * dx + dy * dy);
  }
}
