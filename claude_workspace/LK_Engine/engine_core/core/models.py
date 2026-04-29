"""
核心数据模型定义
定义精灵、技能、状态等核心结构
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import copy


class DamageType(Enum):
    """伤害类型"""
    PHYSICAL = "physical"  # 物理
    MAGICAL = "magical"    # 魔法


class SkillCategory(Enum):
    """技能类别"""
    ATTACK = "attack"      # 攻击
    DEFENSE = "defense"    # 防御
    STATUS = "status"      # 状态


class EffectType(Enum):
    """效果类型"""
    ENERGY_RESTORE = "energy_restore"
    POWER_BONUS = "power_bonus"
    STAT_BUFF = "stat_buff"
    STAT_DEBUFF = "stat_debuff"
    DAMAGE_REDUCTION = "damage_reduction"
    DYNAMIC_POWER = "dynamic_power"
    LIFESTEAL = "lifesteal"        # 吸血
    EXTRA_HITS = "extra_hits"      # 使用次数+1
    APPLY_STATUS = "apply_status"  # 施加状态（中毒/灼烧/冻结/寄生等）
    APPLY_MARK = "apply_mark"      # 施加印记
    HEAL = "heal"                  # 治疗
    SWITCH_OUT = "switch_out"      # 离场/紧急脱离
    REVIVE = "revive"              # 复活
    CUTE = "cute"                  # 萌化（清除对手增益并施加减益）
    RETURN = "return"              # 折返（打完立即换精灵）
    CHARGE = "charge"              # 蓄力（下回合威力翻倍）
    SWIFT = "swift"                # 迅捷（获得先手）
    BURST = "burst"                # 迸发（入场时威力额外加成）
    DISPEL_BUFF = "dispel_buff"    # 驱散增益
    DISPEL_DEBUFF = "dispel_debuff"  # 驱散减益
    DISPEL_MARK = "dispel_mark"    # 驱散印记
    COUNTER = "counter"            # 应对额外效果


@dataclass
class Effect:
    """技能效果"""
    type: EffectType
    target: str  # "self" or "opponent"
    value: float
    conditional: bool = False
    desc: str = ""
    # 施加状态时的额外参数
    status_type: str = ""   # 状态类型名称
    stacks: int = 1         # 层数


@dataclass
class Skill:
    """技能定义"""
    name: str
    element: str  # 属性
    category: SkillCategory
    damage_type: Optional[DamageType]
    base_power: int
    energy_cost: int
    hits: int = 1
    priority: int = 0  # 先手等级
    damage_reduction: float = 0.0
    effects: List[Effect] = field(default_factory=list)
    counters: List[str] = field(default_factory=list)  # 应对类型
    cooldown: int = 0  # 冷却回合数
    desc: str = ""  # 原始描述，供槽位/传动等文本规则解析

    def __hash__(self):
        return hash(self.name)


@dataclass
class Trait:
    """特性"""
    name: str
    desc: str
    icon_url: str = ""


@dataclass
class PetTemplate:
    """精灵模板（种族数据）"""
    id: int
    name: str
    types: List[str]  # 属性列表（1-2个）
    stats: Dict[str, int]  # 种族值：生命、物攻、魔攻、物防、魔防、速度
    traits: List[Trait]
    learnable_skills: List[str]  # 可学习的技能名称列表
    evolution: List[Dict] = field(default_factory=list)
    is_legendary: bool = False  # 是否为传说精灵

    bloodline: str = "unknown"  # supplemental bloodline support
    weight_kg: float = 0.0      # 精灵体重（KG，取均值）；0.0 表示未知
    def __hash__(self):
        return hash((self.id, self.name))


@dataclass
class StatModifier:
    """属性修正（层数，每层10%）"""
    physical_attack: int = 0
    magical_attack: int = 0
    physical_defense: int = 0
    magical_defense: int = 0
    speed: int = 0

    def copy(self) -> 'StatModifier':
        return StatModifier(
            physical_attack=self.physical_attack,
            magical_attack=self.magical_attack,
            physical_defense=self.physical_defense,
            magical_defense=self.magical_defense,
            speed=self.speed
        )


@dataclass
class PetInstance:
    """精灵实例（对战中的精灵）"""
    template: PetTemplate
    current_hp: int
    max_hp: int
    stats: Dict[str, int]  # 实际属性值
    skills: List[Skill]  # 携带的技能（最多4个）
    current_energy: int = 10
    stat_modifiers: StatModifier = field(default_factory=StatModifier)
    skill_cooldowns: Dict[str, int] = field(default_factory=dict)
    is_alive: bool = True

    # 扩展状态（原 ExtendedPetState，直接内嵌）
    # 状态效果：{StatusEffectType -> stacks}
    status_effects: Dict = field(default_factory=dict)
    freeze_stacks: int = 0          # 冻结层数（不随离场消失）
    stun_turns: int = 0             # 眩晕剩余回合数（无法行动）
    skill_transmission: Dict = field(default_factory=dict)  # 技能位传动
    charging_skill: Optional[str] = None   # 正在蓄力的技能
    burst_turns_remaining: int = 0  # 迸发状态剩余回合
    just_entered: bool = False      # 本回合是否刚入场
    pending_switch_out: bool = False  # 是否待命离场（折返/紧急脱离）
    priority_bonus: int = 0         # 额外先手等级（迅捷效果，回合结束后重置）
    runtime_flags: Dict[str, object] = field(default_factory=dict)

    def __getattr__(self, name: str):
        """
        兼容旧的 pet._xxx 运行时字段访问，并将其统一托管到 runtime_flags。
        """
        if name.startswith("_"):
            runtime_flags = self.__dict__.get("runtime_flags", {})
            if name in runtime_flags:
                return runtime_flags[name]
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def __setattr__(self, name: str, value):
        """
        兼容旧的 pet._xxx 运行时字段写入，避免搜索树 copy 时丢失状态。
        """
        if name.startswith("_") and not name.startswith("__"):
            runtime_flags = self.__dict__.setdefault("runtime_flags", {})
            runtime_flags[name] = value
            return
        super().__setattr__(name, value)

    def __delattr__(self, name: str):
        if name.startswith("_") and not name.startswith("__"):
            runtime_flags = self.__dict__.get("runtime_flags", {})
            runtime_flags.pop(name, None)
            return
        super().__delattr__(name)

    def get_runtime_flag(self, name: str, default=None):
        return self.runtime_flags.get(name, default)

    def set_runtime_flag(self, name: str, value) -> None:
        self.runtime_flags[name] = value

    def pop_runtime_flag(self, name: str, default=None):
        return self.runtime_flags.pop(name, default)

    def copy(self) -> 'PetInstance':
        """深拷贝精灵实例"""
        return PetInstance(
            template=self.template,
            current_hp=self.current_hp,
            max_hp=self.max_hp,
            stats=self.stats.copy(),
            skills=copy.deepcopy(self.skills),
            current_energy=self.current_energy,
            stat_modifiers=self.stat_modifiers.copy(),
            skill_cooldowns=self.skill_cooldowns.copy(),
            is_alive=self.is_alive,
            status_effects={k: v for k, v in self.status_effects.items()},
            freeze_stacks=self.freeze_stacks,
            stun_turns=self.stun_turns,
            skill_transmission=self.skill_transmission.copy(),
            charging_skill=self.charging_skill,
            burst_turns_remaining=self.burst_turns_remaining,
            just_entered=self.just_entered,
            pending_switch_out=self.pending_switch_out,
            priority_bonus=self.priority_bonus,
            runtime_flags=copy.deepcopy(self.runtime_flags),
        )

    def get_effective_stat(self, stat_name: str) -> int:
        """获取考虑buff/debuff后的实际属性"""
        base = self.stats[stat_name]
        modifier = 0

        if stat_name == "物攻":
            modifier = self.stat_modifiers.physical_attack
        elif stat_name == "魔攻":
            modifier = self.stat_modifiers.magical_attack
        elif stat_name == "物防":
            modifier = self.stat_modifiers.physical_defense
        elif stat_name == "魔防":
            modifier = self.stat_modifiers.magical_defense
        elif stat_name == "速度":
            modifier = self.stat_modifiers.speed

        # 每层buff/debuff = 10%
        multiplier = 1.0 + (modifier * 0.1)
        return max(1, int(base * multiplier))

    # ── 状态效果快捷方法 ──────────────────────────────────────────

    def add_status(self, status_type, stacks: int = 1):
        """添加状态效果"""
        self.status_effects[status_type] = self.status_effects.get(status_type, 0) + stacks

    def remove_status(self, status_type):
        """移除状态效果"""
        self.status_effects.pop(status_type, None)

    def get_status_stacks(self, status_type) -> int:
        """获取状态层数"""
        return self.status_effects.get(status_type, 0)

    def has_status(self, status_type) -> bool:
        return self.get_status_stacks(status_type) > 0

    def clear_on_switch_out(self, keep_buffs: bool = False):
        """
        离场时清除状态（冻结保留，印记不在此清除）
        keep_buffs=True 时保留 buff/debuff（翠顶/黑羽夫人特性）
        """
        from core.status_effects import StatusEffectType
        to_remove = [
            st for st in self.status_effects
            if st != StatusEffectType.FREEZE
        ]
        for st in to_remove:
            del self.status_effects[st]

        if not keep_buffs:
            self.stat_modifiers = StatModifier()

        self.burst_turns_remaining = 0
        self.just_entered = False
        self.charging_skill = None
        self.pending_switch_out = False


@dataclass
class FieldMark:
    """场地印记"""
    from_core = False  # 避免循环

    type_key: str   # StatusEffectType.value
    stacks: int
    is_positive: bool

    def copy(self) -> 'FieldMark':
        return FieldMark(
            type_key=self.type_key,
            stacks=self.stacks,
            is_positive=self.is_positive
        )


@dataclass
class TeamState:
    """队伍状态（全队共享效果）"""
    devotion_poison: int = 0      # 奉献：附加中毒层数（最多10）
    devotion_lifesteal: int = 0   # 奉献：吸血百分比（最多100%）
    devotion_combo: int = 0       # 奉献：连击次数加成（最多10）
    devotion_power: int = 0       # 奉献：威力加成（最多200）
    devotion_energy: int = 0      # 奉献：能耗减少（最多20）
    leader_evolution_uses: int = 1   # 首领化剩余次数
    willpower_strike_uses: int = 2   # 愿力冲击剩余次数

    # ── 入场积累型特性计数 ────────────────────────────────────────
    # 在场时己方使用特定系别技能的累计次数，入场时被消费
    earth_skill_count: int = 0       # 地脉/地脉馈赠：地系技能使用次数
    ice_skill_count: int = 0         # 打雪仗：冰系技能使用次数
    fire_skill_count: int = 0        # 散热/蒸汽膨胀：火系技能使用次数
    water_skill_count: int = 0       # 水翼推进/水翼飞升：水系技能使用次数
    status_skill_count: int = 0      # 拨浪鼓：状态技能使用次数
    counter_success_count: int = 0   # 慢热型/身经百练：应对成功次数
    defense_skill_count: int = 0     # 定向精炼：防御技能使用次数
    gather_energy_count: int = 0     # 搜刮：聚能次数
    switch_count: int = 0            # 搜刮：换宠次数
    switched_this_turn: bool = False  # 本回合是否换宠（埋伏/灵光/回旋踢/针刺射击）

    # ── 离场礼物标记（由离场特性设置，由下只入场精灵消费）────────
    # 格式：set of str，如 {'免疫冻结', '双防+2', '回复20%生命', '免疫寄生', '免疫灼烧'}
    next_pet_gifts: set = None       # 下只精灵获得的礼物集合
    suppress_next_pet_swift: bool = False  # 下只入场精灵不触发迅捷

    def __post_init__(self):
        if self.next_pet_gifts is None:
            self.next_pet_gifts = set()

    def copy(self) -> 'TeamState':
        return TeamState(
            devotion_poison=self.devotion_poison,
            devotion_lifesteal=self.devotion_lifesteal,
            devotion_combo=self.devotion_combo,
            devotion_power=self.devotion_power,
            devotion_energy=self.devotion_energy,
            leader_evolution_uses=self.leader_evolution_uses,
            willpower_strike_uses=self.willpower_strike_uses,
            earth_skill_count=self.earth_skill_count,
            ice_skill_count=self.ice_skill_count,
            fire_skill_count=self.fire_skill_count,
            water_skill_count=self.water_skill_count,
            status_skill_count=self.status_skill_count,
            counter_success_count=self.counter_success_count,
            defense_skill_count=self.defense_skill_count,
            gather_energy_count=self.gather_energy_count,
            switch_count=self.switch_count,
            switched_this_turn=self.switched_this_turn,
            next_pet_gifts=set(self.next_pet_gifts),
            suppress_next_pet_swift=self.suppress_next_pet_swift,
        )


@dataclass
class PlayerState:
    """玩家状态"""
    team: List[PetInstance]  # 队伍（最多6只）
    active_index: int        # 当前出战精灵索引
    team_state: TeamState = field(default_factory=TeamState)

    def get_active_pet(self) -> Optional[PetInstance]:
        if 0 <= self.active_index < len(self.team):
            return self.team[self.active_index]
        return None

    def get_alive_pets(self) -> List[Tuple[int, PetInstance]]:
        return [(i, pet) for i, pet in enumerate(self.team) if pet.is_alive]

    def copy(self) -> 'PlayerState':
        return PlayerState(
            team=[pet.copy() for pet in self.team],
            active_index=self.active_index,
            team_state=self.team_state.copy(),
        )


@dataclass
class BattleState:
    """对战状态"""
    player: PlayerState
    opponent: PlayerState
    turn: int = 1
    weather: Optional[str] = None
    field_effects: Dict[str, int] = field(default_factory=dict)

    # 扩展战斗状态（原 ExtendedBattleState，直接内嵌）
    player_positive_mark: Optional[FieldMark] = None
    player_negative_mark: Optional[FieldMark] = None
    opponent_positive_mark: Optional[FieldMark] = None
    opponent_negative_mark: Optional[FieldMark] = None
    player_hearts: int = 4
    opponent_hearts: int = 4
    max_turns: int = 50
    turn_prepared: bool = False

    def copy(self) -> 'BattleState':
        return BattleState(
            player=self.player.copy(),
            opponent=self.opponent.copy(),
            turn=self.turn,
            weather=self.weather,
            field_effects=self.field_effects.copy(),
            player_positive_mark=self.player_positive_mark.copy() if self.player_positive_mark else None,
            player_negative_mark=self.player_negative_mark.copy() if self.player_negative_mark else None,
            opponent_positive_mark=self.opponent_positive_mark.copy() if self.opponent_positive_mark else None,
            opponent_negative_mark=self.opponent_negative_mark.copy() if self.opponent_negative_mark else None,
            player_hearts=self.player_hearts,
            opponent_hearts=self.opponent_hearts,
            max_turns=self.max_turns,
            turn_prepared=self.turn_prepared,
        )

    def is_terminal(self) -> bool:
        player_alive = any(pet.is_alive for pet in self.player.team)
        opponent_alive = any(pet.is_alive for pet in self.opponent.team)
        return not player_alive or not opponent_alive

    def get_winner(self) -> Optional[str]:
        if not self.is_terminal():
            return None
        player_alive = any(pet.is_alive for pet in self.player.team)
        opponent_alive = any(pet.is_alive for pet in self.opponent.team)
        if player_alive and not opponent_alive:
            return "player"
        elif opponent_alive and not player_alive:
            return "opponent"
        return "draw"

    def is_battle_over_by_hearts(self) -> bool:
        return self.player_hearts <= 0 or self.opponent_hearts <= 0

    def get_winner_by_hearts(self) -> Optional[str]:
        if self.player_hearts <= 0 and self.opponent_hearts <= 0:
            return "draw"
        elif self.player_hearts <= 0:
            return "opponent"
        elif self.opponent_hearts <= 0:
            return "player"
        return None

    def set_mark(self, is_player: bool, mark: 'FieldMark'):
        """设置印记（同类型只保留最新的）"""
        if is_player:
            if mark.is_positive:
                self.player_positive_mark = mark
            else:
                self.player_negative_mark = mark
        else:
            if mark.is_positive:
                self.opponent_positive_mark = mark
            else:
                self.opponent_negative_mark = mark

    def get_marks(self, is_player: bool):
        """返回 (正面印记, 负面印记)"""
        if is_player:
            return self.player_positive_mark, self.player_negative_mark
        return self.opponent_positive_mark, self.opponent_negative_mark


class ActionType(Enum):
    """行动类型"""
    USE_SKILL = "use_skill"
    SWITCH_PET = "switch_pet"
    GATHER_ENERGY = "gather_energy"      # 聚能
    LEADER_EVOLUTION = "leader_evolution"  # 首领化
    WILLPOWER_STRIKE = "willpower_strike"  # 愿力冲击


@dataclass
class Action:
    """行动"""
    type: ActionType
    skill: Optional[Skill] = None
    target_index: Optional[int] = None
    send_out_index: Optional[int] = None

    def __str__(self):
        prefix = f"补位{self.send_out_index} -> " if self.send_out_index is not None else ""
        if self.type == ActionType.USE_SKILL:
            return f"{prefix}使用技能: {self.skill.name}"
        elif self.type == ActionType.SWITCH_PET:
            return f"换精灵: 索引{self.target_index}"
        elif self.type == ActionType.LEADER_EVOLUTION:
            return f"{prefix}首领化"
        elif self.type == ActionType.WILLPOWER_STRIKE:
            return f"{prefix}愿力冲击"
        return f"{prefix}聚能"

    def __hash__(self):
        if self.type == ActionType.USE_SKILL:
            return hash((self.type, self.skill.name if self.skill else None, self.send_out_index))
        elif self.type == ActionType.SWITCH_PET:
            return hash((self.type, self.target_index))
        return hash((self.type, self.send_out_index))

    def __eq__(self, other):
        if not isinstance(other, Action):
            return False
        if self.type != other.type:
            return False
        if self.type == ActionType.USE_SKILL:
            return self.skill == other.skill and self.send_out_index == other.send_out_index
        elif self.type == ActionType.SWITCH_PET:
            return self.target_index == other.target_index
        elif self.type == ActionType.WILLPOWER_STRIKE:
            return self.skill == other.skill and self.send_out_index == other.send_out_index
        return self.send_out_index == other.send_out_index
