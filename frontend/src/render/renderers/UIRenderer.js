/**
 * UI 渲染器 - 對話泡泡等
 */
import { BaseRenderer } from './BaseRenderer.js';

export class UIRenderer extends BaseRenderer {
  constructor(ctx, camera, tileSize) {
    super(ctx, camera, tileSize);
  }
  
  /**
   * 渲染村民的對話泡泡（舊方法，保留相容性）
   */
  renderVillagerBubbles(villagers) {
    for (const villager of villagers) {
      if (villager.bubble) {
        this.renderSingleBubble(villager);
      }
    }
  }
  
  /**
   * 渲染單一村民的對話泡泡（用於 Y-sorting）
   */
  renderSingleBubble(villager) {
    if (!villager.bubble) return;
    const { x: screenX, y: screenY } = this.toScreen(villager.x, villager.y);
    this.renderBubble(screenX + this.tileSize / 2, screenY - 8, villager.bubble);
  }
  
  /**
   * 渲染對話泡泡（支援多行和自動換行）
   */
  renderBubble(x, y, bubble) {
    const text = bubble.text || '';
    const type = bubble.type || 'speech';
    
    if (!text) return;
    
    const fontSize = 12;
    this.ctx.font = `bold ${fontSize}px sans-serif`;
    const maxWidth = 180;
    const padding = 10;
    const lineHeight = fontSize + 6;
    
    // 自動換行處理
    const lines = this.wrapText(text, maxWidth);
    
    // 計算泡泡大小
    const lineWidths = lines.map(line => this.ctx.measureText(line).width);
    const maxLineWidth = Math.max(...lineWidths);
    
    const bubbleWidth = maxLineWidth + padding * 2;
    const bubbleHeight = lines.length * lineHeight + padding * 2;
    const bubbleX = x - bubbleWidth / 2;
    const bubbleY = y - bubbleHeight - 12;
    
    // 泡泡背景
    this.ctx.fillStyle = type === 'thought' ? 'rgba(200, 200, 255, 0.95)' : 
                         type === 'action' ? 'rgba(255, 240, 200, 0.95)' : 
                         'rgba(255, 255, 255, 0.95)';
    
    this.roundRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight, 6);
    this.ctx.fill();
    
    // 泡泡邊框
    this.ctx.strokeStyle = type === 'thought' ? '#8888cc' : 
                           type === 'action' ? '#ccaa55' : 
                           '#888';
    this.ctx.lineWidth = 2;
    this.roundRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight, 6);
    this.ctx.stroke();
    
    // 小三角或圓點
    if (type === 'speech') {
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      this.ctx.beginPath();
      this.ctx.moveTo(x - 6, bubbleY + bubbleHeight);
      this.ctx.lineTo(x, bubbleY + bubbleHeight + 8);
      this.ctx.lineTo(x + 6, bubbleY + bubbleHeight);
      this.ctx.closePath();
      this.ctx.fill();
      this.ctx.stroke();
    } else if (type === 'thought') {
      this.ctx.fillStyle = 'rgba(200, 200, 255, 0.95)';
      this.ctx.beginPath();
      this.ctx.arc(x, bubbleY + bubbleHeight + 5, 4, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.beginPath();
      this.ctx.arc(x - 3, bubbleY + bubbleHeight + 12, 3, 0, Math.PI * 2);
      this.ctx.fill();
    }
    
    // 繪製多行文字
    this.ctx.fillStyle = '#333';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'top';
    
    for (let i = 0; i < lines.length; i++) {
      const lineY = bubbleY + padding + i * lineHeight;
      this.ctx.fillText(lines[i], x, lineY);
    }
  }
  
  /**
   * 自動換行處理
   */
  wrapText(text, maxWidth) {
    const result = [];
    const paragraphs = text.split('\n');
    
    for (const paragraph of paragraphs) {
      if (this.ctx.measureText(paragraph).width <= maxWidth) {
        result.push(paragraph);
      } else {
        let line = '';
        for (const char of paragraph) {
          const testLine = line + char;
          if (this.ctx.measureText(testLine).width > maxWidth) {
            if (line) result.push(line);
            line = char;
          } else {
            line = testLine;
          }
        }
        if (line) result.push(line);
      }
    }
    return result;
  }
}
