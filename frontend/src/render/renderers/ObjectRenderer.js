/**
 * 物件渲染器 - 水井、樹、地上物品等
 */
import { BaseRenderer } from './BaseRenderer.js';

export class ObjectRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 物品圖示對應表
    this.itemIcons = {
      'hoe': '⛏️', 'pickaxe': '⛏️', 'axe': '🪓', 'shears': '✂️',
      'cleaver': '🔪', 'hammer': '🔨', 'saw': '🪚', 'scraper': '🔪',
      'grain': '🌾', 'livestock': '🐄', 'ore': '🪨', 'wood': '🪵',
      'wool': '🧶', 'hide': '🐑', 'flour': '🌫️', 'meat_raw': '🥩',
      'iron': '🔩', 'plank': '📏', 'cloth': '🧵', 'leather': '🟤',
      'bread': '🍞', 'meat': '🍖', 'clothes': '👕', 'furniture': '🪑'
    };
  }
  
  /**
   * 渲染所有物件
   */
  render(objects) {
    for (const obj of objects) {
      this.renderObject(obj);
    }
  }
  
  /**
   * 渲染地上物品
   */
  renderWorldItems(items) {
    for (const item of items) {
      this.renderWorldItem(item);
    }
  }
  
  /**
   * 渲染單一物件
   */
  renderObject(obj) {
    const { x: screenX, y: screenY } = this.toScreen(obj.x, obj.y);
    const size = this.tileSize;
    
    this.ctx.fillStyle = obj.color || '#8b4513';
    
    switch (obj.type) {
      case 'well':
        this.renderWell(screenX, screenY, size);
        break;
      case 'tree':
        this.renderTree(screenX, screenY, size);
        break;
      case 'table':
        this.ctx.fillStyle = '#8d6e63';
        this.ctx.fillRect(screenX + 2, screenY + 2, size - 4, size - 4);
        break;
      case 'bed':
        this.ctx.fillStyle = '#795548';
        this.ctx.fillRect(screenX + 1, screenY + 1, size - 2, size - 2);
        this.ctx.fillStyle = '#bcaaa4';
        this.ctx.fillRect(screenX + 2, screenY + 2, size - 4, size / 2);
        break;
      case 'chair':
        this.ctx.fillStyle = '#6d4c41';
        this.ctx.fillRect(screenX + 3, screenY + 3, size - 6, size - 6);
        break;
      default:
        this.ctx.fillRect(screenX + 2, screenY + 2, size - 4, size - 4);
    }
  }
  
  /**
   * 渲染水井
   */
  renderWell(screenX, screenY, size) {
    // 外圈
    this.ctx.fillStyle = '#696969';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + size / 2, size / 2, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 內圈（水）
    this.ctx.fillStyle = '#3498db';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + size / 2, size / 3, 0, Math.PI * 2);
    this.ctx.fill();
  }
  
  /**
   * 渲染樹
   */
  renderTree(screenX, screenY, size) {
    // 樹幹
    this.ctx.fillStyle = '#5d4037';
    this.ctx.fillRect(screenX + size * 0.35, screenY + size * 0.5, size * 0.3, size * 0.5);
    
    // 樹冠
    this.ctx.fillStyle = '#2e7d32';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + size * 0.4, size * 0.45, 0, Math.PI * 2);
    this.ctx.fill();
  }
  
  /**
   * 渲染地上物品
   */
  renderWorldItem(item) {
    const { x: screenX, y: screenY } = this.toScreen(item.x, item.y);
    const size = this.tileSize;
    
    const icon = this.itemIcons[item.item_id] || '📦';
    
    // 背景
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.beginPath();
    this.ctx.roundRect(screenX + 2, screenY + 2, size - 4, size - 4, 4);
    this.ctx.fill();
    
    // 物品圖示
    this.ctx.font = `${size * 0.6}px sans-serif`;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(icon, screenX + size / 2, screenY + size / 2 - 2);
    
    // 數量
    if (item.quantity > 1) {
      this.ctx.font = 'bold 10px sans-serif';
      this.ctx.fillStyle = '#fff';
      this.ctx.textAlign = 'right';
      this.ctx.fillText(`${item.quantity}`, screenX + size - 4, screenY + size - 4);
    }
    
    // 擁有者標記
    if (item.owner_id) {
      this.ctx.fillStyle = '#ffd700';
      this.ctx.beginPath();
      this.ctx.arc(screenX + size - 6, screenY + 6, 3, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }
}
