/**
 * 村民類 - NPC 角色
 */

import { Entity } from './Entity.js';

// 性格特質池
const PERSONALITIES = {
  positive: ['friendly', 'hardworking', 'generous', 'optimistic', 'curious'],
  negative: ['greedy', 'lazy', 'suspicious', 'grumpy', 'gossip'],
  neutral: ['introvert', 'extrovert', 'romantic', 'religious']
};

// 任務類型中文翻譯
export const TASK_NAMES = {
  move: '移動',
  move_to_villager: '前往村民',
  eat: '吃東西',
  rest: '休息',
  work: '工作',
  wait: '等待',
  socialize: '社交',
  pickup: '撿取物品',
  drop_item: '放下物品',
  drop_one_item: '放下物品',
  buy_tool: '購買工具',
  buy_material: '購買原料',
  buy_food: '購買食物',
  sell_to_merchant: '販賣給商人',
  sell_excess: '販賣過剩物品',
  cook: '烹飪',
  shear_sheep: '剪羊毛',
  buy_sheep: '購買羊',
  slaughter_sheep: '屠宰羊',
};

// 物品圖示
export const ITEM_ICONS = {
  // 工具
  hoe: '⛏️',
  pickaxe: '⛏️',
  axe: '🪓',
  shears: '✂️',
  cleaver: '🔪',
  hammer: '🔨',
  saw: '🪚',
  scraper: '🔪',
  // 原料
  grain: '🌾',
  livestock: '🐄',
  ore: '🪨',
  wood: '🪵',
  wool: '🧶',
  hide: '☁️',
  // 中間產物
  flour: '🌫️',
  meat_raw: '🥩',
  iron: '🔩',
  plank: '📏',
  cloth: '🧵',
  leather: '🟤',
  // 成品
  bread: '🍞',
  meat: '🍖',
  clothes: '👕',
  furniture: '🪑',
  beer: '🍺',
};

// 狀態中文翻譯
export const STATE_NAMES = {
  idle: '閒置',
  walking: '行走',
  talking: '聊天',
  eating: '進食',
  eat: '進食',
  working: '工作',
  work: '工作',
  resting: '休息',
  rest: '休息',
  socializing: '社交',
  socialize: '社交',
  wait: '等待',
  waiting_social: '等人',
  initiate_chat: '找人聊天',
  move_to_villager: '找人中',
  // 任務狀態
  pickup: '撿取中',
  drop_item: '放下物品',
  drop_one_item: '放下物品',
  buy_tool: '購買工具',
  buy_material: '購買原料',
  buy_food: '購買食物',
  sell_to_merchant: '販賣中',
  sell_excess: '販賣中',
  cook: '烹飪中',
  shear_sheep: '剪羊毛',
  buy_sheep: '購買羊',
  slaughter_sheep: '屠宰羊',
};

// 職業中文翻譯
export const OCCUPATION_NAMES = {
  // 食物鏈
  farmer: '農夫',
  miller: '磨坊主',
  butcher: '屠夫',
  baker: '麵包師',
  // 器具鏈
  miner: '礦工',
  lumberjack: '伐木工',
  blacksmith: '鐵匠',
  carpenter: '木匠',
  // 服飾鏈
  shepherd: '牧羊人',
  weaver: '織工',
  tanner: '皮革匠',
  tailor: '裁縫',
  // 特殊
  merchant: '商人',
  bartender: '酒保',
  // 其他
  house: '無業',
};

// 性格特質中文翻譯（7 維度 × 正反面）
export const PERSONALITY_NAMES = {
  // 社交維度
  extrovert: '外向',
  introvert: '內向',
  // 態度維度
  friendly: '友善',
  grumpy: '暴躁',
  // 信任維度
  trusting: '信任',
  suspicious: '多疑',
  // 感情維度
  romantic: '浪漫',
  reserved: '矜持',
  // 勇氣維度
  brave: '勇敢',
  timid: '膽小',
  // 心態維度
  optimistic: '樂觀',
  pessimistic: '悲觀',
  // 作息維度
  early_bird: '早起',
  night_owl: '夜貓',
};

