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
      
      item.innerHTML = `
        <span class="villager-name">${villager.name}</span>
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
          <span class="value">${(villager.personality || []).join(', ') || '普通'}</span>
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
          <span class="label">飢餓</span>
          <span class="value">${Math.floor(stats.hunger || 0)}%</span>
        </div>
        <div class="detail-row">
          <span class="label">社交</span>
          <span class="value">${Math.floor(stats.social || 0)}%</span>
        </div>
        <div class="detail-row">
          <span class="label">快樂</span>
          <span class="value">${Math.floor(stats.happiness || 0)}%</span>
        </div>
      </div>
      
      <!-- 任務隊列 -->
      <div class="detail-section">
        <div class="detail-title">📝 任務隊列</div>
        <div class="task-list">
          ${tasks.length > 0 
            ? tasks.map((task, i) => `<div class="task-item">${i + 1}. ${task}</div>`).join('')
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
    const occupationMap = {
      'tavern': '酒保',
      'church': '神父',
      'market': '商人',
      'blacksmith': '鐵匠',
      'bakery': '麵包師',
      'butcher_shop': '屠夫',
      'clinic': '醫師',
      'barber_shop': '理髮師',
      'weaver_shop': '織工',
      'pottery': '陶匠',
      'tannery': '皮革匠',
      'farm': '農夫',
      'dock': '漁夫',
      'house': '無業'
    };
    return occupationMap[occupation] || occupation || '村民';
  }
  
  /**
   * 狀態文字轉換
   */
  getStateText(state) {
    const stateMap = {
      'idle': '閒置',
      'walking': '行走',
      'talking': '聊天',
      'eating': '進食',
      'eat': '進食',
      'working': '工作',
      'work': '工作',
      'resting': '休息',
      'rest': '休息',
      'socializing': '社交',
      'socialize': '社交',
      'waiting': '等待',
      'waiting_social': '等人',
      'initiate_chat': '找人聊天',
      'move_to_villager': '找人中'
    };
    return stateMap[state] || state || '閒置';
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
        state: v.state
      }));
      this.updateVillagerList(villagers);
    }
    
    // 如果有選中村民，更新詳情
    if (this.selectedVillagerId) {
      this.updateDetails();
    }
  }
}
