import { PERSONALITY_NAMES, TASK_NAMES, STATE_NAMES, OCCUPATION_NAMES, ITEM_ICONS } from '../entities/Villager.js';

/**
 * 村民 Dashboard - 顯示村民列表和詳細資訊
 */
export class Dashboard {
  constructor(game) {
    this.game = game;
    this.selectedVillagerId = null;
    this.isCollapsed = false;
    
    this.container = document.getElementById('dashboard');
    this.header = document.getElementById('dashboard-header');
    this.toggle = document.getElementById('dashboard-toggle');
    this.listContainer = document.getElementById('villager-list');
    this.detailsContainer = document.getElementById('villager-details');
    
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    // 點擊標題折疊/展開
    this.header.addEventListener('click', () => {
      this.isCollapsed = !this.isCollapsed;
      this.toggle.textContent = this.isCollapsed ? '▶' : '▼';
      this.listContainer.style.display = this.isCollapsed ? 'none' : 'block';
      this.detailsContainer.style.display = this.isCollapsed ? 'none' : 'block';
    });
  }
  
  /**
   * 更新村民列表
   */
  updateVillagerList(villagers) {
    this.listContainer.innerHTML = '';
    
    for (const villager of villagers) {
      const item = document.createElement('div');
      item.className = 'villager-item' + (villager.id === this.selectedVillagerId ? ' selected' : '');
      item.dataset.villagerId = villager.id;
      
      const stateText = this.getStateText(villager.state);
      const stateClass = villager.state || 'idle';
      
      const occupationText = this.getOccupationText(villager.occupation);
      
      item.innerHTML = `
        <span class="villager-name">${villager.name} (${occupationText})</span>
        <span class="villager-state ${stateClass}">${stateText}</span>
      `;
      
      item.addEventListener('click', () => {
        this.selectVillager(villager.id);
      });
      
      this.listContainer.appendChild(item);
    }
  }
  
  /**
   * 選擇村民
   */
  selectVillager(villagerId) {
    this.selectedVillagerId = villagerId;
    
    // 更新列表選中狀態
    const items = this.listContainer.querySelectorAll('.villager-item');
    items.forEach(item => {
      item.classList.toggle('selected', item.dataset.villagerId === villagerId);
    });
    
    // 通知遊戲追蹤這個村民
    if (this.game) {
      this.game.selectVillagerById(villagerId);
    }
    
    // 更新詳細資訊
    this.updateDetails();
  }
  
  /**
   * 更新詳細資訊面板
   */
  updateDetails() {
    if (!this.selectedVillagerId || !this.game) {
      this.detailsContainer.innerHTML = '<div id="no-selection">點擊村民查看詳情</div>';
      return;
    }
    
    const villager = this.game.villagerManager.getVillagerById(this.selectedVillagerId);
    if (!villager) {
      this.detailsContainer.innerHTML = '<div id="no-selection">找不到村民</div>';
      return;
    }
    
    const stats = villager.stats || {};
    const tasks = villager.tasks || [];
    const memories = villager.memories || [];
    const relationships = villager.relationships || {};
    const preferences = villager.preferences || {};
    
    let html = `
      <!-- 基本資訊 -->
      <div class="detail-section">
        <div class="detail-title">📋 基本資訊</div>
        <div class="detail-row">
          <span class="label">姓名</span>
          <span class="value">${villager.name}</span>
        </div>
        <div class="detail-row">
          <span class="label">年齡</span>
          <span class="value">${villager.age || '?'} 歲</span>
        </div>
        <div class="detail-row">
          <span class="label">職業</span>
          <span class="value">${this.getOccupationText(villager.occupation)}</span>
        </div>
        <div class="detail-row">
          <span class="label">性格</span>
          <span class="value">${this.getPersonalityText(villager.personality)}</span>
        </div>
        <div class="detail-row">
          <span class="label">狀態</span>
          <span class="value">${this.getStateText(villager.state)}</span>
        </div>
        <div class="detail-row">
          <span class="label">位置</span>
          <span class="value">(${Math.floor(villager.x)}, ${Math.floor(villager.y)})</span>
        </div>
      </div>
      
      <!-- 喜好 -->
      <div class="detail-section">
        <div class="detail-title">💜 喜好</div>
        <div class="detail-row">
          <span class="label">興趣</span>
          <span class="value">${(preferences.hobbies || []).join(', ') || '無'}</span>
        </div>
        <div class="detail-row">
          <span class="label">喜歡食物</span>
          <span class="value">${(preferences.favorite_foods || []).join(', ') || '無'}</span>
        </div>
        <div class="detail-row">
          <span class="label">討厭</span>
          <span class="value">${(preferences.dislikes || []).join(', ') || '無'}</span>
        </div>
      </div>
      
      <!-- 數值 -->
      <div class="detail-section">
        <div class="detail-title">📊 數值</div>
        <div class="detail-row">
          <span class="label">體力</span>
          <span class="value">${Math.floor(stats.energy || 0)}%</span>
        </div>
        <div class="detail-row">
          <span class="label">飽足</span>
          <span class="value">${Math.floor(100 - (stats.hunger || 0))}%</span>
        </div>
        <div class="detail-row">
          <span class="label">社交</span>
          <span class="value">${Math.floor(stats.social || 0)}%</span>
        </div>
        <div class="detail-row">
          <span class="label">心情</span>
          <span class="value">${Math.floor(stats.happiness || 0)}%</span>
        </div>
      </div>
      
      <!-- 背包 -->
      <div class="detail-section">
        <div class="detail-title">🎒 背包 (💰 $${villager.money || 0})</div>
        <div class="inventory-grid">
          ${this.renderInventory(villager.inventory || [null, null, null, null, null])}
        </div>
      </div>
      
      <!-- 任務隊列 -->
      <div class="detail-section">
        <div class="detail-title">📝 任務隊列</div>
        <div class="task-list">
          ${tasks.length > 0 
            ? tasks.map((task, i) => `<div class="task-item">${i + 1}. ${this.getTaskText(task)}</div>`).join('')
            : '<div class="task-item">無任務</div>'
          }
        </div>
      </div>
      
      <!-- 關係 -->
      <div class="detail-section">
        <div class="detail-title">💛 關係</div>
        <div class="relationship-list">
          ${this.renderRelationships(relationships)}
        </div>
      </div>
      
      <!-- 記憶 -->
      <div class="detail-section">
        <div class="detail-title">🧠 記憶</div>
        <div class="memory-list">
          ${this.renderMemories(memories)}
        </div>
      </div>
    `;
    
    this.detailsContainer.innerHTML = html;
  }
  