// 名字池
const NAMES = {
  male: ['艾德蒙', '約翰', '威廉', '亨利', '湯瑪斯', '羅伯特', '理查', '查爾斯', '喬治', '愛德華'],
  female: ['瑪莉', '伊莉莎白', '安娜', '凱薩琳', '艾瑪', '露西', '克萊兒', '蘇菲', '愛麗絲', '夏洛特']
};

// 職業與對應建築（13 種職業）
const OCCUPATIONS = {
  // 食物鏈
  farmer: { name: '農夫', color: '#228b22' },
  miller: { name: '磨坊主', color: '#d2b48c' },
  butcher: { name: '屠夫', color: '#8b0000' },
  baker: { name: '麵包師', color: '#d2691e' },
  
  // 器具鏈
  miner: { name: '礦工', color: '#4a4a4a' },
  lumberjack: { name: '伐木工', color: '#8b4513' },
  blacksmith: { name: '鐵匠', color: '#696969' },
  carpenter: { name: '木匠', color: '#a0522d' },
  
  // 服飾鏈
  shepherd: { name: '牧羊人', color: '#87ceeb' },
  weaver: { name: '織工', color: '#9370db' },
  tanner: { name: '皮革匠', color: '#8b7355' },
  tailor: { name: '裁縫', color: '#ff69b4' },
  
  // 特殊
  merchant: { name: '商人', color: '#daa520' },
};

export class Villager extends Entity {
  constructor(config) {
    super(config);
    
    // 隨機性別和名字
    this.gender = config.gender || (Math.random() > 0.5 ? 'male' : 'female');
    this.name = config.name || this.generateName();
    this.age = config.age || Math.floor(Math.random() * 40) + 18;
    
    // 職業
    this.occupation = config.occupation || 'villager';
    this.workplace = config.workplace || null;    // 工作地點建築 ID
    this.residence = config.residence || null;    // 住所建築 ID
    
    // 外觀
    this.color = config.color || OCCUPATIONS[this.occupation]?.color || '#8b7355';
    this.showName = false;
    
    // 性格特質
    this.personality = config.personality || this.generatePersonality();
    
    // 狀態數值
    this.stats = {
      energy: 80 + Math.random() * 20,
      hunger: Math.random() * 30,
      social: 40 + Math.random() * 20,
      happiness: 50 + Math.random() * 30,
      health: 80 + Math.random() * 20
    };
    
    // 行為狀態
    this.state = 'idle';  // idle, walking, working, interacting, sleeping
    this.currentAction = null;
    this.actionProgress = 0;
    this.targetObject = null;
    
    // 記憶系統
    this.memories = [];
    this.maxMemories = 20;
    
    // 關係 (villager ID -> relationship data)
    this.relationships = {};
    
    // AI 決策
    this.lastDecisionTime = 0;
    this.decisionCooldown = 3; // 秒
    
    // 對話泡泡
    this.bubble = null;         // { text, type, expireTime }
    this.currentMood = null;    // 當前心情
    
    // 後端模式用
    this.targetX = this.x;
    this.targetY = this.y;
  }
  
  /**
   * 顯示對話泡泡
   * @param {string} text - 顯示文字
   * @param {string} type - 類型: 'speech'(對話), 'thought'(思考), 'action'(行為)
   * @param {number} duration - 顯示時間(毫秒)
   */
  showBubble(text, type = 'speech', duration = 3000) {
    this.bubble = {
      text: text,
      type: type,
      expireTime: Date.now() + duration
    };
  }
  
  /**
   * 清除對話泡泡
   */
  clearBubble() {
    this.bubble = null;
  }
  
  /**
   * 更新泡泡狀態（檢查是否過期）
   */
  updateBubble() {
    if (this.bubble && Date.now() > this.bubble.expireTime) {
      this.bubble = null;
    }
  }
  
