/**
 * 村民管理器 - 管理所有 NPC 村民（後端驅動模式）
 */

import { Villager } from './Villager.js';

export class VillagerManager {
  constructor(map) {
    this.map = map;
    this.villagers = [];
  }

  
  /**
   * 取得指定位置的村民
   */
  getVillagerAt(tileX, tileY) {
    for (const villager of this.villagers) {
      const vx = Math.floor(villager.x);
      const vy = Math.floor(villager.y);
      
      if (vx === tileX && vy === tileY) {
        return villager;
      }
    }
    return null;
  }
  
  /**
   * 取得附近的村民
   */
  getNearbyVillagers(x, y, radius) {
    return this.villagers.filter(v => {
      const dist = Math.abs(v.x - x) + Math.abs(v.y - y);
      return dist <= radius;
    });
  }
  
  /**
   * 根據 ID 取得村民
   */
  getVillagerById(id) {
    return this.villagers.find(v => v.id === id);
  }
  
  /**
   * 從後端資料載入村民
   */
  loadFromBackend(villagersData) {
    this.villagers = [];
    
    for (const data of villagersData) {
      const villager = new Villager({
        id: data.id,
        name: data.name,
        x: data.x,
        y: data.y,
        occupation: data.occupation
      });
      
      // 載入額外資料
      if (data.stats) villager.stats = data.stats;
      if (data.personality) villager.personality = data.personality;
      if (data.state) villager.state = data.state;
      
      this.villagers.push(villager);
    }
  }
  
  /**
   * 同步後端狀態
   */
  syncFromBackend(villagersData, selectedVillagerId = null) {
    for (const data of villagersData) {
      const villager = this.getVillagerById(data.id);
      if (villager) {
        // 如果是選中的村民，印出行為日誌
        if (selectedVillagerId && villager.id === selectedVillagerId) {
          const oldStats = villager.stats || {};
          const newStats = data.stats || {};
          
          // 檢查狀態變化
          if (villager.state !== data.state) {
            console.log(`👁️ [${villager.name}] 狀態: ${villager.state} → ${data.state}`);
          }
          
          // 檢查數值變化
          const energyDiff = (newStats.energy || 0) - (oldStats.energy || 0);
          const satietyDiff = (newStats.satiety || 0) - (oldStats.satiety || 0);
          const socialDiff = (newStats.social || 0) - (oldStats.social || 0);
          
          if (Math.abs(energyDiff) > 1) {
            console.log(`👁️ [${villager.name}] 體力: ${oldStats.energy?.toFixed(0)} → ${newStats.energy?.toFixed(0)} (${energyDiff > 0 ? '+' : ''}${energyDiff.toFixed(0)})`);
          }
          if (Math.abs(satietyDiff) > 1) {
            console.log(`👁️ [${villager.name}] 飽足: ${oldStats.satiety?.toFixed(0)} → ${newStats.satiety?.toFixed(0)} (${satietyDiff > 0 ? '+' : ''}${satietyDiff.toFixed(0)})`);
          }
          if (Math.abs(socialDiff) > 1) {
            console.log(`👁️ [${villager.name}] 社交: ${oldStats.social?.toFixed(0)} → ${newStats.social?.toFixed(0)} (${socialDiff > 0 ? '+' : ''}${socialDiff.toFixed(0)})`);
          }
          
          // 印出目標位置
          if (data.target && (!villager.moveTarget || 
              data.target[0] !== villager.moveTarget[0] || 
              data.target[1] !== villager.moveTarget[1])) {
            console.log(`👁️ [${villager.name}] 移動目標: (${data.target[0]}, ${data.target[1]})`);
          }
          
          // 印出任務隊列變化
          const oldTasks = JSON.stringify(villager.tasks || []);
          const newTasks = JSON.stringify(data.tasks || []);
          if (oldTasks !== newTasks) {
            console.log(`👁️ [${villager.name}] 任務隊列: ${newTasks}`);
          }
        }
        
        // 設定目標位置（用於插值）
        villager.targetX = data.x;
        villager.targetY = data.y;
        villager.state = data.state;
        
        // 保存移動目標（用於顯示路徑）
        villager.moveTarget = data.target;
        
        // 保存任務隊列
        villager.tasks = data.tasks;
        
        // 同步狀態數值
        if (data.stats) {
          villager.stats = data.stats;
        }
        
        // 同步記憶和關係（用於 Dashboard）
        if (data.memories) {
          villager.memories = data.memories;
        }
        if (data.relationships) {
          villager.relationships = data.relationships;
        }
        if (data.occupation) {
          villager.occupation = data.occupation;
        }
        
        // 同步個人資料（用於 Dashboard）
        if (data.age) {
          villager.age = data.age;
        }
        if (data.personality) {
          villager.personality = data.personality;
        }
        if (data.preferences) {
          villager.preferences = data.preferences;
        }
        
        // 同步經濟資料
        if (data.inventory !== undefined) {
          villager.inventory = data.inventory;
        }
        if (data.money !== undefined) {
          villager.money = data.money;
        }
      }
    }
  }
  
  /**
   * 更新動畫（後端模式用，只做插值）
   */
  updateAnimation(deltaTime) {
    const lerpSpeed = 15; // 插值速度（越大越快跟上）
    
    for (const villager of this.villagers) {
      // 平滑插值到目標位置（後端控制移動，前端只做插值）
      if (villager.targetX !== undefined) {
        const dx = villager.targetX - villager.x;
        const dy = villager.targetY - villager.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        // 如果距離太遠（超過 3 格），直接跳到目標位置
        if (dist > 3) {
          villager.x = villager.targetX;
          villager.y = villager.targetY;
        } else {
          // 平滑插值
          villager.x += dx * lerpSpeed * deltaTime;
          villager.y += dy * lerpSpeed * deltaTime;
        }
      }
      
      // 更新泡泡狀態
      villager.updateBubble();
    }
  }
  
  /**
   * 顯示村民對話泡泡
   */
  showVillagerBubble(villagerId, text, type = 'speech', duration = 3000) {
    const villager = this.getVillagerById(villagerId);
    if (villager) {
      villager.showBubble(text, type, duration);
    }
  }
}
