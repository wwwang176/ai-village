/**
 * 輸入處理器 - 處理玩家輸入
 */

import { PathFinding } from '../systems/PathFinding.js';

export class InputHandler {
  constructor(game) {
    this.game = game;
    this.keys = {};
    this.mouse = { x: 0, y: 0, clicked: false };
    this.pathFinding = new PathFinding();
  }
  
  /**
   * 初始化事件監聽
   */
  init() {
    // 鍵盤事件
    window.addEventListener('keydown', (e) => this.onKeyDown(e));
    window.addEventListener('keyup', (e) => this.onKeyUp(e));
    
    // 滑鼠事件
    this.game.canvas.addEventListener('click', (e) => this.onClick(e));
    this.game.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
    this.game.canvas.addEventListener('contextmenu', (e) => this.onRightClick(e));
    
    // 點擊畫面外關閉選單
    document.addEventListener('click', (e) => {
      if (!e.target.closest('#action-menu') && !e.target.closest('#game-canvas')) {
        this.game.uiManager.hideActionMenu();
      }
    });
  }
  
  onKeyDown(e) {
    this.keys[e.code] = true;
    
    // 處理移動
    const player = this.game.player;
    const speed = 3; // tiles per second
    
    switch (e.code) {
      case 'KeyW':
      case 'ArrowUp':
        player.setVelocity(0, -speed);
        break;
      case 'KeyS':
      case 'ArrowDown':
        player.setVelocity(0, speed);
        break;
      case 'KeyA':
      case 'ArrowLeft':
        player.setVelocity(-speed, 0);
        break;
      case 'KeyD':
      case 'ArrowRight':
        player.setVelocity(speed, 0);
        break;
      case 'Escape':
        this.game.uiManager.hideActionMenu();
        break;
    }
  }
  
  onKeyUp(e) {
    this.keys[e.code] = false;
    
    // 停止移動
    const player = this.game.player;
    
    if (['KeyW', 'KeyS', 'ArrowUp', 'ArrowDown'].includes(e.code)) {
      if (!this.keys['KeyW'] && !this.keys['KeyS'] && 
          !this.keys['ArrowUp'] && !this.keys['ArrowDown']) {
        player.velocity.y = 0;
      }
    }
    
    if (['KeyA', 'KeyD', 'ArrowLeft', 'ArrowRight'].includes(e.code)) {
      if (!this.keys['KeyA'] && !this.keys['KeyD'] && 
          !this.keys['ArrowLeft'] && !this.keys['ArrowRight']) {
        player.velocity.x = 0;
      }
    }
  }
  
  onClick(e) {
    const rect = this.game.canvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    
    // 轉換為世界座標（考慮置中偏移量）
    const camera = this.game.camera;
    const worldPos = camera.screenToWorld(screenX, screenY);
    
    // 轉換為格子座標
    const tileX = Math.floor(worldPos.x / this.game.config.tileSize);
    const tileY = Math.floor(worldPos.y / this.game.config.tileSize);
    
    console.log(`點擊位置: 螢幕(${screenX}, ${screenY}) 世界(${worldPos.x.toFixed(0)}, ${worldPos.y.toFixed(0)}) 格子(${tileX}, ${tileY})`);
    
    // 檢查是否點擊到村民
    const clickedVillager = this.game.villagerManager.getVillagerAt(tileX, tileY);
    
    if (clickedVillager) {
      // 選取村民，鏡頭跟隨
      console.log('👁️ 選取村民:', clickedVillager.name);
      this.game.selectVillager(clickedVillager);
    } else {
      // 點擊空地取消選取
      this.game.selectVillager(null);
    }
  }
  
  onMouseMove(e) {
    const rect = this.game.canvas.getBoundingClientRect();
    this.mouse.x = e.clientX - rect.left;
    this.mouse.y = e.clientY - rect.top;
  }
  
  onRightClick(e) {
    e.preventDefault();
    // 取消選取
    this.game.selectVillager(null);
  }
}
