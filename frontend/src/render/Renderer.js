/**
 * 主渲染器 - 協調各子渲染器（統一 Y-sorting）
 */
import { TileRenderer } from './renderers/TileRenderer.js';
import { BuildingRenderer } from './renderers/BuildingRenderer.js';
import { EntityRenderer } from './renderers/EntityRenderer.js';
import { FurnitureRenderer } from './renderers/FurnitureRenderer.js';
import { ObjectRenderer } from './renderers/ObjectRenderer.js';
import { UIRenderer } from './renderers/UIRenderer.js';
import { LightingRenderer } from './renderers/LightingRenderer.js';

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
    this.lighting = new LightingRenderer(ctx, camera, tileSize);
    
    // 開放式建築列表（不需要渲染頂部）
    this.openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture', 'market'];
  }
  
  /**
   * 渲染地圖（地形 + 建築底部 + 非樹木物件）
   * 樹木和羊群由 Y-sort 處理
   */
  renderMap(map) {
    // 1. 地形
    this.tile.render(map);
    
    // 2. 建築物底部
    this.building.render(map.buildings);
    
    // 3. 物件（水井等，樹木由 Y-sort 處理）
    if (map.objects) {
      const nonTreeObjects = map.objects.filter(obj => obj.type !== 'tree');
      this.object.render(nonTreeObjects);
    }
    
    // 4. 地上物品
    if (map.worldItems) {
      this.object.renderWorldItems(map.worldItems);
    }
    
    // 羊群由 Y-sort 處理
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
   * 渲染村民（不含對話框，對話框由 Y-sorting 處理）
   */
  renderVillagers(villagers, selectedVillager = null) {
    this.entity.renderVillagers(villagers, selectedVillager);
  }
  
  /**
   * 統一 Y-sorting 渲染高層物體
   * 包含：建築物牆面、矮牆、村民、家具、樹木、羊群、對話框等
   */
  renderYSorted(map, villagers = [], selectedVillager = null, furniture = []) {
    const renderables = [];
    const tileSize = this.tileSize;
    
    // 判斷每個村民是否在某個建築物內
    const villagersInBuildingIds = new Set();
    for (const villager of villagers) {
      const vx = Math.floor(villager.x);
      const vy = Math.floor(villager.y);
      for (const building of map.buildings) {
        if (vx >= building.x && vx < building.x + building.width &&
            vy >= building.y && vy < building.y + building.height) {
          villagersInBuildingIds.add(building.id);
          break;
        }
      }
    }
    
    // 收集建築物牆面（非開放式建築）
    for (const building of map.buildings) {
      if (this.openBuildings.includes(building.type)) continue;
      
      const hasOccupants = villagersInBuildingIds.has(building.id);
      
      if (hasOccupants) {
        // 有人在內：渲染北邊內部牆面
        renderables.push({
          type: 'north_wall',
          sortY: building.y,
          data: building
        });
        
        // 收集矮牆物件
        const lowWalls = this.building.getLowWallPositions(building);
        for (const wall of lowWalls) {
          renderables.push({
            type: 'low_wall',
            sortY: wall.y,
            data: wall
          });
        }
      } else {
        // 沒人在內：渲染南邊外部牆面 + 屋頂
        renderables.push({
          type: 'south_wall',
          sortY: building.y + building.height,
          data: building
        });
      }
    }
    
    // 收集村民
    for (const villager of villagers) {
      renderables.push({
        type: 'villager',
        sortY: villager.y,
        data: { villager, isSelected: villager === selectedVillager }
      });
    }
    
    // 收集家具
    for (const item of furniture) {
      renderables.push({
        type: 'furniture',
        sortY: item.y - 0.1,
        data: item
      });
    }
    
    // 收集樹木和其他物件
    if (map.objects) {
      for (const obj of map.objects) {
        if (obj.type === 'tree') {
          renderables.push({
            type: 'tree',
            sortY: obj.y,
            data: obj
          });
        }
      }
    }
    
    // 收集羊群
    if (map.sheep) {
      for (const sheep of map.sheep) {
        const posY = sheep.displayY ?? sheep.y;
        renderables.push({
          type: 'sheep',
          sortY: posY,
          data: sheep
        });
      }
    }
    
    // 收集村民對話框（稍微在村民後面）
    for (const villager of villagers) {
      if (villager.bubble) {
        renderables.push({
          type: 'bubble',
          sortY: villager.y + 0.01,
          data: villager
        });
      }
    }
    
    // 按 Y 座標排序（Y 小的先畫）
    renderables.sort((a, b) => a.sortY - b.sortY);
    
    // 依序渲染
    for (const item of renderables) {
      switch (item.type) {
        case 'north_wall':
          this.building.renderInteriorNorthWallOnly(item.data);
          break;
        case 'south_wall':
          this.building.renderBuilding2_5D(item.data, 1.0);
          break;
        case 'low_wall':
          this.building.renderSingleLowWall(item.data);
          break;
        case 'villager':
          this.entity.renderSingleVillager(item.data.villager, item.data.isSelected);
          break;
        case 'furniture':
          this.furniture.renderSingle(item.data);
          break;
        case 'tree':
          this.object.renderSingleObject(item.data);
          break;
        case 'sheep':
          this.entity.renderSingleSheep(item.data);
          break;
        case 'bubble':
          this.ui.renderSingleBubble(item.data);
          break;
      }
    }
  }
  
  /**
   * 渲染建築物頂部（舊方法，保留相容性）
   */
  renderBuildingTops(map, villagers = []) {
    this.renderYSorted(map, villagers);
  }
  
  /**
   * 渲染玩家
   */
  renderPlayer(player) {
    this.entity.renderPlayer(player);
  }
  
  /**
   * 渲染光照層（晝夜效果）
   */
  renderLighting(timeSystem, buildings, villagers, furniture, canvasWidth, canvasHeight, zoom) {
    this.lighting.render(timeSystem, buildings, villagers, furniture, canvasWidth, canvasHeight, zoom);
  }
}
