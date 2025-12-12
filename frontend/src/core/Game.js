/**
 * 遊戲主類 - 管理所有遊戲系統
 * 支援離線模式和後端模式
 */

import { Renderer } from '../render/Renderer.js';
import { Camera } from '../render/Camera.js';
import { MapGenerator } from '../world/MapGenerator.js';
import { GameMap } from '../world/GameMap.js';
import { TimeSystem } from './TimeSystem.js';
import { VillagerManager } from '../entities/VillagerManager.js';
import { Player } from '../entities/Player.js';
import { InputHandler } from './InputHandler.js';
import { UIManager } from '../ui/UIManager.js';
import { Dashboard } from '../ui/Dashboard.js';
import { apiClient } from '../api/ApiClient.js';

export class Game {
  constructor(config) {
    this.config = {
      canvasId: config.canvasId || 'game-canvas',
      width: config.width || 800,
      height: config.height || 600,
      tileSize: config.tileSize || 16,
      mapWidth: config.mapWidth || 64,
      mapHeight: config.mapHeight || 64,
      villagerCount: config.villagerCount || 29, // 29 NPC + 1 玩家 = 30
      useBackend: config.useBackend || false,    // 是否使用後端
    };
    
    this.isRunning = false;
    this.lastTimestamp = 0;
    this.lastTickTime = 0;
    this.tickInterval = 1000; // 每秒呼叫後端一次
    
    // 觀察模式
    this.selectedVillager = null;  // 選中的村民
    
    // API 客戶端
    this.api = apiClient;
    
    // 系統參考
    this.canvas = null;
    this.ctx = null;
    this.renderer = null;
    this.camera = null;
    this.map = null;
    this.timeSystem = null;
    this.villagerManager = null;
    this.player = null;
    this.inputHandler = null;
    this.uiManager = null;
    this.furniture = [];  // 家具（灶台、床）
  }
  
  /**
   * 初始化遊戲
   */
  async init() {
    // 取得 Canvas
    this.canvas = document.getElementById(this.config.canvasId);
    if (!this.canvas) {
      throw new Error(`找不到 Canvas: ${this.config.canvasId}`);
    }
    
    // 設定為滿版
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
    
    this.ctx = this.canvas.getContext('2d');
    
    // 停用抗鋸齒（像素風格）
    this.ctx.imageSmoothingEnabled = false;
    
    // 初始化鏡頭
    this.camera = new Camera({
      viewportWidth: this.canvas.width,
      viewportHeight: this.canvas.height,
      mapWidth: this.config.mapWidth * this.config.tileSize,
      mapHeight: this.config.mapHeight * this.config.tileSize
    });
    
    // 根據模式初始化
    if (this.config.useBackend) {
      await this.initWithBackend();
    } else {
      await this.initOffline();
    }
    
    // 初始化渲染器
    this.renderer = new Renderer(this.ctx, this.camera, this.config.tileSize);
    
    // 鏡頭跟隨玩家
    this.camera.follow(this.player);
    
    // 初始化輸入處理
    this.inputHandler = new InputHandler(this);
    this.inputHandler.init();
    
    // 初始化 UI 管理器
    this.uiManager = new UIManager(this);
    
    // 初始化 Dashboard
    this.dashboard = new Dashboard(this);
    
    // 定期更新 Dashboard
    setInterval(() => {
      if (this.dashboard) {
        this.dashboard.update();
      }
    }, 500);
    
    // 初始化縮放控制
    this.initZoomControls();
  }
  
