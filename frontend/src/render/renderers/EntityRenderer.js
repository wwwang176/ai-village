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
   * 渲染單一村民
   */
  renderVillager(villager, isSelected = false) {
    const { x: screenX, y: screenY } = this.toScreen(villager.x, villager.y);
    const size = this.tileSize;
    
    // 選中效果：發光圈
    if (isSelected) {
      this.ctx.fillStyle = 'rgba(255, 255, 100, 0.3)';
      this.ctx.beginPath();
      this.ctx.arc(screenX + size / 2, screenY + size / 2, size * 0.8, 0, Math.PI * 2);
      this.ctx.fill();
      
      this.ctx.strokeStyle = 'rgba(255, 255, 100, 0.8)';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.arc(screenX + size / 2, screenY + size / 2, size * 0.8, 0, Math.PI * 2);
      this.ctx.stroke();
    }
    
    // 身體
    this.ctx.fillStyle = villager.color || '#e0c080';
    this.ctx.fillRect(screenX + 3, screenY + 4, size - 6, size - 4);
    
    // 頭
    this.ctx.fillStyle = '#ffd5b4';
    this.ctx.beginPath();
    this.ctx.arc(screenX + size / 2, screenY + 4, 4, 0, Math.PI * 2);
    this.ctx.fill();
    
    // 名字
    this.ctx.fillStyle = isSelected ? '#ffff66' : '#fff';
    this.ctx.font = isSelected ? 'bold 9px sans-serif' : '8px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
    this.ctx.shadowBlur = 2;
    this.ctx.shadowOffsetX = 1;
    this.ctx.shadowOffsetY = 1;
    this.ctx.fillText(villager.name, screenX + size / 2, screenY + size + 8);
    this.ctx.shadowColor = 'transparent';
    this.ctx.shadowBlur = 0;
    this.ctx.shadowOffsetX = 0;
    this.ctx.shadowOffsetY = 0;
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
    const { x: screenX, y: screenY } = this.toScreen(sheep.x, sheep.y);
    const size = this.tileSize;
    
    const bodyColor = sheep.is_adult ? '#f5f5dc' : '#fffacd';
    const headColor = '#2f2f2f';
    
    // 羊身體（橢圓）
    this.ctx.fillStyle = bodyColor;
    this.ctx.beginPath();
    const bodyW = sheep.is_adult ? size * 0.7 : size * 0.5;
    const bodyH = sheep.is_adult ? size * 0.5 : size * 0.35;
    this.ctx.ellipse(
      screenX + size / 2, 
      screenY + size / 2 + 2,
      bodyW / 2, bodyH / 2,
      0, 0, Math.PI * 2
    );
    this.ctx.fill();
    
    // 羊頭
    this.ctx.fillStyle = headColor;
    this.ctx.beginPath();
    const headSize = sheep.is_adult ? size * 0.2 : size * 0.15;
    this.ctx.arc(
      screenX + size / 2 - bodyW / 3,
      screenY + size / 2,
      headSize,
      0, Math.PI * 2
    );
    this.ctx.fill();
    
    // 羊毛可剪標記
    if (sheep.wool_ready) {
      this.ctx.fillStyle = '#4CAF50';
      this.ctx.beginPath();
      this.ctx.arc(screenX + size - 4, screenY + 4, 3, 0, Math.PI * 2);
      this.ctx.fill();
    }
    
    // 小羊年齡標記
    if (!sheep.is_adult) {
      this.ctx.font = '8px sans-serif';
      this.ctx.fillStyle = '#ff9800';
      this.ctx.textAlign = 'center';
      this.ctx.fillText('小', screenX + size / 2, screenY + size - 2);
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
