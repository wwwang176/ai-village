/**
 * 村民管理器 - 管理所有 NPC 村民
 */

import { Villager } from './Villager.js';

export class VillagerManager {
  constructor(map) {
    this.map = map;
    this.villagers = [];
  }
  
  /**
   * 生成村民
   */
  generateVillagers(count, buildings) {
    // 先為每個需要工作人員的建築分配村民
    const workBuildings = buildings.filter(b => 
      ['tavern', 'church', 'market', 'blacksmith', 'bakery', 'farm'].includes(b.type)
    );
    
    const houses = buildings.filter(b => b.type === 'house');
    
    for (const building of workBuildings) {
      // 每個工作建築分配一個工人
      const house = houses[this.villagers.length % houses.length];
      
      const villager = new Villager({
        id: `villager_${this.villagers.length}`,
        x: building.doorX,
        y: building.doorY + 1,
        occupation: building.type,
        workplace: building.id,
        residence: house?.id || null
      });
      
      this.villagers.push(villager);
    }
    
    // 填充剩餘村民
    while (this.villagers.length < count) {
      const house = houses[this.villagers.length % houses.length];
      const spawnPoint = this.map.getRandomSpawnPoint();
      
      const villager = new Villager({
        id: `villager_${this.villagers.length}`,
        x: spawnPoint.x,
        y: spawnPoint.y,
        occupation: 'house',
        workplace: null,
        residence: house?.id || null
      });
      
      this.villagers.push(villager);
    }
    
    // 建立初始關係（鄰居、同事）
    this.initializeRelationships();
  }
  
  /**
   * 初始化村民間關係
   */
  initializeRelationships() {
    for (let i = 0; i < this.villagers.length; i++) {
      for (let j = i + 1; j < this.villagers.length; j++) {
        const a = this.villagers[i];
        const b = this.villagers[j];
        
        // 同住所 = 家人
        if (a.residence && a.residence === b.residence) {
          a.relationships[b.id] = {
            affection: 50 + Math.random() * 30,
            trust: 60,
            familiarity: 80,
            tags: ['family']
          };
          b.relationships[a.id] = {
            affection: 50 + Math.random() * 30,
            trust: 60,
            familiarity: 80,
            tags: ['family']
          };
        }
        // 同工作地 = 同事
        else if (a.workplace && a.workplace === b.workplace) {
          a.relationships[b.id] = {
            affection: 10 + Math.random() * 20,
            trust: 20,
            familiarity: 40,
            tags: ['colleague']
          };
          b.relationships[a.id] = {
            affection: 10 + Math.random() * 20,
            trust: 20,
            familiarity: 40,
            tags: ['colleague']
          };
        }
      }
    }
  }
  
  /**
   * 更新所有村民
   */
  update(deltaTime, map, timeSystem) {
    for (const villager of this.villagers) {
      villager.update(deltaTime, map, timeSystem);
    }
    
    // 檢查社交碰撞
    this.checkSocialEncounters();
  }
  
  /**
   * 檢查村民相遇事件
   */
  checkSocialEncounters() {
    const encounterDistance = 1.5; // 格
    
    for (let i = 0; i < this.villagers.length; i++) {
      for (let j = i + 1; j < this.villagers.length; j++) {
        const a = this.villagers[i];
        const b = this.villagers[j];
        
        // 跳過正在忙碌的村民
        if (a.state !== 'idle' && a.state !== 'walking') continue;
        if (b.state !== 'idle' && b.state !== 'walking') continue;
        
        const dist = a.distanceTo(b);
        
        if (dist < encounterDistance) {
          // 觸發相遇事件（之後接入 AI）
          this.handleEncounter(a, b);
        }
      }
    }
  }
  
  /**
   * 處理村民相遇
   */
  handleEncounter(villagerA, villagerB) {
    // 避免太頻繁觸發
    const now = Date.now();
    if (villagerA._lastEncounter && now - villagerA._lastEncounter < 5000) return;
    if (villagerB._lastEncounter && now - villagerB._lastEncounter < 5000) return;
    
    villagerA._lastEncounter = now;
    villagerB._lastEncounter = now;
    
    // 簡單實作：更新熟悉度
    villagerA.updateRelationship(villagerB.id, { familiarity: 1 });
    villagerB.updateRelationship(villagerA.id, { familiarity: 1 });
    
    // 顯示名字
    villagerA.showName = true;
    villagerB.showName = true;
    
    // 顯示對話泡泡
    const greetings = [
      ['你好！', '嗨！'],
      ['早安！', '早啊～'],
      ['最近好嗎？', '還不錯'],
      ['天氣真好', '是啊'],
    ];
    const pair = greetings[Math.floor(Math.random() * greetings.length)];
    
    villagerA.showBubble(pair[0], 'speech', 2500);
    setTimeout(() => {
      villagerB.showBubble(pair[1], 'speech', 2500);
    }, 800);
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
          const hungerDiff = (newStats.hunger || 0) - (oldStats.hunger || 0);
          const socialDiff = (newStats.social || 0) - (oldStats.social || 0);
          
          if (Math.abs(energyDiff) > 1) {
            console.log(`👁️ [${villager.name}] 體力: ${oldStats.energy?.toFixed(0)} → ${newStats.energy?.toFixed(0)} (${energyDiff > 0 ? '+' : ''}${energyDiff.toFixed(0)})`);
          }
          if (Math.abs(hungerDiff) > 1) {
            console.log(`👁️ [${villager.name}] 飢餓: ${oldStats.hunger?.toFixed(0)} → ${newStats.hunger?.toFixed(0)} (${hungerDiff > 0 ? '+' : ''}${hungerDiff.toFixed(0)})`);
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
      // 如果正在對話或等待社交，不移動
      if (villager.state === 'talking' || villager.state === 'waiting_social') {
        villager.updateBubble();
        continue;
      }
      
      // 平滑插值到目標位置
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
