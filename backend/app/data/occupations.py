"""
職業類型定義
"""

from ..models.occupation import OccupationType


# ============================================================
# 職業類型定義（13 種）
# ============================================================

OCCUPATIONS = {
    # ========== 食物鏈 L1 ==========
    "farmer": OccupationType(
        id="farmer", name="農夫", tier=1, chain="food",
        building="farm",
        required_tool="hoe",
        input_materials=[],
        output_product="grain", output_quantity=2, work_time=2,
    ),
    
    # ========== 食物鏈 L2 ==========
    "miller": OccupationType(
        id="miller", name="磨坊主", tier=2, chain="food",
        building="mill",
        required_tool=None,
        input_materials=[("grain", 1)],
        output_product="flour", output_quantity=1, work_time=2,
    ),
    "butcher": OccupationType(
        id="butcher", name="屠夫", tier=2, chain="food",
        building="butcher_shop",
        required_tool="cleaver",
        input_materials=[("livestock", 1)],
        output_product="meat_raw", output_quantity=2, work_time=2,
    ),
    
    # ========== 食物鏈 L3 ==========
    "baker": OccupationType(
        id="baker", name="麵包師", tier=3, chain="food",
        building="bakery",
        required_tool=None,
        input_materials=[("flour", 1)],
        output_product="bread", output_quantity=2, work_time=2,
    ),
    
    # ========== 器具鏈 L1 ==========
    "miner": OccupationType(
        id="miner", name="礦工", tier=1, chain="tool",
        building="mine",
        required_tool="pickaxe",
        input_materials=[],
        output_product="ore", output_quantity=2, work_time=3,
    ),
    "lumberjack": OccupationType(
        id="lumberjack", name="伐木工", tier=1, chain="tool",
        building="lumber_camp",
        required_tool="axe",
        input_materials=[],
        output_product="wood", output_quantity=2, work_time=2,
    ),
    
    # ========== 器具鏈 L2 ==========
    "blacksmith": OccupationType(
        id="blacksmith", name="鐵匠", tier=2, chain="tool",
        building="blacksmith",
        required_tool="hammer",
        input_materials=[("ore", 1)],
        output_product="iron", output_quantity=1, work_time=3,
    ),
    "carpenter": OccupationType(
        id="carpenter", name="木匠", tier=2, chain="tool",
        building="carpentry",
        required_tool="saw",
        input_materials=[("wood", 1), ("iron", 1)],
        output_product="furniture", output_quantity=1, work_time=4,
    ),
    
    # ========== 服飾鏈 L1 ==========
    "shepherd": OccupationType(
        id="shepherd", name="牧羊人", tier=1, chain="clothing",
        building="pasture",
        required_tool="shears",
        input_materials=[],
        output_product="wool", output_quantity=2, work_time=3,
    ),
    
    # ========== 服飾鏈 L2 ==========
    "weaver": OccupationType(
        id="weaver", name="織工", tier=2, chain="clothing",
        building="weaver_shop",
        required_tool=None,
        input_materials=[("wool", 1)],
        output_product="cloth", output_quantity=1, work_time=3,
    ),
    "tanner": OccupationType(
        id="tanner", name="皮革匠", tier=2, chain="clothing",
        building="tannery",
        required_tool="scraper",
        input_materials=[("hide", 1)],
        output_product="leather", output_quantity=1, work_time=3,
    ),
    
    # ========== 服飾鏈 L3 ==========
    "tailor": OccupationType(
        id="tailor", name="裁縫", tier=3, chain="clothing",
        building="tailor_shop",
        required_tool="shears",
        input_materials=[("cloth", 1), ("leather", 1)],
        output_product="clothes", output_quantity=1, work_time=3,
    ),
    
    # ========== 特殊 ==========
    "merchant": OccupationType(
        id="merchant", name="商人", tier=0, chain="trade",
        building="market",
        required_tool=None,
        input_materials=[],
        output_product="", output_quantity=0, work_time=0,
    ),
}


def get_occupation(occupation_id: str) -> OccupationType:
    """取得職業類型"""
    if occupation_id not in OCCUPATIONS:
        raise ValueError(f"Unknown occupation: {occupation_id}")
    return OCCUPATIONS[occupation_id]


def get_all_occupations() -> list:
    """取得所有職業"""
    return list(OCCUPATIONS.values())


def get_occupations_by_tier(tier: int) -> list:
    """取得指定層級的職業"""
    return [occ for occ in OCCUPATIONS.values() if occ.tier == tier]


def get_occupations_by_chain(chain: str) -> list:
    """取得指定產業鏈的職業"""
    return [occ for occ in OCCUPATIONS.values() if occ.chain == chain]
