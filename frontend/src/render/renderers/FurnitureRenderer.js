/**
 * 家具渲染器 - 灶台、床等室內物件
 */
import { BaseRenderer } from './BaseRenderer.js';

export class FurnitureRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
  }
  
  /**
   * 渲染所有家具
   */
  render(furniture) {
    if (!furniture || furniture.length === 0) return;
    
    for (const item of furniture) {
      this.renderItem(item);
    }
  }
  
  /**
   * 渲染單一家具（用於 Y-sort）
   */
  renderSingle(item) {
    this.renderItem(item);
  }
  
  /**
   * 渲染單一家具
   */
  renderItem(item) {
    const { x: screenX, y: screenY } = this.toScreen(item.x, item.y);
    const size = this.tileSize * 0.6;
    const offset = (this.tileSize - size) / 2;
    
    switch (item.type) {
      case 'stove':
        this.renderStove(screenX + offset, screenY + offset, size);
        break;
      case 'bed':
        this.renderBed(screenX + offset, screenY + offset, size);
        break;
      default:
        this.renderGeneric(screenX + offset, screenY + offset, size);
    }
  }
  
  /**
   * 渲染灶台
   */
  renderStove(x, y, size) {
    // 棕色底座
    this.ctx.fillStyle = '#8B4513';
    this.ctx.fillRect(x, y, size, size);
    
    // 火焰線條
    this.ctx.strokeStyle = '#FF4500';
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    
    // 左火焰
    this.ctx.moveTo(x + size * 0.25, y + size * 0.7);
    this.ctx.lineTo(x + size * 0.2, y + size * 0.3);
    this.ctx.lineTo(x + size * 0.35, y + size * 0.5);
    
    // 中火焰
    this.ctx.moveTo(x + size * 0.5, y + size * 0.7);
    this.ctx.lineTo(x + size * 0.5, y + size * 0.2);
    this.ctx.lineTo(x + size * 0.6, y + size * 0.45);
    
    // 右火焰
    this.ctx.moveTo(x + size * 0.75, y + size * 0.7);
    this.ctx.lineTo(x + size * 0.8, y + size * 0.35);
    this.ctx.lineTo(x + size * 0.65, y + size * 0.5);
    
    this.ctx.stroke();
  }
  
  /**
   * 渲染床
   */
  renderBed(x, y, size) {
    // 深棕色床架
    this.ctx.fillStyle = '#654321';
    this.ctx.fillRect(x, y, size, size);
    
    // 米白床單
    this.ctx.fillStyle = '#F5F5DC';
    this.ctx.fillRect(x + 2, y + 2, size - 4, size * 0.6);
    
    // 白色枕頭
    this.ctx.fillStyle = '#FFFFFF';
    this.ctx.fillRect(x + 3, y + 3, size * 0.3, size * 0.25);
    
    // 床架線條
    this.ctx.strokeStyle = '#4a3520';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x, y, size, size);
  }
  
  /**
   * 渲染通用家具
   */
  renderGeneric(x, y, size) {
    this.ctx.fillStyle = '#8d6e63';
    this.ctx.fillRect(x, y, size, size);
    this.ctx.strokeStyle = '#5d4037';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x, y, size, size);
  }
}
