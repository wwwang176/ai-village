/**
 * AI 中古世紀村莊 - 遊戲入口點
 */

import { Game } from './core/Game.js';

/**
 * 檢測後端是否可用
 */
async function checkBackendAvailable() {
  try {
    const response = await fetch('/api/game/state', { 
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return response.ok;
  } catch {
    return false;
  }
}

// 等待 DOM 載入完成
window.addEventListener('DOMContentLoaded', async () => {
  console.log('🏰 AI 中古世紀村莊啟動中...');
  
  // 檢測後端
  const backendAvailable = await checkBackendAvailable();
  console.log(backendAvailable ? '🌐 後端可用' : '📴 後端不可用，使用離線模式');
  
  // 建立遊戲實例
  const game = new Game({
    canvasId: 'game-canvas',
    width: 800,
    height: 600,
    tileSize: 16,
    mapWidth: 64,
    mapHeight: 64,
    useBackend: backendAvailable
  });
  
  // 初始化並開始遊戲
  game.init().then(() => {
    console.log('✅ 遊戲初始化完成');
    game.start();
  }).catch(err => {
    console.error('❌ 遊戲初始化失敗:', err);
  });
  
  // 將遊戲實例掛載到 window 方便除錯
  window.game = game;
});
