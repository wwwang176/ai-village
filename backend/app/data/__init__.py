"""
Data 模組 - 定義遊戲數據
"""

from .items import ITEM_TYPES, get_item_type
from .occupations import OCCUPATIONS, get_occupation
from .supply_chain import SUPPLY_CHAIN, MATERIAL_PRODUCERS, get_supplier_occupation

__all__ = [
    "ITEM_TYPES",
    "get_item_type",
    "OCCUPATIONS",
    "get_occupation",
    "SUPPLY_CHAIN",
    "MATERIAL_PRODUCERS",
    "get_supplier_occupation",
]