  /**
   * 從後端決策設定目標
   */
  setGoalFromDecision(decision) {
    if (decision.target) {
      this.targetX = decision.target.x;
      this.targetY = decision.target.y;
      this.state = 'walking';
    }
    
    // 顯示行為泡泡
    if (decision.reason) {
      this.showBubble(decision.reason, 'thought', 4000);
    }
  }
  
  generateName() {
    const pool = this.gender === 'male' ? NAMES.male : NAMES.female;
    return pool[Math.floor(Math.random() * pool.length)];
  }
  
  generatePersonality() {
    const traits = [];
    
    // 隨機 1 個正面特質
    traits.push(PERSONALITIES.positive[Math.floor(Math.random() * PERSONALITIES.positive.length)]);
    
    // 50% 機會加一個負面特質
    if (Math.random() > 0.5) {
      traits.push(PERSONALITIES.negative[Math.floor(Math.random() * PERSONALITIES.negative.length)]);
    }
    
    // 50% 機會加一個中性特質
    if (Math.random() > 0.5) {
      traits.push(PERSONALITIES.neutral[Math.floor(Math.random() * PERSONALITIES.neutral.length)]);
    }
    
    return traits;
  }
  
  /**
   * 更新村民
   */
  update(deltaTime, map, timeSystem) {
    super.update(deltaTime, map);
    
    // 更新狀態數值
    this.updateStats(deltaTime);
    
    // 更新泡泡
    this.updateBubble();
    
    // 更新行為
    switch (this.state) {
      case 'idle':
        this.handleIdle(deltaTime, map, timeSystem);
        break;
      case 'walking':
        // 由 Entity 基類處理移動
        if (this.path.length === 0 && this.pathIndex === 0) {
          this.state = 'idle';
        }
        break;
      case 'working':
      case 'interacting':
        this.handleAction(deltaTime);
        break;
      case 'sleeping':
        this.handleSleep(deltaTime, timeSystem);
        break;
    }
  }
  
  /**
   * 更新狀態數值
   */
  updateStats(deltaTime) {
    // 飢餓緩慢增加
    this.stats.hunger = Math.min(100, this.stats.hunger + deltaTime * 0.5);
    
    // 如果很餓，快樂度下降
    if (this.stats.hunger > 70) {
      this.stats.happiness = Math.max(0, this.stats.happiness - deltaTime * 0.3);
    }
    
    // 社交需求緩慢增加
    if (!this.personality.includes('introvert')) {
      this.stats.social = Math.max(0, this.stats.social - deltaTime * 0.2);
    }
    
    // 體力緩慢下降
    if (this.state !== 'sleeping') {
      this.stats.energy = Math.max(0, this.stats.energy - deltaTime * 0.1);
    }
  }
  
  /**
   * 處理閒置狀態
   */
  handleIdle(deltaTime, map, timeSystem) {
    // 簡單 AI：根據需求選擇行為（之後會替換成 GPT API）
    const now = Date.now() / 1000;
    
    if (now - this.lastDecisionTime < this.decisionCooldown) {
      return;
    }
    
    this.lastDecisionTime = now;
    
    // 決策邏輯
    this.makeDecision(map, timeSystem);
  }
  
