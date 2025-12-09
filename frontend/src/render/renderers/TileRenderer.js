/**
 * 地形渲染器
 */
import { BaseRenderer } from './BaseRenderer.js';

export class TileRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
    
    // 地形顏色
    this.colors = {
      grass: '#4a7c34',
      grass_dark: '#3d6b2a',
      road: '#8b7355',
      road_light: '#9c8465',
      water: '#3498db',
      water_dark: '#2980b9',
      floor: '#8b7355',
      wall: '#5d4e37',
      farmland: '#8b6914',
      farmland_dark: '#7a5c10',
      mine: '#6b6b6b',
      mine_dark: '#5a5a5a',
      lumber: '#5d4e37',
      lumber_dark: '#4d3e27',
      pasture: '#6b9c4a',
      pasture_dark: '#5a8b3a',
      plaza: '#a0937d',
      plaza_dark: '#8f8270'
    };
  }
  
  /**
   * 渲染所有地形
   */
  render(map) {
    for (let y = 0; y < map.height; y++) {
      for (let x = 0; x < map.width; x++) {
        const terrain = map.getTerrain(x, y);
        this.renderTile(x, y, terrain);
      }
    }
  }
  
  /**
   * 渲染單一格子
   */
  renderTile(tileX, tileY, terrain) {
    const { x: screenX, y: screenY } = this.toScreen(tileX, tileY);
    
    // 根據地形類型選擇顏色（棋盤格紋理）
    const isEven = (tileX + tileY) % 2 === 0;
    let color = this.colors.grass;
    
    switch (terrain) {
      case 0: // 草地
        color = isEven ? this.colors.grass : this.colors.grass_dark;
        break;
      case 1: // 道路
        color = isEven ? this.colors.road : this.colors.road_light;
        break;
      case 2: // 水
        color = isEven ? this.colors.water : this.colors.water_dark;
        break;
      case 3: // 地板
        color = this.colors.floor;
        break;
      case 4: // 農田
        color = isEven ? this.colors.farmland : this.colors.farmland_dark;
        break;
      case 5: // 礦場
        color = isEven ? this.colors.mine : this.colors.mine_dark;
        break;
      case 6: // 伐木場
        color = isEven ? this.colors.lumber : this.colors.lumber_dark;
        break;
      case 7: // 牧場
        color = isEven ? this.colors.pasture : this.colors.pasture_dark;
        break;
      case 8: // 市集廣場
        color = isEven ? this.colors.plaza : this.colors.plaza_dark;
        break;
    }
    
    this.ctx.fillStyle = color;
    this.ctx.fillRect(screenX, screenY, this.tileSize, this.tileSize);
  }
}
