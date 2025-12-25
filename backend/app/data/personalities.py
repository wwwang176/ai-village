"""
性格維度設定
"""

PERSONALITY_DIMENSIONS = {
    "social": {
        "positive": "extrovert",
        "negative": "introvert",
        "descriptions": {
            "extrovert": "喜歡社交，常去廣場",
            "introvert": "偏好獨處，專注工作"
        }
    },
    "temper": {
        "positive": "friendly",
        "negative": "grumpy",
        "descriptions": {
            "friendly": "樂於助人，重視社交",
            "grumpy": "討厭被打擾，優先處理自己的事"
        }
    },
    "trust": {
        "positive": "trusting",
        "negative": "suspicious",
        "descriptions": {
            "trusting": "容易相信他人",
            "suspicious": "對陌生人保持警戒"
        }
    },
    "romance": {
        "positive": "romantic",
        "negative": "reserved",
        "descriptions": {
            "romantic": "容易產生好感，表達情感",
            "reserved": "感情內斂，不輕易表露"
        }
    },
    "courage": {
        "positive": "brave",
        "negative": "timid",
        "descriptions": {
            "brave": "狀態偏低也敢繼續撐",
            "timid": "狀態稍低就想處理"
        }
    },
    "outlook": {
        "positive": "optimistic",
        "negative": "pessimistic",
        "descriptions": {
            "optimistic": "傾向繼續工作",
            "pessimistic": "傾向先滿足需求"
        }
    },
    "schedule": {
        "positive": "early_bird",
        "negative": "night_owl",
        "descriptions": {
            "early_bird": "白天更積極",
            "night_owl": "夜間也願意活動"
        }
    }
}


def get_trait_description(trait: str) -> str:
    """根據性格特質取得描述"""
    for dim in PERSONALITY_DIMENSIONS.values():
        if trait in dim["descriptions"]:
            return dim["descriptions"][trait]
    return trait


def get_dimension_traits() -> dict:
    """取得每個維度的正反面特質（給 game_state 使用）"""
    return {
        dim: [data["positive"], data["negative"]]
        for dim, data in PERSONALITY_DIMENSIONS.items()
    }