  /**
   * 簡單決策（之後替換成 GPT API）
   */
  makeDecision(map, timeSystem) {
    // 睡眠時間
    if (timeSystem && timeSystem.isSleepTime() && this.stats.energy < 50) {
      this.showBubble('好睏...該睡了', 'thought', 3000);
      this.goToSleep(map);
      return;
    }
    
    // 非常餓
    if (this.stats.hunger > 80) {
      this.showBubble('肚子好餓', 'thought', 3000);
      this.goEat(map);
      return;
    }
    
    // 非常累
    if (this.stats.energy < 20) {
      this.showBubble('好累...', 'thought', 3000);
      this.goRest(map);
      return;
    }
    
    // 工作時間
    if (timeSystem && timeSystem.isWorkHour() && this.workplace) {
      this.showBubble('該工作了', 'thought', 2500);
      this.goToWork(map);
      return;
    }
    
    // 社交需求
    if (this.stats.social < 30) {
      this.showBubble('想找人聊聊', 'thought', 3000);
      this.goSocialize(map);
      return;
    }
    
    // 隨機閒逛
    const thoughts = ['到處走走', '今天天氣不錯', '...', '嗯~♪'];
    this.showBubble(thoughts[Math.floor(Math.random() * thoughts.length)], 'thought', 2500);
    this.wander(map);
  }
  
  /**
   * 去睡覺
   */
  goToSleep(map) {
    if (!this.residence) {
      this.wander(map);
      return;
    }
    
    const building = map.buildings.find(b => b.id === this.residence);
    if (building) {
      this.setGoal(building.doorX, building.doorY + 1, map, 'sleeping');
    }
  }
  
  /**
   * 去吃東西
   */
  goEat(map) {
    // 去酒館或家
    const tavern = map.buildings.find(b => b.type === 'tavern');
    if (tavern) {
      this.setGoal(tavern.doorX, tavern.doorY + 1, map, 'interacting');
    }
  }
  
  /**
   * 去休息
   */
  goRest(map) {
    // 找個椅子或回家
    this.goToSleep(map);
  }
  
  /**
   * 去工作
   */
  goToWork(map) {
    if (!this.workplace) {
      this.wander(map);
      return;
    }
    
    const building = map.buildings.find(b => b.id === this.workplace);
    if (building) {
      this.setGoal(building.doorX, building.doorY + 1, map, 'working');
    }
  }
  
  /**
   * 去社交
   */
  goSocialize(map) {
    // 去酒館或市集
    const socialSpots = map.buildings.filter(b => 
      b.type === 'tavern' || b.type === 'market' || b.type === 'church'
    );
    
    if (socialSpots.length > 0) {
      const spot = socialSpots[Math.floor(Math.random() * socialSpots.length)];
      this.setGoal(spot.doorX, spot.doorY + 1, map, 'interacting');
    }
  }
  
  /**
   * 隨機閒逛
   */
  wander(map) {
    // 隨機選一個可到達的點
    const range = 10;
    const currentX = Math.floor(this.x);
    const currentY = Math.floor(this.y);
    
    for (let i = 0; i < 10; i++) {
      const targetX = currentX + Math.floor(Math.random() * range * 2) - range;
      const targetY = currentY + Math.floor(Math.random() * range * 2) - range;
      
      if (map.isWalkable(targetX, targetY)) {
        this.setGoal(targetX, targetY, map, 'idle');
        return;
      }
    }
  }
  
  /**
   * 設定目標並計算路徑
   */
  setGoal(targetX, targetY, map, nextState) {
    // 這裡簡化處理，直接設定路徑點
    // 完整版應該使用 A* 演算法
    const path = this.simplePathTo(targetX, targetY, map);
    
    if (path.length > 0) {
      this.setPath(path);
      this.state = 'walking';
      this.nextState = nextState;
    }
  }
  
  /**
   * 簡單路徑（之後用 A* 替代）
   */
  simplePathTo(targetX, targetY, map) {
    const path = [];
    let x = Math.floor(this.x);
    let y = Math.floor(this.y);
    
    // 簡單直線路徑
    const steps = Math.max(Math.abs(targetX - x), Math.abs(targetY - y));
    
    for (let i = 1; i <= steps && i < 50; i++) {
      const nx = x + Math.sign(targetX - x);
      const ny = y + Math.sign(targetY - y);
      
      if (map.isWalkable(nx, ny)) {
        x = nx;
        y = ny;
        path.push({ x, y });
      } else if (map.isWalkable(nx, y)) {
        x = nx;
        path.push({ x, y });
      } else if (map.isWalkable(x, ny)) {
        y = ny;
        path.push({ x, y });
      } else {
        break;
      }
    }
    
    return path;
  }
  
