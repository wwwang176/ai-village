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
    
    // 鏡頭移動設定
    this.cameraSpeed = 300;      // 鏡頭移動速度（像素/秒）
    
    // 滑鼠拖曳移動鏡頭
    this.isDragging = false;
    this.lastDragPos = { x: 0, y: 0 };
    this.dragDistance = 0;  // 累計拖曳距離，用於區分點擊和拖曳
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
    this.game.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
    this.game.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
    this.game.canvas.addEventListener('mouseleave', (e) => this.onMouseUp(e));
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
    
    // Escape 關閉選單
    if (e.code === 'Escape') {
      this.game.uiManager.hideActionMenu();
    }
  }
  
  onKeyUp(e) {
    this.keys[e.code] = false;
  }
  
  /**
   * 更新鏡頭移動（由 Game.update 呼叫）
   */
  updateCameraMovement(deltaTime) {
    // 跟隨模式下不允許手動移動
    if (this.game.isFollowing) return;
    
    const camera = this.game.camera;
    let dx = 0;
    let dy = 0;
    
    // 鍵盤方向鍵移動鏡頭
    if (this.keys['ArrowUp'] || this.keys['KeyW']) dy -= 1;
    if (this.keys['ArrowDown'] || this.keys['KeyS']) dy += 1;
    if (this.keys['ArrowLeft'] || this.keys['KeyA']) dx -= 1;
    if (this.keys['ArrowRight'] || this.keys['KeyD']) dx += 1;
    
    // 應用移動
    if (dx !== 0 || dy !== 0) {
      const speed = (dx !== 0 && dy !== 0) 
        ? this.cameraSpeed * 0.707  // 對角線移動時正規化
        : this.cameraSpeed;
      camera.move(dx * speed * deltaTime, dy * speed * deltaTime);
    }
  }
  
  onClick(e) {
    // 如果是拖曳操作（移動距離 > 5px），不處理點擊
    if (this.dragDistance > 5) {
      return;
    }
    
    const rect = this.game.canvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    
    // 考慮縮放：先反向縮放螢幕座標
    const camera = this.game.camera;
    const zoom = camera.zoom;
    const centerX = this.game.canvas.width / 2;
    const centerY = this.game.canvas.height / 2;
    
    // 反向縮放變換（與渲染時的縮放相反）
    const zoomedX = (screenX - centerX) / zoom + centerX;
    const zoomedY = (screenY - centerY) / zoom + centerY;
    
    // 轉換為世界座標（考慮置中偏移量）
    const worldPos = camera.screenToWorld(zoomedX, zoomedY);
    
    // 轉換為格子座標
    const tileX = Math.floor(worldPos.x / this.game.config.tileSize);
    const tileY = Math.floor(worldPos.y / this.game.config.tileSize);
    
    console.log(`點擊位置: 螢幕(${screenX}, ${screenY}) 縮放後(${zoomedX.toFixed(0)}, ${zoomedY.toFixed(0)}) 格子(${tileX}, ${tileY})`);
    
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
    
    // 拖曳移動鏡頭（考慮縮放）
    if (this.isDragging && !this.game.isFollowing) {
      const dx = this.lastDragPos.x - this.mouse.x;
      const dy = this.lastDragPos.y - this.mouse.y;
      this.dragDistance += Math.abs(dx) + Math.abs(dy);
      // 縮放時調整移動距離：zoom 大時移動慢，zoom 小時移動快
      const zoom = this.game.camera.zoom;
      this.game.camera.move(dx / zoom, dy / zoom);
      this.lastDragPos.x = this.mouse.x;
      this.lastDragPos.y = this.mouse.y;
    }
  }
  
  onMouseDown(e) {
    // 只處理左鍵拖曳
    if (e.button === 0) {
      this.isDragging = true;
      this.dragDistance = 0;  // 重置拖曳距離
      this.lastDragPos.x = this.mouse.x;
      this.lastDragPos.y = this.mouse.y;
      this.game.canvas.style.cursor = 'grabbing';
    }
  }
  
  onMouseUp(e) {
    this.isDragging = false;
    this.game.canvas.style.cursor = 'default';
  }
  
  onRightClick(e) {
    e.preventDefault();
    // 取消選取
    this.game.selectVillager(null);
  }
}
