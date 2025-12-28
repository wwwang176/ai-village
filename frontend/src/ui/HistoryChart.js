import { OCCUPATION_NAMES } from '../entities/Villager.js';

/**
 * 歷史數據圖表組件
 */

// 產品顏色對應表
const PRODUCT_COLORS = {
  bread: '#8B4513',
  meat_raw: '#CD5C5C',
  meat: '#B22222',
  flour: '#F5DEB3',
  grain: '#DAA520',
  wood: '#654321',
  ore: '#708090',
  iron: '#4682B4',
  wool: '#DDA0DD',
  cloth: '#9370DB',
  hide: '#C4A484',
  leather: '#A0522D',
  furniture: '#D2691E',
  clothes: '#4169E1'
};

export class HistoryChart {
  constructor(apiClient) {
    this.apiClient = apiClient;
    this.chart = null;
    this.productChart = null;
    this.isOpen = false;
    this.currentTab = 'stats';
    this.historyData = null;
    
    // DOM 元素 - 村民狀態
    this.modal = document.getElementById('chart-modal');
    this.chartBtn = document.getElementById('chart-btn');
    this.closeBtn = document.getElementById('chart-close-btn');
    this.targetSelect = document.getElementById('chart-target');
    this.rangeSelect = document.getElementById('chart-range');
    this.canvas = document.getElementById('history-chart');
    
    // DOM 元素 - Tab
    this.tabs = document.querySelectorAll('.chart-tab');
    this.statsPanel = document.getElementById('chart-stats-panel');
    this.productsPanel = document.getElementById('chart-products-panel');
    
    // DOM 元素 - 產品
    this.productRangeSelect = document.getElementById('product-chart-range');
    this.productFilter = document.getElementById('product-filter');
    this.productCanvas = document.getElementById('product-chart');
    
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
    
    // Tab 切換
    this.tabs.forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });
    
    // 產品時間範圍
    if (this.productRangeSelect) {
      this.productRangeSelect.addEventListener('change', () => this.updateProductChart());
    }
    
    // 產品篩選
    if (this.productFilter) {
      this.productFilter.addEventListener('change', () => this.updateProductChart());
    }
  }
  
  switchTab(tabName) {
    this.currentTab = tabName;
    
    // 更新 Tab 樣式
    this.tabs.forEach(tab => {
      tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // 更新 Panel 顯示
    if (this.statsPanel) {
      this.statsPanel.classList.toggle('active', tabName === 'stats');
    }
    if (this.productsPanel) {
      this.productsPanel.classList.toggle('active', tabName === 'products');
    }
    
    // 載入對應數據
    if (tabName === 'products') {
      this.updateProductChart();
    }
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
        // 儲存完整數據供產品圖表使用
        this.historyData = response.data;
        
        // 更新村民下拉選單
        this.updateVillagerSelect(response.villagers);
        
        // 更新圖表
        this.updateChart(response.data, villagerId !== null);
      }
    } catch (error) {
      console.error('Failed to load history data:', error);
    }
  }
  
  async updateProductChart() {
    // 根據產品時間範圍載入數據
    const range = parseInt(this.productRangeSelect?.value) || 0;
    const hours = range === 0 ? null : range;
    
    try {
      const response = await this.apiClient.getHistory(hours, null);
      if (!response.success || !response.data || response.data.length === 0) {
        this.showNoProductData();
        return;
      }
      var data = response.data;
    } catch (error) {
      console.error('Failed to load product history:', error);
      this.showNoProductData();
      return;
    }
    
    // 取得選中的產品
    const selectedProducts = [];
    if (this.productFilter) {
      const checkboxes = this.productFilter.querySelectorAll('input[type="checkbox"]:checked');
      checkboxes.forEach(cb => selectedProducts.push(cb.value));
    }
    
    if (selectedProducts.length === 0) {
      this.showNoProductData('請選擇至少一個產品');
      return;
    }
    
    // 準備數據
    const labels = data.map(d => `第${d.day}天 ${String(d.hour).padStart(2, '0')}:00`);
    
    const datasets = selectedProducts.map(productId => {
      const productData = data.map(d => {
        const products = d.products || {};
        return products[productId] || 0;
      });
      
      return {
        label: this.getProductName(productId),
        data: productData,
        borderColor: PRODUCT_COLORS[productId] || '#888',
        backgroundColor: PRODUCT_COLORS[productId] || '#888',
        tension: 0.3,
        fill: false,
        pointRadius: 2,
        borderWidth: 2
      };
    });
    
    const chartData = { labels, datasets };
    
    const options = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: '#ccc',
            boxWidth: 12,
            boxHeight: 12,
            padding: 10,
            usePointStyle: false
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: ${context.raw} 個`
          }
        }
      },
      scales: {
        x: {
          display: true,
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: '#888', maxTicksLimit: 12, maxRotation: 45 }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          min: 0,
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: '#888' }
        }
      }
    };
    
    // 銷毀舊圖表
    if (this.productChart) {
      this.productChart.destroy();
    }
    
    // 創建新圖表
    if (this.productCanvas) {
      this.productChart = new Chart(this.productCanvas, {
        type: 'line',
        data: chartData,
        options
      });
    }
  }
  
  getProductName(productId) {
    const names = {
      bread: '🍞 麵包',
      meat_raw: '🥩 生肉',
      meat: '🍖 熟肉',
      flour: '🌫️ 麵粉',
      grain: '🌾 穀物',
      wood: '🪵 木材',
      ore: '🪨 礦石',
      iron: '🔩 鐵錠',
      wool: '☁️ 羊毛',
      cloth: '🧵 布料',
      hide: '🟫 獸皮',
      leather: '🟤 皮革',
      furniture: '🪑 家具',
      clothes: '👕 衣服'
    };
    return names[productId] || productId;
  }
  
  showNoProductData(message = '尚無產品數據') {
    if (this.productChart) {
      this.productChart.destroy();
      this.productChart = null;
    }
    
    if (this.productCanvas) {
      const ctx = this.productCanvas.getContext('2d');
      ctx.clearRect(0, 0, this.productCanvas.width, this.productCanvas.height);
      ctx.fillStyle = '#666';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(message, this.productCanvas.width / 2, this.productCanvas.height / 2);
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
    const satietyData = data.map(d => d[satietyKey]);
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
          label: '飽足',
          data: satietyData,
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
      // 如果當前是產品 Tab，也更新產品圖表
      if (this.currentTab === 'products') {
        this.updateProductChart();
      }
    }
  }
}
