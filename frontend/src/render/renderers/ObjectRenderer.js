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
      'wool': '🧶', 'hide': '☁️', 'flour': '🌫️', 'meat_raw': '🥩',
      'iron': '🔩', 'plank': '📏', 'cloth': '🧵', 'leather': '🟤',
      'bread': '🍞', 'meat': '🍖', 'clothes': '👕', 'furniture': '🪑'
    };
    
    // 物品名稱對應表
    this.itemNames = {
      'hoe': '鋤頭', 'pickaxe': '鎬', 'axe': '斧頭', 'shears': '剪刀',
      'cleaver': '剁刀', 'hammer': '鐵鎚', 'saw': '鋸子', 'scraper': '刮刀',
      'grain': '穀物', 'livestock': '牲畜', 'ore': '礦石', 'wood': '木材',
      'wool': '羊毛', 'hide': '獸皮', 'flour': '麵粉', 'meat_raw': '生肉',
      'iron': '鐵錠', 'plank': '木板', 'cloth': '布料', 'leather': '皮革',
      'bread': '麵包', 'meat': '熟肉', 'clothes': '衣服', 'furniture': '傢俱'
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
    const itemName = this.itemNames[item.item_id] || '物品';
    
    // 陰影
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    this.ctx.beginPath();
    this.ctx.ellipse(screenX + size / 2, screenY + size - 4, size * 0.3, size * 0.12, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 物品圖示（不透明）
    this.ctx.font = `${size * 0.7}px sans-serif`;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(icon, screenX + size / 2, screenY + size / 2 - 4);
    
    // 數量（右下角）
    if (item.quantity > 1) {
      this.ctx.font = 'bold 9px sans-serif';
      this.ctx.fillStyle = '#fff';
      this.ctx.strokeStyle = '#000';
      this.ctx.lineWidth = 2;
      this.ctx.textAlign = 'right';
      this.ctx.strokeText(`x${item.quantity}`, screenX + size - 2, screenY + size - 6);
      this.ctx.fillText(`x${item.quantity}`, screenX + size - 2, screenY + size - 6);
    }
    
    // 物品標籤（下方顯示「XXX的XX」）
    const label = item.owner_name ? `${item.owner_name}的${itemName}` : itemName;
    this.ctx.font = '8px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillStyle = '#fff';
    this.ctx.strokeStyle = '#000';
    this.ctx.lineWidth = 2;
    this.ctx.strokeText(label, screenX + size / 2, screenY + size + 8);
    this.ctx.fillText(label, screenX + size / 2, screenY + size + 8);
  }
}
