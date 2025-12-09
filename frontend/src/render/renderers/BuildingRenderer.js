/**
 * 建築渲染器
 */
import { BaseRenderer } from './BaseRenderer.js';

export class BuildingRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 建築物顏色
    this.colors = {
      // 食物鏈
      farm: { wall: '#9c8b6e', roof: '#8b7355' },
      mill: { wall: '#c4a574', roof: '#8b6914' },
      butcher_shop: { wall: '#a05050', roof: '#8b3030' },
      bakery: { wall: '#deb887', roof: '#d2691e' },
      
      // 器具鏈
      mine: { wall: '#6b6b6b', roof: '#4a4a4a' },
      lumber_camp: { wall: '#5d4e37', roof: '#4d3e27' },
      blacksmith: { wall: '#4a4a4a', roof: '#2f2f2f' },
      carpentry: { wall: '#8b7355', roof: '#6b5335' },
      
      // 服飾鏈
      pasture: { wall: '#6b9c4a', roof: '#5a8b3a' },
      weaver_shop: { wall: '#9c8b9c', roof: '#7b6b7b' },
      tannery: { wall: '#8b6b4a', roof: '#6b4b2a' },
      tailor_shop: { wall: '#b08080', roof: '#906060' },
      
      // 特殊
      market: { wall: '#deb887', roof: '#cd853f' },
      
      // 其他
      house: { wall: '#c4a574', roof: '#8b4513' },
      well: { wall: '#696969' }
    };
    
    // 開放式建築（不畫牆壁和屋頂）
    this.openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture', 'market'];
  }
  
  /**
   * 渲染所有建築物底部
   */
  render(buildings) {
    for (const building of buildings) {
      this.renderBuilding(building);
    }
  }
  
  /**
   * 渲染建築物頂部（屋頂）
   */
  renderTops(buildings) {
    for (const building of buildings) {
      // 跳過戶外工作場所
      if (this.openBuildings.includes(building.type)) continue;
      this.renderRoof(building);
    }
  }
  
  /**
   * 渲染單一建築物
   */
  renderBuilding(building) {
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    const height = building.height * this.tileSize;
    
    // 開放式建築只顯示名稱
    if (this.openBuildings.includes(building.type)) {
      this.ctx.fillStyle = '#fff';
      this.ctx.font = '10px sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(building.name, screenX + width / 2, screenY - 4);
      return;
    }
    
    const colors = this.colors[building.type] || this.colors.house;
    
    // 建築物地板
    this.ctx.fillStyle = '#8b7355';
    this.ctx.fillRect(screenX, screenY, width, height);
    
    // 牆壁
    this.ctx.fillStyle = colors.wall;
    
    // 上牆
    this.ctx.fillRect(screenX, screenY, width, this.tileSize);
    // 下牆
    this.ctx.fillRect(screenX, screenY + height - this.tileSize, width, this.tileSize);
    // 門
    const doorX = screenX + Math.floor(width / 2) - this.tileSize / 2;
    this.ctx.fillStyle = '#4a3520';
    this.ctx.fillRect(doorX, screenY + height - this.tileSize, this.tileSize, this.tileSize);
    
    // 左右牆
    this.ctx.fillStyle = colors.wall;
    this.ctx.fillRect(screenX, screenY, this.tileSize, height);
    this.ctx.fillRect(screenX + width - this.tileSize, screenY, this.tileSize, height);
  }
  
  /**
   * 渲染屋頂
   */
  renderRoof(building) {
    const colors = this.colors[building.type] || this.colors.house;
    if (!colors.roof) return;
    
    const { x: screenX, y: screenY } = this.toScreen(building.x, building.y);
    const width = building.width * this.tileSize;
    
    // 屋頂三角形
    this.ctx.fillStyle = colors.roof;
    this.ctx.beginPath();
    this.ctx.moveTo(screenX - 4, screenY);
    this.ctx.lineTo(screenX + width / 2, screenY - 16);
    this.ctx.lineTo(screenX + width + 4, screenY);
    this.ctx.closePath();
    this.ctx.fill();
    
    // 屋頂中央顯示建築名稱（民宅除外）
    if (building.type !== 'house') {
      this.ctx.fillStyle = '#fff';
      this.ctx.font = 'bold 10px sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(building.name, screenX + width / 2, screenY - 6);
    }
  }
}
