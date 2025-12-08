/**
 * 時間系統 - 管理遊戲內時間流動
 */

export class TimeSystem {
  constructor(config = {}) {
    // 遊戲時間倍率：1 現實秒 = N 遊戲秒
    this.timeScale = config.timeScale || 60;
    
    // 當前遊戲時間
    this.day = 1;
    this.hour = 8;    // 從早上 8 點開始
    this.minute = 0;
    
    // 累積的遊戲秒數
    this.totalGameSeconds = 0;
  }
  
  /**
   * 更新時間
   * @param {number} deltaTime - 現實時間差（秒）
   */
  update(deltaTime) {
    // 計算遊戲時間流逝
    const gameSeconds = deltaTime * this.timeScale;
    this.totalGameSeconds += gameSeconds;
    
    // 累加分鐘
    this.minute += gameSeconds / 60;
    
    // 進位：分鐘 -> 小時 -> 天
    while (this.minute >= 60) {
      this.minute -= 60;
      this.hour++;
    }
    
    while (this.hour >= 24) {
      this.hour -= 24;
      this.day++;
    }
  }
  
  /**
   * 取得格式化時間字串
   */
  getTimeString() {
    const h = String(Math.floor(this.hour)).padStart(2, '0');
    const m = String(Math.floor(this.minute)).padStart(2, '0');
    return `第 ${this.day} 天 ${h}:${m}`;
  }
  
  /**
   * 取得當前時段
   */
  getPeriod() {
    const h = this.hour;
    if (h >= 5 && h < 7) return 'dawn';      // 黎明
    if (h >= 7 && h < 12) return 'morning';  // 上午
    if (h >= 12 && h < 17) return 'afternoon'; // 下午
    if (h >= 17 && h < 20) return 'evening'; // 傍晚
    return 'night'; // 夜晚
  }
  
  /**
   * 取得光照強度 (0-1)
   */
  getLightLevel() {
    const h = this.hour;
    
    if (h >= 7 && h < 17) {
      return 1.0; // 白天全亮
    } else if (h >= 5 && h < 7) {
      // 黎明漸亮
      return 0.3 + (h - 5) * 0.35;
    } else if (h >= 17 && h < 20) {
      // 傍晚漸暗
      return 1.0 - (h - 17) * 0.25;
    } else {
      return 0.25; // 夜晚
    }
  }
  
  /**
   * 是否為工作時間
   */
  isWorkHour() {
    return this.hour >= 8 && this.hour < 12 || this.hour >= 14 && this.hour < 18;
  }
  
  /**
   * 是否為睡眠時間
   */
  isSleepTime() {
    return this.hour >= 22 || this.hour < 6;
  }
}
