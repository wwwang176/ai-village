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
   * 渲染床（2.5D 效果，整張床高度 1.5 格）
   */
  renderBed(x, y, size) {
    // 床的總高度 = 1.8 格
    const bedHeight = size * 1.8;
    // Y 座標向北偏移，讓床從上一格開始
    const startY = y - size * 0.8;
    
    // 木色床頭板（約 10%）
    this.ctx.fillStyle = '#D4A574';
    this.ctx.fillRect(x, startY, size, bedHeight * 0.1);
    
    // 米白色枕頭區域背景（約 20%）
    this.ctx.fillStyle = '#F5F0E6';
    this.ctx.fillRect(x, startY + bedHeight * 0.08, size, bedHeight * 0.2);
    
    // 米黃色枕頭
    this.ctx.fillStyle = '#F5F0DC';
    this.ctx.fillRect(x + size * 0.12, startY + bedHeight * 0.1, size * 0.76, bedHeight * 0.15);
    // 枕頭邊框
    this.ctx.strokeStyle = '#E0D5C0';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x + size * 0.12, startY + bedHeight * 0.1, size * 0.76, bedHeight * 0.15);
    
    // 淺藍色被子（約 55%）
    this.ctx.fillStyle = '#A8D4E6';
    this.ctx.fillRect(x, startY + bedHeight * 0.26, size, bedHeight * 0.55);
    
    // 被子上緣折疊線
    this.ctx.fillStyle = '#90C4D6';
    this.ctx.fillRect(x, startY + bedHeight * 0.26, size, bedHeight * 0.05);
    
    // 被子邊框
    this.ctx.strokeStyle = '#80B4C6';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x, startY + bedHeight * 0.26, size, bedHeight * 0.55);
    
    // 木色床尾板（約 10%）
    this.ctx.fillStyle = '#D4A574';
    this.ctx.fillRect(x, startY + bedHeight * 0.81, size, bedHeight * 0.1);
    
    // 床腳（左右，約 15%）
    this.ctx.fillStyle = '#C49A6C';
    this.ctx.fillRect(x, startY + bedHeight * 0.85, size * 0.1, bedHeight * 0.15);
    this.ctx.fillRect(x + size * 0.9, startY + bedHeight * 0.85, size * 0.1, bedHeight * 0.15);
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
