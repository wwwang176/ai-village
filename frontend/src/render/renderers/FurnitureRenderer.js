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
    const zoom = this.camera.zoom || 1;
    
    // LOD: 極遠景只畫簡單方塊
    if (zoom <= 0.5) {
      this.renderFurnitureLOD(screenX + offset, screenY + offset, size, item.type);
      return;
    }
    
    switch (item.type) {
      case 'stove':
        this.renderStove(screenX + offset, screenY + offset, size, zoom);
        break;
      case 'bed':
        this.renderBed(screenX + offset, screenY + offset, size, zoom);
        break;
      case 'workbench':
        this.renderWorkbench(screenX + offset, screenY + offset, size, zoom);
        break;
      default:
        this.renderGeneric(screenX + offset, screenY + offset, size);
    }
  }
  
  /**
   * LOD 簡化渲染（極遠景）
   */
  renderFurnitureLOD(x, y, size, type) {
    const colors = {
      'stove': '#8B4513',
      'bed': '#A8D4E6',
      'workbench': '#8B5A2B'
    };
    this.ctx.fillStyle = colors[type] || '#8d6e63';
    this.ctx.fillRect(x, y, size, size);
  }
  
  /**
   * 渲染灶台
   */
  renderStove(x, y, size, zoom = 1) {
    // 棕色底座
    this.ctx.fillStyle = '#8B4513';
    this.ctx.fillRect(x, y, size, size);
    
    // LOD: 中遠景省略火焰細節
    if (zoom <= 0.75) {
      this.ctx.fillStyle = '#FF4500';
      this.ctx.fillRect(x + size * 0.3, y + size * 0.3, size * 0.4, size * 0.4);
      return;
    }
    
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
  renderBed(x, y, size, zoom = 1) {
    // 床的總高度 = 1.8 格
    const bedHeight = size * 1.8;
    // Y 座標向北偏移，讓床從上一格開始
    const startY = y - size * 0.8;
    
    // LOD: 中遠景簡化渲染
    if (zoom <= 0.75) {
      // 簡化：只畫床頭、被子、床尾
      this.ctx.fillStyle = '#D4A574';
      this.ctx.fillRect(x, startY, size, bedHeight * 0.15);
      this.ctx.fillStyle = '#A8D4E6';
      this.ctx.fillRect(x, startY + bedHeight * 0.15, size, bedHeight * 0.7);
      this.ctx.fillStyle = '#D4A574';
      this.ctx.fillRect(x, startY + bedHeight * 0.85, size, bedHeight * 0.15);
      return;
    }
    
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
   * 渲染工作台（2.5D 風格，向北延伸）
   */
  renderWorkbench(x, y, size, zoom = 1) {
    // 桌面 1 格 + 桌腳 0.3 格，總高度 1.3 格
    // 向北偏移 0.3 格，讓桌腳底部貼到格子南端
    const startY = y - size * 0.3;
    
    // LOD: 中遠景簡化渲染
    if (zoom <= 0.75) {
      // 簡化：只畫桌面和桌腳
      this.ctx.fillStyle = '#5D3A1A';
      this.ctx.fillRect(x + size * 0.1, startY + size, size * 0.12, size * 0.3);
      this.ctx.fillRect(x + size * 0.78, startY + size, size * 0.12, size * 0.3);
      this.ctx.fillStyle = '#A0724B';
      this.ctx.fillRect(x, startY, size, size);
      return;
    }
    
    // 桌腳（左右，先畫在最底層）- 從 startY + size 到 startY + 1.3*size
    this.ctx.fillStyle = '#5D3A1A';
    this.ctx.fillRect(x + size * 0.1, startY + size, size * 0.12, size * 0.3);
    this.ctx.fillRect(x + size * 0.78, startY + size, size * 0.12, size * 0.3);
    
    // 桌子正面（厚度）- 在桌面底部
    this.ctx.fillStyle = '#6B4423';
    this.ctx.fillRect(x, startY + size * 0.85, size, size * 0.15);
    
    // 桌面（俯視面積，淺棕色）- 從 startY 到 startY + 0.85*size
    this.ctx.fillStyle = '#A0724B';
    this.ctx.fillRect(x, startY, size, size * 0.85);
    
    // 桌面邊框
    this.ctx.strokeStyle = '#5D3A1A';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x, startY, size, size);
    
    // 桌面木紋（水平線條）
    this.ctx.strokeStyle = '#8B5A2B';
    this.ctx.beginPath();
    this.ctx.moveTo(x + size * 0.1, startY + size * 0.3);
    this.ctx.lineTo(x + size * 0.9, startY + size * 0.3);
    this.ctx.moveTo(x + size * 0.1, startY + size * 0.6);
    this.ctx.lineTo(x + size * 0.9, startY + size * 0.6);
    this.ctx.stroke();
    
    // 桌上工具（左：灰色方塊代表錘子/工具）
    this.ctx.fillStyle = '#505050';
    this.ctx.fillRect(x + size * 0.15, startY + size * 0.1, size * 0.2, size * 0.15);
    
    // 桌上工具（右：橘色方塊代表材料）
    this.ctx.fillStyle = '#CD853F';
    this.ctx.fillRect(x + size * 0.65, startY + size * 0.1, size * 0.2, size * 0.15);
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
