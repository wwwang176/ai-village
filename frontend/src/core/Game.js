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
    const { map: mapData, player, villagers, time } = data;
    
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
   * 處理村民間對話
   */
  handleVillagerChat(data) {
    const { villager_a_id, villager_a_name, villager_b_id, text_a, text_b } = data;
    
    // 顯示 A 的對話泡泡
    this.villagerManager.showVillagerBubble(villager_a_id, text_a, 'speech', 4000);
    
    // 延遲 1.5 秒後顯示 B 的回應
    setTimeout(() => {
      this.villagerManager.showVillagerBubble(villager_b_id, text_b, 'speech', 4000);
    }, 1500);
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
  }
  
  /**
   * 選取村民
   */
  selectVillager(villager) {
    this.selectedVillager = villager;
    if (villager) {
      console.log(`👁️ 開始觀察: ${villager.name}`);
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
    
    // 渲染地圖
    this.renderer.renderMap(this.map);
    
    // 渲染選中村民的路徑
    if (this.selectedVillager) {
      this.renderer.renderVillagerPath(this.selectedVillager);
    }
    
    // 渲染村民
    this.renderer.renderVillagers(this.villagerManager.villagers, this.selectedVillager);
    
    // 渲染建築物頂部（遮擋效果）
    this.renderer.renderBuildingTops(this.map);
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
