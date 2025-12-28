/**
 * AI 中古世紀村莊 - 遊戲入口點
 * 需要後端伺服器才能運行
 */

import { Game } from './core/Game.js';

// 等待 DOM 載入完成
window.addEventListener('DOMContentLoaded', async () => {
  console.log('🏰 AI 中古世紀村莊啟動中...');
  console.log('🌐 連接後端伺服器...');
  
  // 建立遊戲實例（固定使用後端模式）
  const game = new Game({
    canvasId: 'game-canvas',
    width: 800,
    height: 600,
    tileSize: 16,
    mapWidth: 64,
    mapHeight: 64
  });
  
  // 初始化並開始遊戲
  try {
    await game.init();
    console.log('✅ 遊戲初始化完成');
    game.start();
  } catch (err) {
    console.error('❌ 遊戲初始化失敗:', err);
    // 顯示友善的錯誤訊息
    document.body.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: #1a1a2e; color: #fff; font-family: sans-serif;">
        <div style="text-align: center;">
          <h1 style="color: #ff6b6b;">❌ 無法連接到後端伺服器</h1>
          <p>請確認後端服務已啟動：</p>
          <pre style="background: #16213e; padding: 20px; border-radius: 8px; text-align: left; margin: 20px auto; max-width: 500px;">cd backend
python -m uvicorn app.main:app --reload</pre>
          <p style="color: #888;">錯誤訊息：${err.message}</p>
        </div>
      </div>
    `;
  }
  
  // 將遊戲實例掛載到 window 方便除錯
  window.game = game;
});
