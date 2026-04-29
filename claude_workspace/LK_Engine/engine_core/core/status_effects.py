"""
状态效果枚举定义
ExtendedPetState / ExtendedBattleState 已合并进 core/models.py
此文件保留枚举定义，供其他模块导入
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class StatusEffectType(Enum):
    """状态效果类型"""
    # 基础状态
    POISON = "poison"              # 中毒
    POISON_MARK = "poison_mark"    # 中毒印记
    BURN = "burn"                  # 灼烧
    FREEZE = "freeze"              # 冻结
    PARASITE = "parasite"          # 寄生

    # 印记
    STAR_FALL_MARK = "star_fall_mark"           # 星陨印记：每层30威力魔法伤害（造成伤害后触发，消除所有层）
    DESCENT_MARK = "descent_mark"               # 降灵印记：入场时每层失去1能量
    THORN = "thorn"                             # 棘刺：入场时每层造成6%最大生命伤害
    FROST_MARK = "frost_mark"                   # 凝霜印记：速度-10（固定值）
    PHOTOSYNTHESIS_MARK = "photosynthesis_mark" # 光合印记：每回合每层恢复1点能量
    CHARGE_MARK = "charge_mark"                 # 蓄电印记：入场首回合技能威力+10
    MOMENTUM_MARK = "momentum_mark"             # 蓄势印记（旧数据，未见于wiki，保留）
    ATTACK_MARK = "attack_mark"                 # 攻击印记：每层使攻击技能威力+10（加法）
    WIND_MARK = "wind_mark"                     # 风起印记：先手攻击时每层伤害+20%（仅1回合）
    DRAGON_BITE_MARK = "dragon_bite_mark"       # 龙噬印记：释放5能耗技能时提升40%攻击（仅1回合）
    MOIST_MARK = "moist_mark"                   # 湿润印记：每层使所有技能能耗-1
    SLOW_MARK = "slow_mark"                     # 迟缓印记：后手攻击时每层伤害提升30%


# ── 兼容层：让旧的 import 不报错 ───────────────────────────────────

# ExtendedPetState 的状态现在直接存储在 PetInstance 里，
# 但为了兼容旧测试保留这个符号（指向 PetInstance 自身）
class ExtendedPetState:
    """已废弃：状态已内嵌进 PetInstance。此类仅用于兼容。"""
    def __init__(self):
        raise DeprecationWarning(
            "ExtendedPetState 已废弃，状态已内嵌进 PetInstance。"
            "请直接使用 PetInstance 上的 status_effects / freeze_stacks 等字段。"
        )


# ExtendedBattleState 的状态现在直接存储在 BattleState 里
class ExtendedBattleState:
    """已废弃：状态已内嵌进 BattleState。此类仅用于兼容。"""
    def __init__(self):
        raise DeprecationWarning(
            "ExtendedBattleState 已废弃，状态已内嵌进 BattleState。"
        )


# FieldMark 已移到 core/models.py，这里重新导出
from core.models import FieldMark, TeamState
