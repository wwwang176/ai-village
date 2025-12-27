/**
 * UI 管理器 - 管理遊戲介面
 */

export class UIManager {
  constructor(game) {
    this.game = game;
    
    // 取得 UI 元素
    this.actionMenu = document.getElementById('action-menu');
    this.statusBar = document.getElementById('status-bar');
    this.timeDisplay = document.getElementById('time-display');
    this.dialogBox = document.getElementById('dialog-box');
    
    this.currentTarget = null;
  }
  
  /**
   * 更新 UI
   */
  update(player, timeSystem) {
    this.updateStatusBar(player);
    this.updateTimeDisplay(timeSystem);
  }
  
  /**
   * 更新狀態列（顯示選中村民的狀態）
   */
  updateStatusBar(villager) {
    if (!this.statusBar) return;
    
    const nameEl = document.getElementById('villager-name');
    
    if (!villager) {
      // 沒有選中村民
      if (nameEl) nameEl.textContent = '點擊村民觀察';
      this.updateStatBar('energy', 0);
      this.updateStatBar('satiety', 0);
      this.updateStatBar('social', 0);
      this.updateStatBar('happiness', 0);
      return;
    }
    
    // 更新村民名字
    if (nameEl) {
      nameEl.textContent = `👁️ ${villager.name}`;
    }
    
    const stats = villager.stats || {};
    
    // 更新各狀態條
    this.updateStatBar('energy', stats.energy || 0);
    this.updateStatBar('satiety', stats.satiety || 0);
    this.updateStatBar('social', stats.social || 0);
    this.updateStatBar('happiness', stats.happiness || 0);
  }
  
  updateStatBar(statName, value) {
    const fill = this.statusBar.querySelector(`.stat-fill.${statName}`);
    const valueEl = document.getElementById(`${statName}-value`);
    const clampedValue = Math.max(0, Math.min(100, value));
    
    if (fill) {
      fill.style.width = `${clampedValue}%`;
    }
    if (valueEl) {
      valueEl.textContent = `${Math.round(clampedValue)}%`;
    }
  }
  
  /**
   * 更新時間顯示
   */
  updateTimeDisplay(timeSystem) {
    if (!timeSystem) return;
    
    // 更新時間文字（使用 #time-text span）
    const timeText = document.getElementById('time-text');
    if (timeText) {
      timeText.textContent = timeSystem.getTimeString();
    }
    
    // 根據時段改變顏色
    if (this.timeDisplay) {
      const period = timeSystem.getPeriod();
      switch (period) {
        case 'night':
          this.timeDisplay.style.color = '#8888ff';
          break;
        case 'dawn':
        case 'evening':
          this.timeDisplay.style.color = '#ffaa55';
          break;
        default:
          this.timeDisplay.style.color = '#ffd700';
      }
    }
  }
  
