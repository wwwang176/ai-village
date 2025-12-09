/**
 * 基礎渲染器 - 提供共用方法和狀態
 */
export class BaseRenderer {
  constructor(ctx, camera, tileSize) {
    this.ctx = ctx;
    this.camera = camera;
    this.tileSize = tileSize;
  }
  
  /**
   * 將世界座標轉換為螢幕座標
   */
  toScreen(worldX, worldY) {
    return {
      x: worldX * this.tileSize - this.camera.x + this.camera.offsetX,
      y: worldY * this.tileSize - this.camera.y + this.camera.offsetY
    };
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
}
