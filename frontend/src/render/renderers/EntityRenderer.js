/**
 * 實體渲染器 - 村民、羊、玩家
 */
import { BaseRenderer } from './BaseRenderer.js';

export class EntityRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
  }
  
  // ==================== 村民 ====================
  
  /**
   * 渲染所有村民
   */
  renderVillagers(villagers, selectedVillager = null) {
    // 按 Y 座標排序（下方的後渲染，遮擋上方的）
    const sorted = [...villagers].sort((a, b) => a.y - b.y);
    
    for (const villager of sorted) {
      const isSelected = selectedVillager && selectedVillager.id === villager.id;
      this.renderVillager(villager, isSelected);
    }
  }
  
  /**
   * 渲染單一村民（用於 Y-sort）
   */
  renderSingleVillager(villager, isSelected = false) {
    this.renderVillager(villager, isSelected);
  }
  
  /**
   * 渲染單一村民
   */
  renderVillager(villager, isSelected = false) {
    const screen = this.toScreen(villager.x, villager.y);
    const screenX = screen.x;
    const screenY = screen.y - 8; // 往上偏移，讓腳對齊格子中央
    const size = this.tileSize;
    const cx = screenX + size / 2;
    
    // 選中效果：發光圈
    if (isSelected) {
      this.ctx.fillStyle = 'rgba(255, 255, 100, 0.25)';
      this.ctx.beginPath();
      this.ctx.arc(cx, screenY + size / 2 + 2, size * 0.7, 0, Math.PI * 2);
      this.ctx.fill();
      
      this.ctx.strokeStyle = 'rgba(255, 220, 100, 0.9)';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.arc(cx, screenY + size / 2 + 2, size * 0.7, 0, Math.PI * 2);
      this.ctx.stroke();
    }
    
    // 陰影（橢圓形）
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    this.ctx.beginPath();
    this.ctx.ellipse(cx, screenY + size - 1, 5, 2, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 服裝顏色
    const clothColor = villager.color || '#5b8dd9';
    const clothDark = this.darkenColor(clothColor, 0.3);
    const clothLight = this.lightenColor(clothColor, 0.2);
    
    // 膚色
    const skinColor = '#f5d5c0';
    const skinDark = '#e0b8a0';
    
    // 頭髮顏色（根據村民 ID 決定）
    const hairColors = ['#2c1810', '#4a3728', '#8b6914', '#1a1a1a', '#6b4423', '#c4a882'];
    const hairColor = hairColors[Math.abs(villager.id?.charCodeAt(0) || 0) % hairColors.length];
    const hairDark = this.darkenColor(hairColor, 0.3);
    
    const isMale = villager.gender === 'male';
    
    // === 身體（2.5D 風格）===
    
    // 身體主體
    this.ctx.fillStyle = clothColor;
    this.ctx.fillRect(cx - 4, screenY + 6, 8, 8);
    
    // 身體右側陰影
    this.ctx.fillStyle = clothDark;
    this.ctx.fillRect(cx + 2, screenY + 6, 2, 8);
    
    // 身體底部陰影
    this.ctx.fillStyle = clothDark;
    this.ctx.fillRect(cx - 4, screenY + 12, 8, 2);
    
    // 領口
    this.ctx.fillStyle = skinColor;
    this.ctx.fillRect(cx - 2, screenY + 5, 4, 2);
    
    // === 頭部 ===
    
    // 頭部主體
    this.ctx.fillStyle = skinColor;
    this.ctx.beginPath();
    this.ctx.arc(cx - 0.5, screenY + 3, 4, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 頭部右側陰影
    this.ctx.fillStyle = skinDark;
    this.ctx.beginPath();
    this.ctx.arc(cx + 0.5, screenY + 3, 4, -0.3, 1.2);
    this.ctx.lineTo(cx + 0.5, screenY + 3);
    this.ctx.fill();
    
    // === 頭髮 ===
    if (isMale) {
      // 男性：短髮
      this.ctx.fillStyle = hairColor;
      this.ctx.beginPath();
      this.ctx.arc(cx - 0.5, screenY + 2, 4, Math.PI, 0);
      this.ctx.fill();
      // 頭髮陰影
      this.ctx.fillStyle = hairDark;
      this.ctx.fillRect(cx, screenY - 1, 3, 2);
    } else {
      // 女性：長髮
      this.ctx.fillStyle = hairColor;
      this.ctx.beginPath();
      this.ctx.arc(cx - 0.5, screenY + 2, 4, Math.PI, 0);
      this.ctx.fill();
      // 側邊長髮
      this.ctx.fillRect(cx - 5, screenY + 1, 2, 6);
      this.ctx.fillRect(cx + 3, screenY + 1, 2, 6);
      // 頭髮陰影
      this.ctx.fillStyle = hairDark;
      this.ctx.fillRect(cx + 1, screenY - 1, 2, 2);
    }
    
    // === 眼睛 ===
    this.ctx.fillStyle = '#1a1a1a';
    this.ctx.fillRect(cx - 2, screenY + 2, 1, 2);
    this.ctx.fillRect(cx + 1, screenY + 2, 1, 2);
    
    // === 腿部 ===
    this.ctx.fillStyle = '#3d3d5c';
    this.ctx.fillRect(cx - 3, screenY + 14, 2, 2);
    this.ctx.fillRect(cx + 1, screenY + 14, 2, 2);
    
    // 名字
    this.ctx.fillStyle = isSelected ? '#ffff66' : '#fff';
    this.ctx.font = isSelected ? 'bold 9px sans-serif' : '8px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
    this.ctx.shadowBlur = 2;
    this.ctx.shadowOffsetX = 1;
    this.ctx.shadowOffsetY = 1;
    this.ctx.fillText(villager.name, cx, screenY + size + 8);
    this.ctx.shadowColor = 'transparent';
    this.ctx.shadowBlur = 0;
    this.ctx.shadowOffsetX = 0;
    this.ctx.shadowOffsetY = 0;
    
    // 睡覺時顯示 ZZZ 動畫
    if (villager.state === 'sleeping') {
      this.renderSleepZZZ(cx, screenY - 5);
    }
    
    // 開放式職業工作時顯示粒子動畫
    const openFieldJobs = ['farmer', 'miner', 'lumberjack'];
    if (villager.state === 'work' && openFieldJobs.includes(villager.occupation)) {
      this.renderWorkParticles(cx, screenY + 5, villager.occupation);
    }
    // 剪羊毛時顯示粒子動畫
    if (villager.state === 'shear_sheep') {
      this.renderWorkParticles(cx, screenY + 5, 'shepherd');
    }
    // 照顧羊時顯示粒子動畫
    if (villager.state === 'tend_sheep') {
      this.renderWorkParticles(cx, screenY + 5, 'tender');
    }
    // 屠宰羊時顯示粒子動畫
    if (villager.state === 'slaughter_sheep') {
      this.renderWorkParticles(cx, screenY + 5, 'butcher');
    }
  }
  
  /**
   * 渲染開放式職業工作粒子動畫
   */
  renderWorkParticles(x, y, occupation) {
    // LOD: 極遠景不渲染粒子
    const zoom = this.camera.zoom || 1;
    if (zoom <= 0.5) return;
    
    const time = performance.now() / 1000;
    const particleCount = 4;
    
    // 根據職業決定顏色
    const colors = {
      'farmer': '#8B4513',     // 棕色土塵
      'miner': '#FFA500',      // 橙黃火花
      'lumberjack': '#DEB887', // 淺棕木屑
      'shepherd': '#FFFFFF',   // 白色羊毛
      'tender': '#90EE90',     // 淺綠色（照顧）
      'butcher': '#8B0000'     // 暗紅色血滴
    };
    const color = colors[occupation] || '#FFFFFF';
    
    for (let i = 0; i < particleCount; i++) {
      const phase = (time * 2 + i * 0.5) % 1.5;
      const angle = (i / particleCount) * Math.PI * 2 + time;
      const radius = 8 + phase * 10;
      const floatX = Math.cos(angle) * radius;
      const floatY = -phase * 15 + Math.sin(angle) * 3;
      const alpha = Math.max(0, 0.8 - phase * 0.6);
      const size = 2 + (1 - phase) * 1.5;
      
      this.ctx.save();
      this.ctx.globalAlpha = alpha;
      this.ctx.fillStyle = color;
      this.ctx.beginPath();
      this.ctx.arc(x + floatX, y + floatY, size, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();
    }
  }
  
  /**
   * 渲染睡覺 ZZZ 動畫
   */
  renderSleepZZZ(x, y) {
    // LOD: 極遠景不渲染 ZZZ
    const zoom = this.camera.zoom || 1;
    if (zoom <= 0.5) return;
    
    const time = performance.now() / 1000;
    const letters = ['Z', 'z', 'z'];
    
    this.ctx.font = 'bold 8px Arial';
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'middle';
    
    for (let i = 0; i < letters.length; i++) {
      // 每個 Z 有不同的動畫相位
      const phase = time * 2 + i * 0.8;
      const floatY = Math.sin(phase) * 3;
      const floatX = i * 6 + Math.sin(phase * 0.5) * 2;
      const alpha = 0.5 + Math.sin(phase) * 0.3;
      const scale = 1 - i * 0.15;
      
      this.ctx.save();
      this.ctx.globalAlpha = alpha;
      this.ctx.fillStyle = '#ffffff';
      this.ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
      this.ctx.shadowBlur = 2;
      this.ctx.font = `bold ${8 * scale}px Arial`;
      this.ctx.fillText(letters[i], x + floatX, y - 8 - i * 5 + floatY);
      this.ctx.restore();
    }
  }
  
  darkenColor(hex, amount) {
    const num = parseInt(hex.slice(1), 16);
    const r = Math.max(0, (num >> 16) - Math.round(255 * amount));
    const g = Math.max(0, ((num >> 8) & 0x00FF) - Math.round(255 * amount));
    const b = Math.max(0, (num & 0x0000FF) - Math.round(255 * amount));
    return `rgb(${r},${g},${b})`;
  }
  
  lightenColor(hex, amount) {
    const num = parseInt(hex.slice(1), 16);
    const r = Math.min(255, (num >> 16) + Math.round(255 * amount));
    const g = Math.min(255, ((num >> 8) & 0x00FF) + Math.round(255 * amount));
    const b = Math.min(255, (num & 0x0000FF) + Math.round(255 * amount));
    return `rgb(${r},${g},${b})`;
  }
  
  /**
   * 渲染村民移動路徑
   */
  renderVillagerPath(villager) {
    if (!villager.moveTarget) return;
    
    const [targetX, targetY] = villager.moveTarget;
    const { x: startX, y: startY } = this.toScreen(villager.x, villager.y);
    const { x: endX, y: endY } = this.toScreen(targetX, targetY);
    const size = this.tileSize;
    
    // 畫虛線路徑
    this.ctx.save();
    this.ctx.setLineDash([4, 4]);
    this.ctx.strokeStyle = 'rgba(255, 255, 100, 0.6)';
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.moveTo(startX + size / 2, startY + size / 2);
    this.ctx.lineTo(endX + size / 2, endY + size / 2);
    this.ctx.stroke();
    this.ctx.restore();
    
    // 畫目標點
    this.ctx.fillStyle = 'rgba(255, 255, 100, 0.8)';
    this.ctx.beginPath();
    this.ctx.arc(endX + size / 2, endY + size / 2, 6, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 目標點外圈
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.arc(endX + size / 2, endY + size / 2, 8, 0, Math.PI * 2);
    this.ctx.stroke();
  }
  
  // ==================== 羊 ====================
  
  /**
   * 渲染所有羊
   */
  renderSheep(sheepList) {
    for (const sheep of sheepList) {
      this.renderSingleSheep(sheep);
    }
  }
  
  /**
   * 渲染單一羊
   */
  renderSingleSheep(sheep) {
    // 使用 displayX/displayY 做插值動畫
    const posX = sheep.displayX ?? sheep.x;
    const posY = sheep.displayY ?? sheep.y;
    const screen = this.toScreen(posX, posY);
    const screenX = screen.x;
    const screenY = screen.y - 8; // 往上偏移，讓腳對齊格子中央
    const size = this.tileSize;
    const zoom = this.camera.zoom || 1;
    
    // 根據羊毛狀態決定顏色和大小
    let bodyColor, bodyColorDark, bodyScale;
    if (sheep.wool_ready) {
      bodyColor = '#ffffff';
      bodyColorDark = '#e8e8e8';
      bodyScale = 1.15;
    } else {
      bodyColor = sheep.is_adult ? '#d0d0d0' : '#e0e0e0';
      bodyColorDark = sheep.is_adult ? '#b8b8b8' : '#c8c8c8';
      bodyScale = 1.0;
    }
    
    const isAdult = sheep.is_adult;
    const baseBodyW = isAdult ? size * 0.75 : size * 0.5;
    const baseBodyH = isAdult ? size * 0.5 : size * 0.35;
    const bodyW = baseBodyW * bodyScale;
    const bodyH = baseBodyH * bodyScale;
    
    const centerX = screenX + size / 2;
    const centerY = screenY + size / 2 + 2;
    
    // LOD: 極遠景只畫簡單橢圓
    if (zoom <= 0.5) {
      this.ctx.fillStyle = bodyColor;
      this.ctx.fillRect(centerX - bodyW / 2, centerY - bodyH / 2, bodyW, bodyH);
      return;
    }
    
    // === 陰影 ===
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    this.ctx.beginPath();
    this.ctx.ellipse(centerX, screenY + size - 1, bodyW / 2.5, 2, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    // LOD: 中遠景簡化渲染
    if (zoom <= 0.75) {
      // 簡化：只畫身體和頭
      this.ctx.fillStyle = bodyColor;
      this.ctx.beginPath();
      this.ctx.ellipse(centerX, centerY, bodyW / 2, bodyH / 2, 0, 0, Math.PI * 2);
      this.ctx.fill();
      // 簡化頭
      this.ctx.fillStyle = '#3d3d3d';
      const headSize = isAdult ? size * 0.18 : size * 0.12;
      this.ctx.beginPath();
      this.ctx.arc(centerX - bodyW / 2.5, centerY - bodyH / 6, headSize, 0, Math.PI * 2);
      this.ctx.fill();
      return;
    }
    
    // === 腿部（4隻腳）===
    const legColor = '#2a2a2a';
    const legW = isAdult ? 2 : 1.5;
    const legH = isAdult ? 4 : 3;
    this.ctx.fillStyle = legColor;
    // 後腿
    this.ctx.fillRect(centerX - bodyW / 3, centerY + bodyH / 3, legW, legH);
    this.ctx.fillRect(centerX + bodyW / 4 - legW, centerY + bodyH / 3, legW, legH);
    // 前腿
    this.ctx.fillRect(centerX - bodyW / 2.5, centerY + bodyH / 4, legW, legH);
    this.ctx.fillRect(centerX + bodyW / 3.5 - legW, centerY + bodyH / 4, legW, legH);
    
    // === 毛茸茸邊緣（有羊毛時）===
    if (sheep.wool_ready) {
      this.ctx.fillStyle = '#f0f0f0';
      const fluffCount = 10;
      for (let i = 0; i < fluffCount; i++) {
        const angle = (i / fluffCount) * Math.PI * 2;
        const fluffX = centerX + Math.cos(angle) * (bodyW / 2) * 0.85;
        const fluffY = centerY + Math.sin(angle) * (bodyH / 2) * 0.85;
        this.ctx.beginPath();
        this.ctx.arc(fluffX, fluffY, isAdult ? 3 : 2, 0, Math.PI * 2);
        this.ctx.fill();
      }
    }
    
    // === 身體主體（橢圓）===
    this.ctx.fillStyle = bodyColor;
    this.ctx.beginPath();
    this.ctx.ellipse(centerX, centerY, bodyW / 2, bodyH / 2, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 身體底部陰影
    this.ctx.fillStyle = bodyColorDark;
    this.ctx.beginPath();
    this.ctx.ellipse(centerX, centerY + bodyH / 4, bodyW / 2.5, bodyH / 4, 0, 0, Math.PI);
    this.ctx.fill();
    
    // === 頭部 ===
    const headColor = '#3d3d3d';
    const headColorLight = '#4a4a4a';
    const headSize = isAdult ? size * 0.22 : size * 0.16;
    const headX = centerX - bodyW / 2.5;
    const headY = centerY - bodyH / 6;
    
    // 頭部主體
    this.ctx.fillStyle = headColor;
    this.ctx.beginPath();
    this.ctx.ellipse(headX, headY, headSize, headSize * 0.85, 0, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 頭部高光
    this.ctx.fillStyle = headColorLight;
    this.ctx.beginPath();
    this.ctx.arc(headX - 1, headY - 1, headSize * 0.4, 0, Math.PI * 2);
    this.ctx.fill();
    
    // === 耳朵 ===
    this.ctx.fillStyle = headColor;
    // 左耳
    this.ctx.beginPath();
    this.ctx.ellipse(headX - headSize * 0.7, headY - headSize * 0.3, 2, 3, -0.5, 0, Math.PI * 2);
    this.ctx.fill();
    // 右耳
    this.ctx.beginPath();
    this.ctx.ellipse(headX - headSize * 0.2, headY - headSize * 0.8, 2, 3, 0.3, 0, Math.PI * 2);
    this.ctx.fill();
    
    // === 眼睛 ===
    this.ctx.fillStyle = '#1a1a1a';
    this.ctx.fillRect(headX - 2, headY - 1, 1, 2);
    
    // === 鼻子 ===
    this.ctx.fillStyle = '#e8b4b4';
    this.ctx.fillRect(headX - headSize - 1, headY + 1, 2, 2);
    
    // === 尾巴（小圓球）===
    if (sheep.wool_ready) {
      this.ctx.fillStyle = '#f8f8f8';
      this.ctx.beginPath();
      this.ctx.arc(centerX + bodyW / 2 - 1, centerY, isAdult ? 3 : 2, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }
  
  // ==================== 玩家 ====================
  
  /**
   * 渲染玩家
   */
  renderPlayer(player) {
    const { x: screenX, y: screenY } = this.toScreen(player.x, player.y);
    const size = this.tileSize;
    
    // 玩家高亮邊框
    this.ctx.strokeStyle = '#ffd700';
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(screenX + 1, screenY + 1, size - 2, size - 2);
    
    // 身體
    this.ctx.fillStyle = '#4a90d9';
    this.ctx.fillRect(screenX + 3, screenY + 4, size - 6, size - 4);
    
    // 頭
    this.ctx.fillStyle = '#ffd5b4';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + 4, 4, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 名字
    this.ctx.fillStyle = '#ffd700';
    this.ctx.font = 'bold 9px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(player.name, screenX + size / 2, screenY - 2);
  }
}