  /**
   * 初始化縮放控制
   */
  initZoomControls() {
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const zoomLevel = document.getElementById('zoom-level');
    
    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        this.camera.zoomIn();
        this.updateZoomDisplay();
      });
    }
    
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        this.camera.zoomOut();
        this.updateZoomDisplay();
      });
    }
    
    // 滑鼠滾輪縮放
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      if (e.deltaY < 0) {
        this.camera.zoomIn();
      } else {
        this.camera.zoomOut();
      }
      this.updateZoomDisplay();
    });
  }
  
  /**
   * 更新縮放顯示
   */
  updateZoomDisplay() {
    const zoomLevel = document.getElementById('zoom-level');
    if (zoomLevel) {
      zoomLevel.textContent = `${Math.round(this.camera.zoom * 100)}%`;
    }
  }
  
  /**
   * 離線模式初始化
   */
  async initOffline() {
    console.log('🎮 離線模式');
    
    // 生成地圖
    console.log('🗺️ 生成地圖中...');
    const mapGenerator = new MapGenerator({
      width: this.config.mapWidth,
      height: this.config.mapHeight,
      tileSize: this.config.tileSize
    });
    const mapData = mapGenerator.generate();
    
    this.map = new GameMap(mapData, this.config.tileSize);
    console.log(`✅ 地圖生成完成: ${this.map.buildings.length} 棟建築物`);
    
    // 初始化時間系統
    this.timeSystem = new TimeSystem();
    
    // 初始化村民管理器
    this.villagerManager = new VillagerManager(this.map);
    this.villagerManager.generateVillagers(this.config.villagerCount, this.map.buildings);
    console.log(`✅ 生成 ${this.villagerManager.villagers.length} 位村民`);
    
    // 初始化玩家
    const playerSpawn = this.map.getPlayerSpawnPoint();
    this.player = new Player({
      x: playerSpawn.x,
      y: playerSpawn.y,
      name: '玩家'
    });
  }
  
  /**
   * 後端模式初始化 (WebSocket)
   */
  async initWithBackend() {
    console.log('🌐 後端模式 (WebSocket)');
    
    try {
      // 註冊 WebSocket 訊息處理器
      this.setupWebSocketHandlers();
      
      // 連接 WebSocket（會自動收到 init 訊息）
      await this.api.connectWebSocket();
      
      // 等待初始化完成
      await this.waitForInit();
      
    } catch (error) {
      console.error('後端連接失敗，切換到離線模式:', error);
      this.config.useBackend = false;
      await this.initOffline();
    }
  }
  
  /**
   * 設定 WebSocket 訊息處理器
   */
  setupWebSocketHandlers() {
    // 初始化訊息
    this.api.on('init', (data) => {
      console.log('📥 收到初始化資料');
      this.handleInit(data);
    });
    
    // 定期 tick 更新
    this.api.on('tick', (data) => {
      this.handleTick(data);
    });
    
    // 村民 AI 決策
    this.api.on('villager_decision', (data) => {
      this.handleVillagerDecision(data);
    });
    
    // 對話
    this.api.on('dialogue', (data) => {
      if (this.uiManager) {
        this.uiManager.showDialog(data.speaker, data.text);
      }
    });
    
    // 互動結果
    this.api.on('interact_result', (data) => {
      if (data.message && this.uiManager) {
        this.uiManager.showMessage(data.message);
      }
    });
    
    // 狀態更新
    this.api.on('state_update', (data) => {
      this.syncFromServer(data);
    });
    
    // 村民泡泡
    this.api.on('villager_bubble', (data) => {
      this.handleVillagerBubble(data);
    });
    
    // 村民對話
    this.api.on('villager_chat', (data) => {
      this.handleVillagerChat(data);
    });
    
    // 交易動畫
    this.api.on('trade_animation', (data) => {
      this.playTradeAnimation(data);
    });
  }
  
  /**
   * 等待初始化完成
   */
  waitForInit() {
    return new Promise((resolve) => {
      const checkInit = () => {
        if (this.map && this.player) {
          resolve();
        } else {
          setTimeout(checkInit, 100);
        }
      };
      // 最多等 5 秒
      setTimeout(() => resolve(), 5000);
      checkInit();
    });
  }
  
  /**
   * 處理初始化訊息
   */
  handleInit(data) {
    const { map: mapData, player, villagers, furniture, time } = data;
    
    // 使用後端的地圖資料
    this.map = new GameMap(mapData, this.config.tileSize);
    console.log(`✅ 地圖載入完成: ${this.map.buildings.length} 棟建築物`);
    
    // 時間系統
    this.timeSystem = new TimeSystem();
    if (time) {
      this.timeSystem.day = time.day;
      this.timeSystem.hour = time.hour;
      this.timeSystem.minute = time.minute;
    }
    
    // 村民管理器
    this.villagerManager = new VillagerManager(this.map);
    this.villagerManager.loadFromBackend(villagers);
    console.log(`✅ 載入 ${this.villagerManager.villagers.length} 位村民`);
    
    // 家具
    this.furniture = furniture || [];
    console.log(`✅ 載入 ${this.furniture.length} 件家具`);
    
    // 玩家
    this.player = new Player({
      x: player.x,
      y: player.y,
      name: player.name
    });
    this.player.stats = player.stats;
  }
  
  /**
   * 處理 tick 更新（從後端推送）
   */
  handleTick(data) {
    // 同步時間
    if (data.time) {
      this.timeSystem.day = data.time.day;
      this.timeSystem.hour = data.time.hour;
      this.timeSystem.minute = data.time.minute;
    }
    
    // 同步村民位置（傳入選中村民 ID 以便印出日誌）
    if (data.villagers) {
      const selectedId = this.selectedVillager?.id || null;
      this.villagerManager.syncFromBackend(data.villagers, selectedId);
    }
    
    // 同步地上物品
    if (data.world_items && this.map) {
      this.map.worldItems = data.world_items;
    }
    
    // 同步羊群
    if (data.sheep && this.map) {
      this.map.sheep = data.sheep;
    }
  }
  
  /**
   * 處理村民 AI 決策
   */
  handleVillagerDecision(data) {
    const villager = this.villagerManager.getVillagerById(data.villager_id);
    if (villager && data.decision) {
      // 如果是選中的村民，印出決策日誌
      if (this.selectedVillager && this.selectedVillager.id === villager.id) {
        console.log(`🤖 [${villager.name}] AI決策: ${data.decision.action} (原因: ${data.decision.reason})`);
      }
      
      // 設定村民目標和顯示泡泡
      villager.setGoalFromDecision(data.decision);
      villager.currentMood = data.decision.mood;
    }
  }
  
  /**
   * 處理村民對話/泡泡訊息
   */
  handleVillagerBubble(data) {
    const { villager_id, text, type } = data;
    this.villagerManager.showVillagerBubble(villager_id, text, type || 'speech');
  }
  
  /**
   * 處理村民間對話（新的多輪對話格式）
   */
  handleVillagerChat(data) {
    console.log('📨 收到對話訊息:', data);
    
    const { villager_id, villager_name, target_name, text, turn } = data;
    
    if (!villager_id || !text) {
      console.warn('⚠️ 對話資料不完整:', data);
      return;
    }
    
    // 組合完整訊息：「對XX說：」+ 內容
    const fullText = target_name ? `對${target_name}說：\n${text}` : text;
    
    // 顯示對話泡泡（持續時間根據輪數和文字長度調整）
    const baseDuration = 4000 + (turn || 0) * 500;
    const textDuration = Math.min(text.length * 100, 3000); // 每字 100ms，最多 3 秒
    const duration = baseDuration + textDuration;
    
    const villager = this.villagerManager.getVillagerById(villager_id);
    
    if (villager) {
      villager.showBubble(fullText, 'speech', duration);
      console.log(`💬 [${villager_name}] 對 [${target_name}] 說: ${text}`);
    } else {
      console.warn(`⚠️ 找不到村民: ${villager_id}`);
    }
  }
  
  /**
   * 播放交易動畫（物品從 A 飛到 B）
   */
  playTradeAnimation(data) {
    const { from_pos, to_pos, icon, quantity } = data;
    
    if (!from_pos || !to_pos) {
      console.warn('⚠️ 交易動畫資料不完整:', data);
      return;
    }
    
    // 建立飛行物件
    const flyingItem = {
      x: from_pos.x * this.config.tileSize + this.config.tileSize / 2,
      y: from_pos.y * this.config.tileSize + this.config.tileSize / 2,
      targetX: to_pos.x * this.config.tileSize + this.config.tileSize / 2,
      targetY: to_pos.y * this.config.tileSize + this.config.tileSize / 2,
      icon: icon || '📦',
      quantity: quantity || 1,
      progress: 0,
      duration: 800  // 動畫持續 0.8 秒
    };
    
    // 加入動畫列表
    if (!this.flyingItems) {
      this.flyingItems = [];
    }
    this.flyingItems.push(flyingItem);
    
    console.log(`🎁 交易動畫: ${icon} x${quantity} 從 (${from_pos.x},${from_pos.y}) 飛到 (${to_pos.x},${to_pos.y})`);
  }
  
  /**
   * 同步後端狀態
   */
  syncFromServer(state) {
    if (state.time) {
      this.timeSystem.day = state.time.day;
      this.timeSystem.hour = state.time.hour;
      this.timeSystem.minute = state.time.minute;
    }
    
    if (state.villagers) {
      this.villagerManager.syncFromBackend(state.villagers);
    }
  }
  
  /**
   * 開始遊戲循環
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.lastTimestamp = performance.now();
    requestAnimationFrame((ts) => this.gameLoop(ts));
    
    console.log('🎮 遊戲開始運行');
  }
  
  /**
   * 暫停遊戲
   */
  pause() {
    this.isRunning = false;
  }
  
  /**
   * 遊戲主循環
   */
  gameLoop(timestamp) {
    if (!this.isRunning) return;
    
    const deltaTime = (timestamp - this.lastTimestamp) / 1000; // 轉換為秒
    this.lastTimestamp = timestamp;
    
    // 更新
    this.update(deltaTime);
    
    // 渲染
    this.render();
    
    // 繼續循環
    requestAnimationFrame((ts) => this.gameLoop(ts));
  }
  
  /**
   * 更新遊戲狀態
   */
  update(deltaTime) {
    // 離線模式：本地更新時間
    // 後端模式：時間由後端 tick 推送同步
    if (!this.config.useBackend) {
      this.timeSystem.update(deltaTime);
    }
    
    // 鏡頭跟隨選中的村民
    if (this.selectedVillager) {
      this.camera.follow(this.selectedVillager);
    }
    
    // 更新鏡頭
    this.camera.update();
    
    // 離線模式：本地更新村民
    // 後端模式：村民由後端控制，本地只做插值動畫
    if (!this.config.useBackend) {
      this.villagerManager.update(deltaTime, this.map, this.timeSystem);
    } else {
      this.villagerManager.updateAnimation(deltaTime);
    }
    
    // 更新 UI
    this.uiManager.update(this.selectedVillager, this.timeSystem);
    
    // 更新飛行物品動畫
    this.updateFlyingItems(deltaTime);
  }
  
  /**
   * 更新飛行物品動畫
   */
  updateFlyingItems(deltaTime) {
    if (!this.flyingItems || this.flyingItems.length === 0) return;
    
    for (let i = this.flyingItems.length - 1; i >= 0; i--) {
      const item = this.flyingItems[i];
      item.progress += (deltaTime * 1000) / item.duration;
      
      if (item.progress >= 1) {
        // 動畫完成，移除
        this.flyingItems.splice(i, 1);
      } else {
        // 使用 ease-out 曲線計算位置
        const t = 1 - Math.pow(1 - item.progress, 3);
        item.currentX = item.x + (item.targetX - item.x) * t;
        item.currentY = item.y + (item.targetY - item.y) * t;
        // 加入拋物線高度（最高點在中間）
        const arcHeight = 30;
        item.arcY = -Math.sin(item.progress * Math.PI) * arcHeight;
      }
    }
  }
  
  /**
   * 選取村民
   */
  selectVillager(villager) {
    this.selectedVillager = villager;
    if (villager) {
      console.log(`👁️ 開始觀察: ${villager.name}`);
      // 鏡頭跟隨選中的村民
      this.camera.follow(villager);
      // 立即定位鏡頭到村民位置
      this.camera.centerOn(villager);
    }
  }
  
  /**
   * 根據 ID 選取村民
   */
  selectVillagerById(villagerId) {
    if (!this.villagerManager) return;
    
    const villager = this.villagerManager.getVillagerById(villagerId);
    if (villager) {
      this.selectVillager(villager);
      // 同步更新 Dashboard 選擇狀態
      if (this.dashboard) {
        this.dashboard.selectedVillagerId = villagerId;
      }
    }
  }
  
  /**
   * 同步玩家位置到後端
   */
  syncPlayerToServer() {
    // 節流：每 100ms 同步一次
    const now = Date.now();
    if (!this.lastPlayerSync || now - this.lastPlayerSync > 100) {
      this.lastPlayerSync = now;
      this.api.sendPlayerMove(this.player.x, this.player.y);
    }
  }
  
  /**
   * 渲染遊戲畫面
   */
  render() {
    // 清除畫面
    this.ctx.fillStyle = '#1a1a2e';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // 應用縮放
    const zoom = this.camera.zoom;
    this.ctx.save();
    
    // 以畫面中心為縮放中心
    // 因為相機已經讓目標在畫面中心，所以縮放時目標會保持在中心
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;
    this.ctx.translate(centerX, centerY);
    this.ctx.scale(zoom, zoom);
    this.ctx.translate(-centerX, -centerY);
    
    // 渲染地圖
    this.renderer.renderMap(this.map);
    
    // 渲染家具（灶台、床）
    this.renderer.renderFurniture(this.furniture);
    
    // 渲染選中村民的路徑
    if (this.selectedVillager) {
      this.renderer.renderVillagerPath(this.selectedVillager);
    }
    
    // 渲染村民
    this.renderer.renderVillagers(this.villagerManager.villagers, this.selectedVillager);
    
    // 渲染飛行物品（交易動畫）
    this.renderFlyingItems();
    
    // 渲染建築物頂部（遮擋效果）
    this.renderer.renderBuildingTops(this.map);
    
    // 還原縮放
    this.ctx.restore();
    
    // 渲染光照層（晝夜效果）- 在縮放外渲染
    this.renderer.renderLighting(
      this.timeSystem,
      this.map.buildings,
      this.villagerManager.villagers,
      this.furniture,
      this.canvas.width,
      this.canvas.height,
      this.camera.zoom
    );
  }
  
  /**
   * 渲染飛行物品（交易動畫）
   */
  renderFlyingItems() {
    if (!this.flyingItems || this.flyingItems.length === 0) return;
    
    const ctx = this.ctx;
    
    for (const item of this.flyingItems) {
      if (item.currentX === undefined) continue;
      
      // 轉換為螢幕座標
      const screenX = item.currentX - this.camera.x;
      const screenY = item.currentY - this.camera.y + (item.arcY || 0);
      
      // 繪製 emoji 圖示
      ctx.save();
      ctx.font = '16px serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // 縮放效果（開始和結束時較小）
      const scale = 0.8 + 0.4 * Math.sin(item.progress * Math.PI);
      ctx.translate(screenX, screenY);
      ctx.scale(scale, scale);
      
      // 繪製圖示
      ctx.fillText(item.icon, 0, 0);
      
      // 如果數量 > 1，顯示數量
      if (item.quantity > 1) {
        ctx.font = 'bold 10px Arial';
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeText(`x${item.quantity}`, 10, 8);
        ctx.fillText(`x${item.quantity}`, 10, 8);
      }
      
      ctx.restore();
    }
  }
  
  /**
   * 調整 Canvas 大小為滿版
   */
  resizeCanvas() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    
    // 更新鏡頭視窗大小
    if (this.camera) {
      this.camera.viewportWidth = this.canvas.width;
      this.camera.viewportHeight = this.canvas.height;
    }
    
    // 重新停用抗鋸齒
    if (this.ctx) {
      this.ctx.imageSmoothingEnabled = false;
    }
  }
}
