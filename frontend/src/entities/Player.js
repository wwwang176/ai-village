/**
 * 玩家類 - 玩家控制的角色
 */

import { Entity } from './Entity.js';

export class Player extends Entity {
  constructor(config) {
    super(config);
    
    this.name = config.name || '玩家';
    this.isPlayer = true;
    
    // 玩家特有屬性
    this.color = '#4a90d9';
    
    // 狀態數值
    this.stats = {
      energy: 100,
      satiety: 100,
      social: 50,
      happiness: 70,
      health: 100,
      money: 50
    };
    
    // 物品欄
    this.inventory = [];
    
    // 當前互動目標
    this.interactTarget = null;
    
    // 關係
    this.relationships = {};
  }
  
  /**
   * 更新玩家
   */
  update(deltaTime, map) {
    super.update(deltaTime, map);
    
    // 更新狀態
    this.updateStats(deltaTime);
  }
  
  /**
   * 更新狀態數值
   */
  updateStats(deltaTime) {
    // 飽足度緩慢下降
    this.stats.satiety = Math.max(0, this.stats.satiety - deltaTime * 0.3);
    
    // 體力緩慢下降
    this.stats.energy = Math.max(0, this.stats.energy - deltaTime * 0.05);
    
    // 飢餓影響心情度和健康
    if (this.stats.satiety < 20) {
      this.stats.happiness = Math.max(0, this.stats.happiness - deltaTime * 0.2);
      this.stats.health = Math.max(0, this.stats.health - deltaTime * 0.1);
    }
    
    // 疲勞影響心情度
    if (this.stats.energy < 20) {
      this.stats.happiness = Math.max(0, this.stats.happiness - deltaTime * 0.1);
    }
  }
  
  /**
   * 執行動作
   */
  performAction(action, target) {
    console.log(`執行動作: ${action.name}`);
    
    // 檢查需求
    if (action.cost && this.stats.money < action.cost) {
      console.log('金錢不足');
      return false;
    }
    
    // 扣除成本
    if (action.cost) {
      this.stats.money -= action.cost;
    }
    
    // 應用效果
    if (action.effects) {
      for (const [stat, value] of Object.entries(action.effects)) {
        if (this.stats[stat] !== undefined) {
          this.stats[stat] = Math.max(0, Math.min(100, this.stats[stat] + value));
        }
      }
    }
    
    return true;
  }
  
  /**
   * 取得對村民的關係
   */
  getRelationship(villagerId) {
    if (!this.relationships[villagerId]) {
      this.relationships[villagerId] = {
        affection: 0,
        trust: 0,
        familiarity: 0,
        tags: ['stranger']
      };
    }
    return this.relationships[villagerId];
  }
  
  /**
   * 更新與村民的關係
   */
  updateRelationship(villagerId, changes) {
    const rel = this.getRelationship(villagerId);
    
    if (changes.affection) rel.affection += changes.affection;
    if (changes.trust) rel.trust += changes.trust;
    if (changes.familiarity) rel.familiarity += changes.familiarity;
    
    // 限制範圍
    rel.affection = Math.max(-100, Math.min(100, rel.affection));
    rel.trust = Math.max(-100, Math.min(100, rel.trust));
    rel.familiarity = Math.max(0, Math.min(100, rel.familiarity));
  }
}
