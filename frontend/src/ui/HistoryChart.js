import { OCCUPATION_NAMES } from '../entities/Villager.js';

/**
 * 歷史數據圖表組件
 */

export class HistoryChart {
  constructor(apiClient) {
    this.apiClient = apiClient;
    this.chart = null;
    this.isOpen = false;
    
    // DOM 元素
    this.modal = document.getElementById('chart-modal');
    this.chartBtn = document.getElementById('chart-btn');
    this.closeBtn = document.getElementById('chart-close-btn');
    this.targetSelect = document.getElementById('chart-target');
    this.rangeSelect = document.getElementById('chart-range');
    this.canvas = document.getElementById('history-chart');
    
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    // 開啟圖表
    this.chartBtn.addEventListener('click', () => this.toggle());
    
    // 關閉圖表
    this.closeBtn.addEventListener('click', () => this.close());
    
    // 切換目標（全體/個人）
    this.targetSelect.addEventListener('change', () => this.loadData());
    
    // 切換時間範圍
    this.rangeSelect.addEventListener('change', () => this.loadData());
  }
  
  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }
  
  async open() {
    this.modal.classList.add('show');
    this.isOpen = true;
    await this.loadData();
  }
  
  close() {
    this.modal.classList.remove('show');
    this.isOpen = false;
  }
  
  async loadData() {
    try {
      const target = this.targetSelect.value;
      const range = parseInt(this.rangeSelect.value) || null;
      
      const villagerId = target === 'all' ? null : target;
      const hours = range === 0 ? null : range;
      
      const response = await this.apiClient.getHistory(hours, villagerId);
      
      if (response.success) {
        // 更新村民下拉選單
        this.updateVillagerSelect(response.villagers);
        
        // 更新圖表
        this.updateChart(response.data, villagerId !== null);
      }
    } catch (error) {
      console.error('Failed to load history data:', error);
    }
  }
  
  updateVillagerSelect(villagers) {
    const currentValue = this.targetSelect.value;
    
    // 保留「全體平均」選項
    this.targetSelect.innerHTML = '<option value="all">全體平均</option>';
    
    // 添加村民選項
    for (const v of villagers) {
      const option = document.createElement('option');
      option.value = v.id;
      const occupationText = OCCUPATION_NAMES[v.occupation] || v.occupation || '';
      option.textContent = occupationText ? `${v.name} (${occupationText})` : v.name;
      this.targetSelect.appendChild(option);
    }
    
    // 恢復選中值
    if (currentValue) {
      this.targetSelect.value = currentValue;
    }
  }
  
  updateChart(data, isIndividual) {
    if (!data || data.length === 0) {
      this.showNoData();
      return;
    }
    
    // 準備數據
    const labels = data.map(d => `第${d.day}天 ${String(d.hour).padStart(2, '0')}:00`);
    
    // 根據是否為個人數據選擇欄位
    const satietyKey = isIndividual ? 'satiety' : 'avg_satiety';
    const energyKey = isIndividual ? 'energy' : 'avg_energy';
    const socialKey = isIndividual ? 'social' : 'avg_social';
    const moneyKey = isIndividual ? 'money' : 'total_money';
    
    const energyData = data.map(d => d[energyKey]);
    const hungerData = data.map(d => 100 - d[satietyKey]);  // 飢餓 = 100 - 飽足度
    const socialData = data.map(d => d[socialKey]);
    const moneyData = data.map(d => d[moneyKey]);
    
    // 計算金錢的縮放比例（讓它和百分比數據在同一範圍內顯示）
    const maxMoney = Math.max(...moneyData, 1);
    const moneyScaled = moneyData.map(m => (m / maxMoney) * 100);
    
    const chartData = {
      labels,
      datasets: [
        {
          label: '體力',
          data: energyData,
          borderColor: '#4CAF50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          tension: 0.3,
          fill: false,
          pointRadius: 2,
          borderWidth: 2
        },
        {
          label: '飢餓',
          data: hungerData,
          borderColor: '#FF9800',
          backgroundColor: 'rgba(255, 152, 0, 0.1)',
          tension: 0.3,
          fill: false,
          pointRadius: 2,
          borderWidth: 2
        },
        {
          label: '社交',
          data: socialData,
          borderColor: '#2196F3',
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          tension: 0.3,
          fill: false,
          pointRadius: 2,
          borderWidth: 2
        },
        {
          label: isIndividual ? '金錢' : '總金錢',
          data: moneyScaled,
          borderColor: '#ffd700',
          backgroundColor: 'rgba(255, 215, 0, 0.1)',
          tension: 0.3,
          fill: false,
          pointRadius: 2,
          borderWidth: 2,
          yAxisID: 'y1'
        }
      ]
    };
    
    const options = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          display: false  // 使用自定義圖例
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const datasetLabel = context.dataset.label;
              const value = context.raw;
              
              // 金錢顯示原始值
              if (datasetLabel.includes('金錢')) {
                const originalValue = moneyData[context.dataIndex];
                return `${datasetLabel}: $${originalValue}`;
              }
              
              return `${datasetLabel}: ${value.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          display: true,
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: '#888',
            maxTicksLimit: 12,
            maxRotation: 45
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          min: 0,
          max: 100,
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: '#888',
            callback: (value) => `${value}%`
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          min: 0,
          max: 100,
          grid: {
            drawOnChartArea: false
          },
          ticks: {
            color: '#ffd700',
            callback: (value) => `$${Math.round(value / 100 * maxMoney)}`
          }
        }
      }
    };
    
    // 銷毀舊圖表
    if (this.chart) {
      this.chart.destroy();
    }
    
    // 創建新圖表
    this.chart = new Chart(this.canvas, {
      type: 'line',
      data: chartData,
      options
    });
  }
  
  showNoData() {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
    
    const ctx = this.canvas.getContext('2d');
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('尚無歷史數據', this.canvas.width / 2, this.canvas.height / 2);
  }
  
  // 定期更新（如果彈窗開啟中）
  async update() {
    if (this.isOpen) {
      await this.loadData();
    }
  }
}
