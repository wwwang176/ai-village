/**
 * 主渲染器 - 協調各子渲染器
 */
import { TileRenderer } from './renderers/TileRenderer.js';
import { BuildingRenderer } from './renderers/BuildingRenderer.js';
import { EntityRenderer } from './renderers/EntityRenderer.js';
import { FurnitureRenderer } from './renderers/FurnitureRenderer.js';
import { ObjectRenderer } from './renderers/ObjectRenderer.js';
import { UIRenderer } from './renderers/UIRenderer.js';

export class Renderer {
  constructor(ctx, camera, tileSize) {
    this.ctx = ctx;
    this.camera = camera;
    this.tileSize = tileSize;
    
    // 初始化子渲染器
    this.tile = new TileRenderer(ctx, camera, tileSize);
    this.building = new BuildingRenderer(ctx, camera, tileSize);
    this.entity = new EntityRenderer(ctx, camera, tileSize);
    this.furniture = new FurnitureRenderer(ctx, camera, tileSize);
    this.object = new ObjectRenderer(ctx, camera, tileSize);
    this.ui = new UIRenderer(ctx, camera, tileSize);
  }
  
  /**
   * 渲染地圖（地形 + 建築底部 + 物件）
   */
  renderMap(map) {
    // 1. 地形
    this.tile.render(map);
    
    // 2. 建築物底部
    this.building.render(map.buildings);
    
    // 3. 物件（水井、樹等）
    this.object.render(map.objects);
    
    // 4. 地上物品
    if (map.worldItems) {
      this.object.renderWorldItems(map.worldItems);
    }
    
    // 5. 羊群
    if (map.sheep) {
      this.entity.renderSheep(map.sheep);
    }
  }
  
  /**
   * 渲染家具
   */
  renderFurniture(furniture) {
    this.furniture.render(furniture);
  }
  
  /**
   * 渲染村民路徑
   */
  renderVillagerPath(villager) {
    this.entity.renderVillagerPath(villager);
  }
  
  /**
   * 渲染村民
   */
  renderVillagers(villagers, selectedVillager = null) {
    this.entity.renderVillagers(villagers, selectedVillager);
    this.ui.renderVillagerBubbles(villagers);
  }
  
  /**
   * 渲染建築物頂部（屋頂）
   */
  renderBuildingTops(map) {
    this.building.renderTops(map.buildings);
  }
  
  /**
   * 渲染玩家
   */
  renderPlayer(player) {
    this.entity.renderPlayer(player);
  }
}
