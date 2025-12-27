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
    this.openBuildings = ['farm', 'mine', 'lumber_camp', 'pasture', 'plaza'];
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
  renderFurniture(furniture, villagers = []) {
    this.furniture.render(furniture, villagers);
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
    
    // 漸變速度（每幀變化量）
    const fadeSpeed = 0.08;
    
    // 收集建築物牆面（非開放式建築）
    for (const building of map.buildings) {
      if (this.openBuildings.includes(building.type)) continue;
      
      const hasOccupants = villagersInBuildingIds.has(building.id);
      
      // 初始化 currentOpacity（1.0 = 外部完全顯示，0.0 = 內部完全顯示）
      if (building.currentOpacity === undefined) {
        building.currentOpacity = 1.0;
      }
      
      // 計算目標透明度
      const targetOpacity = hasOccupants ? 0.0 : 1.0;
      
      // 漸變更新 currentOpacity
      if (building.currentOpacity < targetOpacity) {
        building.currentOpacity = Math.min(building.currentOpacity + fadeSpeed, targetOpacity);
      } else if (building.currentOpacity > targetOpacity) {
        building.currentOpacity = Math.max(building.currentOpacity - fadeSpeed, targetOpacity);
      }
      
      const opacity = building.currentOpacity;
      
      // 內部北牆（透明度 = 1 - opacity）
      if (opacity < 1.0) {
        renderables.push({
          type: 'north_wall',
          sortY: building.y,
          data: { building, opacity: 1.0 - opacity }
        });
        
        // 收集矮牆物件（也需要漸變）
        const lowWalls = this.building.getLowWallPositions(building);
        for (const wall of lowWalls) {
          renderables.push({
            type: 'low_wall',
            sortY: wall.y,
            data: { ...wall, opacity: 1.0 - opacity }
          });
        }
      }
      
      // 外部建築（透明度 = opacity）
      if (opacity > 0.0) {
        renderables.push({
          type: 'south_wall',
          sortY: building.y + building.height,
          data: { building, opacity }
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
    
    // 收集樹木（從 map.trees）
    if (map.trees) {
      for (const tree of map.trees) {
        renderables.push({
          type: 'tree',
          sortY: tree.y,
          data: { ...tree, type: 'tree' }
        });
      }
    }
    
    // 收集其他物件中的樹木
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
    
    // 收集草叢（前後分層）
    if (map.bushes) {
      for (const bush of map.bushes) {
        // 小草前後靠近一點
        const backOffset = bush.size === 'small' ? -0.25 : -0.4;
        const frontOffset = bush.size === 'small' ? 0.35 : 0.5;
        // 後景（sortY 略小，先渲染）
        renderables.push({
          type: 'bush_back',
          sortY: bush.y + backOffset,
          data: bush
        });
        // 前景（sortY 略大，後渲染）
        renderables.push({
          type: 'bush_front',
          sortY: bush.y + frontOffset,
          data: bush
        });
      }
    }
    
    // 收集稻米（前後分層）
    if (map.crops) {
      for (const crop of map.crops) {
        // 後景
        renderables.push({
          type: 'crop_back',
          sortY: crop.y - 0.4,
          data: crop
        });
        // 前景
        renderables.push({
          type: 'crop_front',
          sortY: crop.y + 0.5,
          data: crop
        });
      }
    }
    
    // 收集礦石
    if (map.ores) {
      for (const ore of map.ores) {
        renderables.push({
          type: 'ore',
          sortY: ore.y,
          data: ore
        });
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
    
    // 按 Y 座標排序（Y 小的先畫）
    renderables.sort((a, b) => a.sortY - b.sortY);
    
    // 依序渲染
    for (const item of renderables) {
      switch (item.type) {
        case 'north_wall':
          this.building.renderInteriorNorthWall(item.data.building, item.data.opacity);
          break;
        case 'south_wall':
          this.building.renderBuilding2_5D(item.data.building, item.data.opacity);
          break;
        case 'low_wall':
          this.building.renderSingleLowWall(item.data, item.data.opacity);
          break;
        case 'villager':
          this.entity.renderSingleVillager(item.data.villager, item.data.isSelected);
          break;
        case 'furniture':
          this.furniture.renderSingle(item.data, villagers);
          break;
        case 'tree':
          this.object.renderSingleObject(item.data);
          break;
        case 'bush_back':
          this.object.renderBushBack(
            item.data.x * this.tileSize - this.camera.x + this.camera.offsetX,
            item.data.y * this.tileSize - this.camera.y + this.camera.offsetY,
            this.tileSize,
            item.data
          );
          break;
        case 'bush_front':
          this.object.renderBushFront(
            item.data.x * this.tileSize - this.camera.x + this.camera.offsetX,
            item.data.y * this.tileSize - this.camera.y + this.camera.offsetY,
            this.tileSize,
            item.data
          );
          break;
        case 'crop_back':
          this.object.renderCropBack(
            item.data.x * this.tileSize - this.camera.x + this.camera.offsetX,
            item.data.y * this.tileSize - this.camera.y + this.camera.offsetY,
            this.tileSize,
            item.data
          );
          break;
        case 'crop_front':
          this.object.renderCropFront(
            item.data.x * this.tileSize - this.camera.x + this.camera.offsetX,
            item.data.y * this.tileSize - this.camera.y + this.camera.offsetY,
            this.tileSize,
            item.data
          );
          break;
        case 'ore':
          this.object.renderOre(
            item.data.x * this.tileSize - this.camera.x + this.camera.offsetX,
            item.data.y * this.tileSize - this.camera.y + this.camera.offsetY,
            this.tileSize,
            item.data
          );
          break;
        case 'sheep':
          this.entity.renderSingleSheep(item.data);
          break;
      }
    }
    
    // === 泡泡對話框獨立層 ===
    // 泡泡不受 Y-sort 影響，永遠顯示在最上層
    // 按建立時間排序，新的泡泡覆蓋舊的
    const bubbles = [];
    for (const villager of villagers) {
      if (villager.bubble) {
        bubbles.push({
          villager,
          createdAt: villager.bubble.createdAt || 0
        });
      }
    }
    
    // 按時間排序（早的先渲染，晚的後渲染 = 在上面）
    bubbles.sort((a, b) => a.createdAt - b.createdAt);
    
    for (const { villager } of bubbles) {
      this.ui.renderSingleBubble(villager);
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
