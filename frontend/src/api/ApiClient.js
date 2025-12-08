/**
 * API 客戶端 - 與後端通訊 (WebSocket 優先)
 */

export class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl || window.location.origin;
    this.ws = null;
    this.wsConnected = false;
    this.wsCallbacks = {};
    this.messageHandlers = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  // === WebSocket 核心 ===

  connectWebSocket() {
    return new Promise((resolve, reject) => {
      const wsUrl = `${this.baseUrl.replace('http', 'ws')}/ws`;
      console.log('🔌 連接 WebSocket:', wsUrl);
      
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('✅ WebSocket 已連線');
        this.wsConnected = true;
        this.reconnectAttempts = 0;
        
        if (this.wsCallbacks.onConnect) {
          this.wsCallbacks.onConnect();
        }
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (e) {
          console.error('WebSocket 訊息解析錯誤:', e);
        }
      };

      this.ws.onclose = () => {
        console.log('🔌 WebSocket 已斷線');
        this.wsConnected = false;
        
        if (this.wsCallbacks.onDisconnect) {
          this.wsCallbacks.onDisconnect();
        }
        
        // 自動重連
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket 錯誤:', error);
        reject(error);
      };
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      console.log(`🔄 ${delay/1000}秒後重連... (第${this.reconnectAttempts}次)`);
      setTimeout(() => this.connectWebSocket(), delay);
    } else {
      console.error('❌ WebSocket 重連失敗，已達最大嘗試次數');
    }
  }

  handleMessage(message) {
    const { type, data } = message;
    
    // 呼叫特定類型的處理器
    const handler = this.messageHandlers.get(type);
    if (handler) {
      handler(data);
    }
    
    // 呼叫通用處理器
    if (this.wsCallbacks.onMessage) {
      this.wsCallbacks.onMessage(message);
    }
  }

  // === 訊息處理器註冊 ===

  on(messageType, handler) {
    this.messageHandlers.set(messageType, handler);
  }

  off(messageType) {
    this.messageHandlers.delete(messageType);
  }

  onConnect(callback) {
    this.wsCallbacks.onConnect = callback;
  }

  onDisconnect(callback) {
    this.wsCallbacks.onDisconnect = callback;
  }

  onMessage(callback) {
    this.wsCallbacks.onMessage = callback;
  }

  // === 發送訊息 ===

  send(type, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket 未連線，訊息未發送:', type);
    }
  }

  // === 玩家動作 ===

  sendPlayerMove(x, y) {
    this.send('player_move', { x, y });
  }

  sendPlayerInteract(targetId, actionId) {
    this.send('player_interact', { target_id: targetId, action_id: actionId });
  }

  sendPlayerTalk(villagerId, action, message = null) {
    this.send('player_talk', { 
      villager_id: villagerId, 
      action: action,
      message: message 
    });
  }

  requestState() {
    this.send('request_state');
  }

  ping() {
    this.send('ping');
  }

  // === HTTP API (備用/初始化用) ===

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}/api${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  async get(endpoint) {
    return this.request(endpoint);
  }

  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async getGameState() {
    return this.get('/game/state');
  }

  async saveGame() {
    return this.post('/game/save', {});
  }
}

// 單例
export const apiClient = new ApiClient();