  /**
   * 顯示物件動作選單
   */
  showActionMenu(object, screenX, screenY) {
    if (!object.actions || object.actions.length === 0) return;
    
    this.currentTarget = object;
    
    // 清空選單
    this.actionMenu.innerHTML = '';
    
    // 標題
    const title = document.createElement('div');
    title.className = 'action-menu-title';
    title.textContent = object.name;
    this.actionMenu.appendChild(title);
    
    // 動作項目
    for (const action of object.actions) {
      const item = document.createElement('div');
      item.className = 'action-menu-item';
      item.textContent = action.name;
      
      // 檢查是否可執行
      const canPerform = this.canPerformAction(action);
      if (!canPerform) {
        item.classList.add('disabled');
      }
      
      item.addEventListener('click', () => {
        if (canPerform) {
          this.performAction(action, object);
          this.hideActionMenu();
        }
      });
      
      this.actionMenu.appendChild(item);
    }
    
    // 離開選項
    const leaveItem = document.createElement('div');
    leaveItem.className = 'action-menu-item';
    leaveItem.textContent = '離開';
    leaveItem.addEventListener('click', () => this.hideActionMenu());
    this.actionMenu.appendChild(leaveItem);
    
    // 定位選單
    this.actionMenu.style.left = `${screenX}px`;
    this.actionMenu.style.top = `${screenY}px`;
    this.actionMenu.style.display = 'block';
    
    // 確保選單不超出視窗
    const rect = this.actionMenu.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
      this.actionMenu.style.left = `${screenX - rect.width}px`;
    }
    if (rect.bottom > window.innerHeight) {
      this.actionMenu.style.top = `${screenY - rect.height}px`;
    }
  }
  
  /**
   * 顯示村民互動選單
   */
  showVillagerMenu(villager, screenX, screenY) {
    this.currentTarget = villager;
    
    // 清空選單
    this.actionMenu.innerHTML = '';
    
    // 標題
    const title = document.createElement('div');
    title.className = 'action-menu-title';
    title.textContent = `${villager.name} (${this.getOccupationName(villager.occupation)})`;
    this.actionMenu.appendChild(title);
    
    // 互動選項
    const actions = [
      { id: 'greet', name: '打招呼' },
      { id: 'chat', name: '聊天' },
      { id: 'ask_info', name: '打聽消息' }
    ];
    
    // 根據關係添加更多選項
    const rel = this.game.player.getRelationship(villager.id);
    if (rel.familiarity > 30) {
      actions.push({ id: 'give_gift', name: '送禮物' });
    }
    if (rel.affection > 50) {
      actions.push({ id: 'invite', name: '邀請一起做事' });
    }
    
    for (const action of actions) {
      const item = document.createElement('div');
      item.className = 'action-menu-item';
      item.textContent = action.name;
      
      item.addEventListener('click', () => {
        this.interactWithVillager(action, villager);
        this.hideActionMenu();
      });
      
      this.actionMenu.appendChild(item);
    }
    
    // 離開選項
    const leaveItem = document.createElement('div');
    leaveItem.className = 'action-menu-item';
    leaveItem.textContent = '離開';
    leaveItem.addEventListener('click', () => this.hideActionMenu());
    this.actionMenu.appendChild(leaveItem);
    
    // 定位選單
    this.actionMenu.style.left = `${screenX}px`;
    this.actionMenu.style.top = `${screenY}px`;
    this.actionMenu.style.display = 'block';
  }
  
  /**
   * 隱藏動作選單
   */
  hideActionMenu() {
    this.actionMenu.style.display = 'none';
    this.currentTarget = null;
  }
  
  /**
   * 檢查是否可執行動作
   */
  canPerformAction(action) {
    const player = this.game.player;
    
    if (action.cost && player.stats.money < action.cost) {
      return false;
    }
    
    return true;
  }
  
  /**
   * 執行動作
   */
  performAction(action, target) {
    console.log(`對 ${target.name} 執行: ${action.name}`);
    
    const player = this.game.player;
    player.performAction(action, target);
    
    // 顯示結果訊息（之後可改為對話框）
    this.showMessage(`你${action.name}了`);
  }
  
  /**
   * 與村民互動
   */
  interactWithVillager(action, villager) {
    console.log(`對 ${villager.name} 執行: ${action.name}`);
    
    const player = this.game.player;
    
    // 更新關係
    switch (action.id) {
      case 'greet':
        player.updateRelationship(villager.id, { familiarity: 2 });
        villager.updateRelationship('player', { familiarity: 2 });
        this.showDialog(villager.name, '你好！今天天氣真好呢。');
        break;
        
      case 'chat':
        player.updateRelationship(villager.id, { 
          familiarity: 5, 
          affection: Math.random() > 0.5 ? 2 : -1 
        });
        player.stats.social = Math.min(100, player.stats.social + 10);
        this.showDialog(villager.name, '最近村裡發生了很多事呢...');
        break;
        
      case 'ask_info':
        player.updateRelationship(villager.id, { familiarity: 3 });
        this.showDialog(villager.name, '你想知道什麼？我聽說了一些有趣的事...');
        break;
        
      case 'give_gift':
        player.updateRelationship(villager.id, { affection: 10 });
        this.showDialog(villager.name, '這是給我的？太感謝了！');
        break;
        
      case 'invite':
        this.showDialog(villager.name, '好啊，我正好有空！');
        break;
    }
    
    // 記錄互動
    villager.addMemory(`與玩家${action.name}`, 'positive');
  }
  
  /**
   * 顯示對話框
   */
  showDialog(speaker, text) {
    if (!this.dialogBox) return;
    
    const speakerEl = document.getElementById('dialog-speaker');
    const textEl = document.getElementById('dialog-text');
    
    if (speakerEl) speakerEl.textContent = speaker;
    if (textEl) textEl.textContent = text;
    
    this.dialogBox.style.display = 'block';
    
    // 3 秒後自動隱藏
    setTimeout(() => {
      this.dialogBox.style.display = 'none';
    }, 3000);
  }
  
  /**
   * 顯示訊息
   */
  showMessage(msg) {
    this.showDialog('系統', msg);
  }
  
  /**
   * 取得職業名稱
   */
  getOccupationName(occupation) {
    const names = {
      tavern: '酒保',
      church: '神父',
      plaza: '廣場',
      blacksmith: '鐵匠',
      bakery: '麵包師',
      farm: '農夫',
      house: '村民'
    };
    return names[occupation] || '村民';
  }
}
