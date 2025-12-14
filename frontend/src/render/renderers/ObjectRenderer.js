/**
 * 物件渲染器 - 水井、樹、地上物品等（像素風格）
 */
import { BaseRenderer } from './BaseRenderer.js';

export class ObjectRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 樹木顏色
    this.treeColors = {
      trunk: '#5d4037',
      trunkDark: '#3e2723',
      trunkLight: '#6d4c41',
      leaf1: '#2e7d32',      // 深綠
      leaf2: '#388e3c',      // 中綠
      leaf3: '#4caf50',      // 亮綠
      leaf4: '#1b5e20',      // 最深綠
      leafHighlight: '#66bb6a', // 高光
    };
    
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
        this.renderTree(screenX, screenY, size, obj);
        break;
      case 'rock':
        this.renderRock(screenX, screenY, size, obj);
        break;
      case 'bush':
        this.renderBush(screenX, screenY, size, obj);
        break;
      case 'tallgrass':
        this.renderTallGrass(screenX, screenY, size, obj);
        break;
      case 'stump':
        this.renderStump(screenX, screenY, size);
        break;
      case 'mushroom':
        this.renderMushroom(screenX, screenY, size, obj);
        break;
      case 'bridge_railing':
        this.renderBridgeRailing(screenX, screenY, size);
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
   * 渲染樹 - 像素風格多層次
   */
  renderTree(screenX, screenY, size, obj = null) {
    // 使用物件座標作為隨機種子，確保同一棵樹外觀一致
    const seed = obj ? (obj.x * 100 + obj.y) : 0;
    const variant = seed % 3; // 3 種樹木變體
    
    // 陰影
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    this.ctx.beginPath();
    this.ctx.ellipse(screenX + size / 2, screenY + size - 2, size * 0.4, size * 0.15, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    switch (variant) {
      case 0:
        this.renderOakTree(screenX, screenY, size);
        break;
      case 1:
        this.renderPineTree(screenX, screenY, size);
        break;
      case 2:
        this.renderBushyTree(screenX, screenY, size);
        break;
    }
  }
  
  /**
   * 橡樹 - 圓形樹冠
   */
  renderOakTree(screenX, screenY, size) {
    const cx = screenX + size / 2;
    
    // 樹幹
    this.ctx.fillStyle = this.treeColors.trunk;
    this.ctx.fillRect(cx - 2, screenY + size * 0.5, 4, size * 0.5);
    // 樹幹紋理
    this.ctx.fillStyle = this.treeColors.trunkDark;
    this.ctx.fillRect(cx - 1, screenY + size * 0.55, 1, size * 0.3);
    this.ctx.fillStyle = this.treeColors.trunkLight;
    this.ctx.fillRect(cx + 1, screenY + size * 0.6, 1, size * 0.2);
    
    // 樹冠 - 多層次
    // 底層（最深）
    this.ctx.fillStyle = this.treeColors.leaf4;
    this.ctx.fillRect(cx - 6, screenY + size * 0.3, 12, 8);
    
    // 中層
    this.ctx.fillStyle = this.treeColors.leaf1;
    this.ctx.fillRect(cx - 7, screenY + size * 0.15, 14, 10);
    this.ctx.fillRect(cx - 5, screenY + size * 0.35, 10, 4);
    
    // 上層（較亮）
    this.ctx.fillStyle = this.treeColors.leaf2;
    this.ctx.fillRect(cx - 5, screenY + size * 0.1, 10, 8);
    this.ctx.fillRect(cx - 6, screenY + size * 0.2, 12, 6);
    
    // 頂部
    this.ctx.fillStyle = this.treeColors.leaf3;
    this.ctx.fillRect(cx - 3, screenY + size * 0.05, 6, 5);
    
    // 高光
    this.ctx.fillStyle = this.treeColors.leafHighlight;
    this.ctx.fillRect(cx - 4, screenY + size * 0.12, 2, 2);
    this.ctx.fillRect(cx + 1, screenY + size * 0.18, 2, 2);
  }
  
  /**
   * 松樹 - 三角形
   */
  renderPineTree(screenX, screenY, size) {
    const cx = screenX + size / 2;
    
    // 樹幹
    this.ctx.fillStyle = this.treeColors.trunk;
    this.ctx.fillRect(cx - 2, screenY + size * 0.7, 4, size * 0.3);
    this.ctx.fillStyle = this.treeColors.trunkDark;
    this.ctx.fillRect(cx, screenY + size * 0.75, 1, size * 0.2);
    
    // 樹冠 - 三層三角形
    // 底層
    this.ctx.fillStyle = this.treeColors.leaf4;
    this.ctx.fillRect(cx - 6, screenY + size * 0.55, 12, 5);
    this.ctx.fillRect(cx - 5, screenY + size * 0.6, 10, 4);
    
    // 中層
    this.ctx.fillStyle = this.treeColors.leaf1;
    this.ctx.fillRect(cx - 5, screenY + size * 0.35, 10, 5);
    this.ctx.fillRect(cx - 4, screenY + size * 0.4, 8, 5);
    
    // 上層
    this.ctx.fillStyle = this.treeColors.leaf2;
    this.ctx.fillRect(cx - 4, screenY + size * 0.15, 8, 5);
    this.ctx.fillRect(cx - 3, screenY + size * 0.2, 6, 5);
    
    // 頂部
    this.ctx.fillStyle = this.treeColors.leaf3;
    this.ctx.fillRect(cx - 2, screenY + size * 0.05, 4, 4);
    this.ctx.fillRect(cx - 1, screenY, 2, 3);
    
    // 高光
    this.ctx.fillStyle = this.treeColors.leafHighlight;
    this.ctx.fillRect(cx - 2, screenY + size * 0.18, 1, 2);
  }
  
  /**
   * 茂密樹 - 較寬的樹冠
   */
  renderBushyTree(screenX, screenY, size) {
    const cx = screenX + size / 2;
    
    // 樹幹（較粗）
    this.ctx.fillStyle = this.treeColors.trunk;
    this.ctx.fillRect(cx - 3, screenY + size * 0.55, 6, size * 0.45);
    this.ctx.fillStyle = this.treeColors.trunkDark;
    this.ctx.fillRect(cx - 1, screenY + size * 0.6, 1, size * 0.3);
    this.ctx.fillStyle = this.treeColors.trunkLight;
    this.ctx.fillRect(cx + 1, screenY + size * 0.65, 1, size * 0.2);
    
    // 樹冠 - 較寬較矮
    // 底層
    this.ctx.fillStyle = this.treeColors.leaf4;
    this.ctx.fillRect(cx - 7, screenY + size * 0.35, 14, 6);
    
    // 中層
    this.ctx.fillStyle = this.treeColors.leaf1;
    this.ctx.fillRect(cx - 8, screenY + size * 0.2, 16, 8);
    this.ctx.fillRect(cx - 7, screenY + size * 0.4, 14, 4);
    
    // 上層
    this.ctx.fillStyle = this.treeColors.leaf2;
    this.ctx.fillRect(cx - 6, screenY + size * 0.1, 12, 8);
    
    // 頂部突起
    this.ctx.fillStyle = this.treeColors.leaf3;
    this.ctx.fillRect(cx - 4, screenY + size * 0.05, 3, 4);
    this.ctx.fillRect(cx + 1, screenY + size * 0.08, 3, 3);
    
    // 高光
    this.ctx.fillStyle = this.treeColors.leafHighlight;
    this.ctx.fillRect(cx - 5, screenY + size * 0.15, 2, 2);
    this.ctx.fillRect(cx + 3, screenY + size * 0.12, 2, 2);
  }
  
  /**
   * 渲染小石頭
   */
  renderRock(screenX, screenY, size, obj) {
    const seed = obj ? (obj.x * 100 + obj.y) : 0;
    const variant = seed % 3;
    
    // 陰影
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    this.ctx.fillRect(screenX + 4, screenY + size - 4, size - 6, 3);
    
    if (variant === 0) {
      // 小石頭
      this.ctx.fillStyle = '#7f8c8d';
      this.ctx.fillRect(screenX + 5, screenY + size - 8, 6, 5);
      this.ctx.fillStyle = '#95a5a6';
      this.ctx.fillRect(screenX + 6, screenY + size - 9, 4, 3);
      this.ctx.fillStyle = '#bdc3c7';
      this.ctx.fillRect(screenX + 7, screenY + size - 8, 2, 1);
    } else if (variant === 1) {
      // 扁石頭
      this.ctx.fillStyle = '#6b7b7c';
      this.ctx.fillRect(screenX + 3, screenY + size - 6, 10, 4);
      this.ctx.fillStyle = '#8b9b9c';
      this.ctx.fillRect(screenX + 4, screenY + size - 7, 8, 3);
      this.ctx.fillStyle = '#a0b0b0';
      this.ctx.fillRect(screenX + 5, screenY + size - 6, 3, 1);
    } else {
      // 雙石頭
      this.ctx.fillStyle = '#7f8c8d';
      this.ctx.fillRect(screenX + 3, screenY + size - 7, 5, 4);
      this.ctx.fillRect(screenX + 9, screenY + size - 6, 4, 3);
      this.ctx.fillStyle = '#95a5a6';
      this.ctx.fillRect(screenX + 4, screenY + size - 6, 3, 2);
      this.ctx.fillRect(screenX + 10, screenY + size - 5, 2, 1);
    }
  }
  
  /**
   * 渲染灌木
   */
  renderBush(screenX, screenY, size, obj) {
    const seed = obj ? (obj.x * 100 + obj.y) : 0;
    const variant = seed % 2;
    
    // 陰影
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    this.ctx.beginPath();
    this.ctx.ellipse(screenX + size / 2, screenY + size - 2, size * 0.35, size * 0.1, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    const cx = screenX + size / 2;
    
    if (variant === 0) {
      // 圓形灌木
      this.ctx.fillStyle = '#1b5e20';
      this.ctx.fillRect(cx - 6, screenY + size * 0.5, 12, 6);
      this.ctx.fillStyle = '#2e7d32';
      this.ctx.fillRect(cx - 7, screenY + size * 0.35, 14, 7);
      this.ctx.fillStyle = '#388e3c';
      this.ctx.fillRect(cx - 5, screenY + size * 0.3, 10, 5);
      // 高光
      this.ctx.fillStyle = '#4caf50';
      this.ctx.fillRect(cx - 3, screenY + size * 0.32, 2, 2);
      this.ctx.fillRect(cx + 2, screenY + size * 0.35, 2, 2);
    } else {
      // 寬灌木
      this.ctx.fillStyle = '#1b5e20';
      this.ctx.fillRect(cx - 7, screenY + size * 0.55, 14, 5);
      this.ctx.fillStyle = '#2e7d32';
      this.ctx.fillRect(cx - 8, screenY + size * 0.4, 16, 6);
      this.ctx.fillStyle = '#388e3c';
      this.ctx.fillRect(cx - 6, screenY + size * 0.35, 12, 4);
      // 高光
      this.ctx.fillStyle = '#4caf50';
      this.ctx.fillRect(cx - 4, screenY + size * 0.38, 2, 2);
      this.ctx.fillRect(cx + 3, screenY + size * 0.4, 2, 2);
    }
  }
  
  /**
   * 渲染高草
   */
  renderTallGrass(screenX, screenY, size, obj) {
    const seed = obj ? (obj.x * 100 + obj.y) : 0;
    
    // 多束草
    const grassColors = ['#2d5a1e', '#3d6b2a', '#4a7c34', '#5a8c44'];
    
    for (let i = 0; i < 4; i++) {
      const gx = screenX + 2 + (i * 3) + ((seed + i) % 2);
      const gh = 4 + ((seed + i) % 4);
      this.ctx.fillStyle = grassColors[(seed + i) % grassColors.length];
      this.ctx.fillRect(gx, screenY + size - gh - 2, 1, gh);
      this.ctx.fillRect(gx + 1, screenY + size - gh, 1, gh - 1);
    }
  }
  
  /**
   * 渲染樹樁
   */
  renderStump(screenX, screenY, size) {
    const cx = screenX + size / 2;
    
    // 陰影
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    this.ctx.fillRect(cx - 5, screenY + size - 3, 10, 3);
    
    // 樹樁
    this.ctx.fillStyle = '#5d4037';
    this.ctx.fillRect(cx - 4, screenY + size - 8, 8, 6);
    
    // 年輪
    this.ctx.fillStyle = '#8d6e63';
    this.ctx.fillRect(cx - 3, screenY + size - 7, 6, 4);
    this.ctx.fillStyle = '#6d4c41';
    this.ctx.fillRect(cx - 1, screenY + size - 6, 2, 2);
    
    // 樹皮
    this.ctx.fillStyle = '#3e2723';
    this.ctx.fillRect(cx - 4, screenY + size - 8, 1, 6);
    this.ctx.fillRect(cx + 3, screenY + size - 8, 1, 6);
  }
  
  /**
   * 渲染蘑菇
   */
  renderMushroom(screenX, screenY, size, obj) {
    const seed = obj ? (obj.x * 100 + obj.y) : 0;
    const variant = seed % 3;
    
    const cx = screenX + size / 2;
    const colors = [
      { cap: '#c0392b', capLight: '#e74c3c', stem: '#ecf0f1' }, // 紅蘑菇
      { cap: '#8e44ad', capLight: '#9b59b6', stem: '#ecf0f1' }, // 紫蘑菇
      { cap: '#d35400', capLight: '#e67e22', stem: '#fdf2e9' }, // 橙蘑菇
    ];
    const c = colors[variant];
    
    // 莖
    this.ctx.fillStyle = c.stem;
    this.ctx.fillRect(cx - 1, screenY + size - 6, 3, 4);
    
    // 傘蓋
    this.ctx.fillStyle = c.cap;
    this.ctx.fillRect(cx - 3, screenY + size - 9, 7, 4);
    this.ctx.fillRect(cx - 2, screenY + size - 10, 5, 2);
    
    // 高光
    this.ctx.fillStyle = c.capLight;
    this.ctx.fillRect(cx - 2, screenY + size - 9, 2, 2);
    
    // 白點（紅蘑菇）
    if (variant === 0) {
      this.ctx.fillStyle = '#fff';
      this.ctx.fillRect(cx, screenY + size - 9, 1, 1);
      this.ctx.fillRect(cx + 2, screenY + size - 8, 1, 1);
    }
  }
  
  /**
   * 渲染橋欄杆
   */
  renderBridgeRailing(screenX, screenY, size) {
    // 左側欄杆柱
    this.ctx.fillStyle = '#5d4037';
    this.ctx.fillRect(screenX + 2, screenY + 4, 4, size - 4);
    
    // 右側欄杆柱（跨越多格）
    this.ctx.fillRect(screenX + size + 2, screenY + 4, 4, size - 4);
    this.ctx.fillRect(screenX + size * 2 + 2, screenY + 4, 4, size - 4);
    this.ctx.fillRect(screenX + size * 3 - 2, screenY + 4, 4, size - 4);
    
    // 欄杆頂部裝飾
    this.ctx.fillStyle = '#8b7355';
    this.ctx.fillRect(screenX + 1, screenY + 2, 6, 3);
    this.ctx.fillRect(screenX + size + 1, screenY + 2, 6, 3);
    this.ctx.fillRect(screenX + size * 2 + 1, screenY + 2, 6, 3);
    this.ctx.fillRect(screenX + size * 3 - 3, screenY + 2, 6, 3);
    
    // 橫杆
    this.ctx.fillStyle = '#6b5335';
    this.ctx.fillRect(screenX + 2, screenY + 8, size * 3, 2);
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
