"""
天氣系統設定
"""

from typing import List
from dataclasses import dataclass


# ============================================================
# 天氣類型定義
# ============================================================

@dataclass
class WeatherType:
    id: str
    name: str
    icon: str
    stamina_drain: int  # 室外額外體力消耗 per tick
    darkness: float     # 畫面變暗程度 (0.0 ~ 1.0)


WEATHER_TYPES = {
    "sunny": WeatherType(
        id="sunny", name="晴天", icon="☀️",
        stamina_drain=0, darkness=0.0
    ),
    "cloudy": WeatherType(
        id="cloudy", name="多雲", icon="⛅",
        stamina_drain=0, darkness=0.1
    ),
    "rainy": WeatherType(
        id="rainy", name="下雨", icon="🌧️",
        stamina_drain=1, darkness=0.2
    ),
    "stormy": WeatherType(
        id="stormy", name="暴風雨", icon="⛈️",
        stamina_drain=2, darkness=0.4
    ),
}


# 天氣轉換機率（從當前天氣 → 下一個天氣的機率）
# 確保每行加總為 1.0
WEATHER_TRANSITIONS = {
    "sunny": {"sunny": 0.6, "cloudy": 0.3, "rainy": 0.1, "stormy": 0.0},
    "cloudy": {"sunny": 0.3, "cloudy": 0.4, "rainy": 0.25, "stormy": 0.05},
    "rainy": {"sunny": 0.1, "cloudy": 0.3, "rainy": 0.4, "stormy": 0.2},
    "stormy": {"sunny": 0.0, "cloudy": 0.2, "rainy": 0.5, "stormy": 0.3},
}


# 天氣持續時間範圍（遊戲小時）
WEATHER_DURATION_MIN = 1
WEATHER_DURATION_MAX = 8


# ============================================================
# 室外建築定義
# ============================================================

# 開放式建築（沒有遮蔽，受天氣影響）
OUTDOOR_BUILDINGS = ['farm', 'mine', 'lumber_camp', 'pasture', 'plaza']


# ============================================================
# 輔助函數
# ============================================================

def get_weather_type(weather_id: str) -> WeatherType:
    """取得天氣類型"""
    return WEATHER_TYPES.get(weather_id, WEATHER_TYPES["sunny"])


def is_outdoor_building(building_type: str) -> bool:
    """檢查建築物是否為室外"""
    return building_type in OUTDOOR_BUILDINGS


def get_stamina_drain(weather_id: str) -> int:
    """取得天氣的室外體力消耗"""
    weather = get_weather_type(weather_id)
    return weather.stamina_drain
