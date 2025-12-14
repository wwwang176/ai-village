/**
 * 天氣特效系統
 */
export class WeatherEffect {
  constructor() {
    this.effectsContainer = document.getElementById('weather-effects');
    this.overlay = document.getElementById('weather-overlay');
    this.weatherIcon = document.getElementById('weather-icon');
    
    this.currentWeather = 'sunny';
    this.raindrops = [];
    this.lightningTimeout = null;
    this.isRaining = false;
  }
  
  /**
   * 更新天氣狀態
   */
  update(weatherInfo) {
    if (!weatherInfo) return;
    
    const newWeather = weatherInfo.id;
    
    // 更新天氣圖示
    if (this.weatherIcon) {
      this.weatherIcon.textContent = weatherInfo.icon;
    }
    
    // 更新遮罩（調暗畫面）
    if (this.overlay) {
      const darkness = weatherInfo.darkness || 0;
      this.overlay.style.background = `rgba(0, 0, 0, ${darkness})`;
    }
    
    // 天氣變化時更新特效
    if (newWeather !== this.currentWeather) {
      this.currentWeather = newWeather;
      this.updateEffects();
    }
  }
  
  /**
   * 根據天氣更新特效
   */
  updateEffects() {
    // 清除現有特效
    this.clearEffects();
    
    switch (this.currentWeather) {
      case 'rainy':
        this.startRain(50);  // 中等雨量
        break;
      case 'stormy':
        this.startRain(100); // 大雨
        this.startLightning();
        break;
      default:
        // 晴天或多雲不需要特效
        break;
    }
  }
  
  /**
   * 開始下雨
   */
  startRain(intensity) {
    if (this.isRaining) return;
    this.isRaining = true;
    
    // 建立雨滴
    for (let i = 0; i < intensity; i++) {
      this.createRaindrop();
    }
  }
  
  /**
   * 建立單個雨滴
   */
  createRaindrop() {
    const drop = document.createElement('div');
    drop.className = 'raindrop';
    
    // 隨機位置和動畫參數
    const left = Math.random() * 100;
    const height = 15 + Math.random() * 25;
    const duration = 0.3 + Math.random() * 0.4;
    const delay = Math.random() * 2;
    
    drop.style.left = `${left}%`;
    drop.style.height = `${height}px`;
    drop.style.animationDuration = `${duration}s`;
    drop.style.animationDelay = `${delay}s`;
    
    this.effectsContainer.appendChild(drop);
    this.raindrops.push(drop);
  }
  
  /**
   * 開始閃電
   */
  startLightning() {
    // 建立閃電元素（如果不存在）
    let lightning = this.effectsContainer.querySelector('.lightning');
    if (!lightning) {
      lightning = document.createElement('div');
      lightning.className = 'lightning';
      this.effectsContainer.appendChild(lightning);
    }
    
    // 單次閃爍
    const singleFlash = (opacity) => {
      lightning.style.setProperty('--flash-opacity', opacity);
      lightning.classList.remove('flash');
      void lightning.offsetWidth; // 強制重繪
      lightning.classList.add('flash');
    };
    
    // 多次連閃
    const triggerLightning = () => {
      if (this.currentWeather !== 'stormy') return;
      
      const flashCount = 2 + Math.floor(Math.random() * 2); // 2~3 次
      
      for (let i = 0; i < flashCount; i++) {
        setTimeout(() => {
          // 每次亮度隨機 (0.3~0.6)，第一閃稍亮
          const opacity = i === 0 
            ? 0.4 + Math.random() * 0.2   // 第一閃：0.4~0.6
            : 0.3 + Math.random() * 0.2;  // 後續：0.3~0.5
          singleFlash(opacity);
        }, i * (80 + Math.random() * 70)); // 間隔 80~150ms
      }
      
      // 下次閃電（5~15秒後）
      const nextDelay = 5000 + Math.random() * 10000;
      this.lightningTimeout = setTimeout(triggerLightning, nextDelay);
    };
    
    // 首次閃電（2~5秒後）
    const initialDelay = 2000 + Math.random() * 3000;
    this.lightningTimeout = setTimeout(triggerLightning, initialDelay);
  }
  
  /**
   * 清除所有特效
   */
  clearEffects() {
    this.isRaining = false;
    
    // 移除雨滴
    this.raindrops.forEach(drop => drop.remove());
    this.raindrops = [];
    
    // 停止閃電
    if (this.lightningTimeout) {
      clearTimeout(this.lightningTimeout);
      this.lightningTimeout = null;
    }
    
    // 移除閃電元素
    const lightning = this.effectsContainer?.querySelector('.lightning');
    if (lightning) {
      lightning.remove();
    }
  }
  
  /**
   * 銷毀
   */
  destroy() {
    this.clearEffects();
  }
}