  /**
   * 渲染關係列表
   */
  renderRelationships(relationships) {
    const entries = Object.entries(relationships);
    if (entries.length === 0) {
      return '<div class="relationship-item">尚無關係</div>';
    }
    
    return entries.map(([id, rel]) => {
      const name = this.getVillagerNameById(id);
      const fam = rel.familiarity || 0;
      const aff = rel.affection || 0;
      return `
        <div class="relationship-item">
          <span class="relationship-name">${name}</span>
          <span class="relationship-stats">熟悉:${fam} 好感:${aff}</span>
        </div>
      `;
    }).join('');
  }
  
  /**
   * 渲染記憶列表
   */
  renderMemories(memories) {
    if (memories.length === 0) {
      return '<div class="memory-item">尚無記憶</div>';
    }
    
    // 顯示最近 5 條
    return memories.slice(-5).reverse().map(mem => {
      if (mem.type === 'conversation') {
        return `
          <div class="memory-item">
            和 <span class="memory-with">${mem.with}</span>: ${mem.summary || '聊天'}
            <small style="color:#666">(第${mem.day}天)</small>
          </div>
        `;
      }
      return `<div class="memory-item">${mem.summary || JSON.stringify(mem)}</div>`;
    }).join('');
  }
  
  /**
   * 渲染背包
   */
  renderInventory(inventory) {
    return inventory.map((slot, i) => {
      if (!slot) {
        return `<div class="inventory-slot empty">空</div>`;
      }
      
      const icon = ITEM_ICONS[slot.item_id] || '📦';
      const isTool = slot.durability !== undefined && slot.durability !== null;
      
      if (isTool) {
        // 工具顯示耐久度
        return `<div class="inventory-slot tool">
          <span class="item-icon">${icon}</span>
          <span class="item-durability">${slot.durability}%</span>
        </div>`;
      } else {
        // 一般物品顯示數量
        return `<div class="inventory-slot">
          <span class="item-icon">${icon}</span>
          <span class="item-quantity">x${slot.quantity}</span>
        </div>`;
      }
    }).join('');
  }
  
  /**
   * 根據 ID 取得村民名字
   */
  getVillagerNameById(id) {
    if (!this.game || !this.game.villagerManager) return id;
    const villager = this.game.villagerManager.getVillagerById(id);
    return villager ? villager.name : id;
  }
  
  /**
   * 職業文字轉換
   */
  getOccupationText(occupation) {
    return OCCUPATION_NAMES[occupation] || occupation || '村民';
  }
  
  /**
   * 性格文字轉換
   */
  getPersonalityText(personality) {
    if (!personality || personality.length === 0) return '普通';
    return personality.map(p => PERSONALITY_NAMES[p] || p).join('、');
  }
  
  /**
   * 任務文字轉換
   */
  getTaskText(task) {
    if (typeof task === 'string') {
      return TASK_NAMES[task] || task;
    }
    // 任務是物件時
    const taskType = task.type || task;
    return TASK_NAMES[taskType] || taskType;
  }
  
  /**
   * 狀態文字轉換
   */
  getStateText(state) {
    return STATE_NAMES[state] || state || '閒置';
  }
  
  /**
   * 定期更新（每秒）
   */
  update() {
    // 從 VillagerManager 取得村民資料
    if (this.game && this.game.villagerManager) {
      const villagers = this.game.villagerManager.villagers.map(v => ({
        id: v.id,
        name: v.name,
        state: v.state,
        occupation: v.occupation
      }));
      this.updateVillagerList(villagers);
    }
    
    // 如果有選中村民，更新詳情
    if (this.selectedVillagerId) {
      this.updateDetails();
    }
  }
}
