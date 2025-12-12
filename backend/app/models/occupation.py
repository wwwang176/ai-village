"""
職業類別定義
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class OccupationType:
    """職業類型定義"""
    id: str                    # farmer, miller, baker...
    name: str                  # 農夫, 磨坊主, 麵包師...
    tier: int                  # 層級 1, 2, 3
    chain: str                 # 產業鏈: food, tool, clothing
    building: str              # 工作建築 ID
    
    # 工具需求
    required_tool: Optional[str] = None
    
    # 生產配方
    input_materials: List[Tuple[str, int]] = field(default_factory=list)  # [(item_id, quantity), ...]
    output_product: str = ""
    output_quantity: int = 0
    work_time: int = 2         # 工作所需時間（遊戲時間單位）
    
    def needs_tool(self) -> bool:
        """是否需要工具"""
        return self.required_tool is not None
    
    def get_required_materials(self) -> List[Tuple[str, int]]:
        """取得所需原料"""
        return self.input_materials
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier,
            "chain": self.chain,
            "building": self.building,
            "required_tool": self.required_tool,
            "input_materials": self.input_materials,
            "output_product": self.output_product,
            "output_quantity": self.output_quantity,
        }