  /**
   * 路徑完成
   */
  onPathComplete() {
    if (this.nextState) {
      this.state = this.nextState;
      this.nextState = null;
      
      if (this.state === 'working' || this.state === 'interacting') {
        this.actionProgress = 0;
        this.currentAction = { duration: 5000 + Math.random() * 5000 };
      } else if (this.state === 'sleeping') {
        this.actionProgress = 0;
      }
    } else {
      this.state = 'idle';
    }
  }
  
  /**
   * 處理動作進行中
   */
  handleAction(deltaTime) {
    if (!this.currentAction) {
      this.state = 'idle';
      return;
    }
    
    this.actionProgress += deltaTime * 1000;
    
    if (this.actionProgress >= this.currentAction.duration) {
      // 動作完成
      this.completeAction();
    }
  }
  
  /**
   * 完成動作
   */
  completeAction() {
    // 根據動作類型給予效果
    if (this.state === 'working') {
      this.stats.energy = Math.max(0, this.stats.energy - 10);
      // 可加入金錢系統
    } else if (this.state === 'interacting') {
      this.stats.social = Math.min(100, this.stats.social + 20);
      this.stats.happiness = Math.min(100, this.stats.happiness + 5);
    }
    
    this.currentAction = null;
    this.actionProgress = 0;
    this.state = 'idle';
  }
  
  /**
   * 處理睡眠
   */
  handleSleep(deltaTime, timeSystem) {
    // 恢復體力
    this.stats.energy = Math.min(100, this.stats.energy + deltaTime * 5);
    
    // 天亮或體力滿就醒來
    if (timeSystem && !timeSystem.isSleepTime() && this.stats.energy > 80) {
      this.state = 'idle';
    }
  }
  
  /**
   * 加入記憶
   */
  addMemory(event, sentiment = 'neutral') {
    this.memories.push({
      event,
      timestamp: Date.now(),
      sentiment
    });
    
    // 限制記憶數量
    if (this.memories.length > this.maxMemories) {
      this.memories.shift();
    }
  }
  
  /**
   * 取得對另一個村民的關係
   */
  getRelationship(otherId) {
    if (!this.relationships[otherId]) {
      this.relationships[otherId] = {
        affection: 0,
        trust: 0,
        familiarity: 0,
        tags: ['stranger']
      };
    }
    return this.relationships[otherId];
  }
  
  /**
   * 更新關係
   */
  updateRelationship(otherId, changes) {
    const rel = this.getRelationship(otherId);
    
    if (changes.affection) {
      rel.affection = Math.max(-100, Math.min(100, rel.affection + changes.affection));
    }
    if (changes.trust) {
      rel.trust = Math.max(-100, Math.min(100, rel.trust + changes.trust));
    }
    if (changes.familiarity) {
      rel.familiarity = Math.max(0, Math.min(100, rel.familiarity + changes.familiarity));
    }
    
    // 更新關係標籤
    this.updateRelationshipTags(rel);
  }
  
  updateRelationshipTags(rel) {
    const tags = [];
    
    if (rel.familiarity < 10) {
      tags.push('stranger');
    } else if (rel.familiarity < 30) {
      tags.push('acquaintance');
    } else {
      if (rel.affection > 30) {
        tags.push('friend');
      } else if (rel.affection < -30) {
        tags.push('rival');
      } else {
        tags.push('neighbor');
      }
    }
    
    rel.tags = tags;
  }
  
  /**
   * 取得用於 AI 決策的狀態摘要
   */
  getAISummary() {
    return {
      name: this.name,
      occupation: this.occupation,
      personality: this.personality,
      stats: { ...this.stats },
      currentState: this.state,
      recentMemories: this.memories.slice(-5).map(m => m.event)
    };
  }
}
