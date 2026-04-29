"""
特性系统
处理精灵特性的触发和效果
状态现在存储在 PetInstance / BattleState 上
"""
from enum import Enum
import random
from typing import Optional, List
from core.models import PetInstance, BattleState, PlayerState
from core.status_effects import StatusEffectType
from engine.slot_effects import SlotEffectsProcessor


def _normalize_bloodline(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    text = str(value).strip()
    lowered = text.lower()
    if lowered == "unknown":
        return "unknown"
    if lowered in {"leader", "leader_bloodline"} or "首领" in text:
        return "leader"
    if lowered in {"polluted", "corrupted"} or "污染" in text:
        return "polluted"
    if lowered.startswith("element:"):
        return lowered
    return f"element:{text}"


def _has_bloodline(pet: Optional[PetInstance], bloodline: str) -> bool:
    if pet is None:
        return False
    return _normalize_bloodline(getattr(pet.template, "bloodline", "unknown")) == bloodline


def _has_foreign_element_bloodline(attacker: PetInstance, defender: Optional[PetInstance]) -> bool:
    if defender is None:
        return False
    defender_bloodline = _normalize_bloodline(getattr(defender.template, "bloodline", "unknown"))
    if not defender_bloodline.startswith("element:"):
        return False
    defender_element = defender_bloodline.split(":", 1)[1]
    return defender_element not in set(attacker.template.types or [])


class TraitTrigger(Enum):
    ON_ENTER = "on_enter"
    ON_ATTACK = "on_attack"
    ON_DAMAGED = "on_damaged"
    ON_DEATH = "on_death"
    ON_KILL = "on_kill"
    ON_SWITCH_OUT = "on_switch_out"
    ON_SKILL_USE = "on_skill_use"       # 使用技能后（攻击/状态均可）
    END_OF_TURN = "end_of_turn"         # 回合结束
    PASSIVE = "passive"


# 特性名 -> 触发时机
TRAIT_TRIGGERS = {
    # ── 入场 ──────────────────────────────────────────────────────
    "威吓": TraitTrigger.ON_ENTER,
    "降压": TraitTrigger.ON_ENTER,
    "恶臭": TraitTrigger.ON_ENTER,
    "压迫": TraitTrigger.ON_ENTER,
    "强运": TraitTrigger.ON_ENTER,
    "竭泽而渔": TraitTrigger.ON_ENTER,
    "土地神": TraitTrigger.ON_ENTER,
    "闪电侠": TraitTrigger.ON_ENTER,
    "反弹": TraitTrigger.ON_ENTER,
    "免疫": TraitTrigger.ON_ENTER,
    "专注力": TraitTrigger.ON_ENTER,
    "全神贯注": TraitTrigger.ON_ENTER,
    "渴求": TraitTrigger.ON_ENTER,
    "小偷小摸": TraitTrigger.ON_ENTER,
    "图书守卫者": TraitTrigger.ON_ENTER,
    "构装契约者": TraitTrigger.ON_ENTER,
    "铃兰晚钟": TraitTrigger.ON_ENTER,
    "蓄电池": TraitTrigger.ON_ENTER,
    "超级电池": TraitTrigger.ON_ENTER,
    "虫群突袭": TraitTrigger.ON_ENTER,
    "虫群鼓舞": TraitTrigger.ON_ENTER,
    "壮胆": TraitTrigger.ON_ENTER,
    "悲悯": TraitTrigger.ON_ENTER,
    "悼亡": TraitTrigger.ON_ENTER,
    "抓到你了": TraitTrigger.ON_ENTER,
    "衡量": TraitTrigger.ON_ENTER,
    # 入场积累型
    "地脉": TraitTrigger.ON_ENTER,
    "地脉馈赠": TraitTrigger.ON_ENTER,
    "打雪仗": TraitTrigger.ON_ENTER,
    "散热": TraitTrigger.ON_ENTER,
    "慢热型": TraitTrigger.ON_ENTER,
    "水翼推进": TraitTrigger.ON_ENTER,
    "水翼飞升": TraitTrigger.ON_ENTER,
    "蒸汽膨胀": TraitTrigger.ON_ENTER,
    "拨浪鼓": TraitTrigger.ON_ENTER,
    "搜刮": TraitTrigger.ON_ENTER,
    "身经百练": TraitTrigger.ON_ENTER,
    "定向精炼": TraitTrigger.ON_ENTER,
    "守护者": TraitTrigger.ON_ENTER,
    # 其他入场
    "得寸进尺": TraitTrigger.ON_ENTER,
    "御驾亲征": TraitTrigger.ON_ENTER,
    "保守派": TraitTrigger.ON_ENTER,
    "冻土": TraitTrigger.ON_ENTER,
    "消波块": TraitTrigger.ON_ENTER,
    "溶解腐蚀": TraitTrigger.ON_ENTER,
    "夺目": TraitTrigger.ON_ENTER,

    # ── 攻击时 ────────────────────────────────────────────────────
    "猛毒": TraitTrigger.ON_ATTACK,
    "灼热": TraitTrigger.ON_ATTACK,
    "冰封": TraitTrigger.ON_ATTACK,
    "寄生虫": TraitTrigger.ON_ATTACK,
    "吸血鬼": TraitTrigger.ON_ATTACK,
    "连击": TraitTrigger.ON_ATTACK,
    "灵魂灼伤": TraitTrigger.ON_ATTACK,
    "高浓生物碱": TraitTrigger.ON_ATTACK,
    "毒腺": TraitTrigger.ON_ATTACK,
    "灰色肖像": TraitTrigger.ON_ATTACK,
    "加个雪球": TraitTrigger.ON_ATTACK,
    "毒牙": TraitTrigger.ON_ATTACK,
    "月牙雪糕": TraitTrigger.ON_ATTACK,
    "最好的伙伴": TraitTrigger.ON_ATTACK,

    # ── 使用技能后 ────────────────────────────────────────────────
    "助燃": TraitTrigger.ON_SKILL_USE,
    "爆燃": TraitTrigger.ON_SKILL_USE,
    "氧循环": TraitTrigger.ON_SKILL_USE,
    "深层氧循环": TraitTrigger.ON_SKILL_USE,
    "浸润": TraitTrigger.ON_SKILL_USE,
    "浪潮": TraitTrigger.ON_SKILL_USE,
    "扩散侵蚀": TraitTrigger.ON_SKILL_USE,
    "碰瓷": TraitTrigger.ON_SKILL_USE,
    "三鼓作气": TraitTrigger.ON_SKILL_USE,
    "鼓气": TraitTrigger.ON_SKILL_USE,
    "洄游": TraitTrigger.ON_SKILL_USE,
    "奔波命": TraitTrigger.ON_SKILL_USE,

    # ── 受击时 ────────────────────────────────────────────────────
    "反击": TraitTrigger.ON_DAMAGED,
    "荆棘": TraitTrigger.ON_DAMAGED,
    "愤怒": TraitTrigger.ON_DAMAGED,
    "坚韧": TraitTrigger.ON_DAMAGED,
    "再生": TraitTrigger.ON_DAMAGED,
    "化茧": TraitTrigger.ON_DAMAGED,
    "嫁祸": TraitTrigger.ON_DAMAGED,
    "石头大餐": TraitTrigger.ON_DAMAGED,

    # ── 死亡时 ────────────────────────────────────────────────────
    "同归于尽": TraitTrigger.ON_DEATH,
    "遗愿": TraitTrigger.ON_DEATH,
    "爆裂": TraitTrigger.ON_DEATH,
    "涅槃": TraitTrigger.ON_DEATH,
    "虚假宝箱": TraitTrigger.ON_DEATH,
    "付给恶魔的赎价": TraitTrigger.ON_DEATH,
    "御驾亲征_death": TraitTrigger.ON_DEATH,
    "不朽": TraitTrigger.ON_DEATH,

    # ── 击杀时 ────────────────────────────────────────────────────
    "收割": TraitTrigger.ON_KILL,
    "猎人": TraitTrigger.ON_KILL,
    "贪婪": TraitTrigger.ON_KILL,

    # ── 离场时 ────────────────────────────────────────────────────
    "告别": TraitTrigger.ON_SWITCH_OUT,
    "快充": TraitTrigger.ON_SWITCH_OUT,
    "防过载保护": TraitTrigger.ON_SWITCH_OUT,
    "吉利丁片": TraitTrigger.ON_SWITCH_OUT,
    "茶多酚": TraitTrigger.ON_SWITCH_OUT,
    "美拉德反应": TraitTrigger.ON_SWITCH_OUT,
    "洁癖": TraitTrigger.ON_SWITCH_OUT,
    "下黑手": TraitTrigger.ON_SWITCH_OUT,
    "木桶戏法": TraitTrigger.ON_SWITCH_OUT,

    # ── 回合结束 ──────────────────────────────────────────────────
    "养分内循环": TraitTrigger.END_OF_TURN,
    "养分重吸收": TraitTrigger.END_OF_TURN,
    "生长": TraitTrigger.END_OF_TURN,
    "吸积盘": TraitTrigger.END_OF_TURN,
    "毒蘑菇": TraitTrigger.END_OF_TURN,
    "大捞一笔": TraitTrigger.END_OF_TURN,
    "蚀刻": TraitTrigger.END_OF_TURN,
    "复方汤剂": TraitTrigger.END_OF_TURN,
    "特殊清洁场景": TraitTrigger.END_OF_TURN,
    "石天平": TraitTrigger.END_OF_TURN,
    "扫拖一体": TraitTrigger.END_OF_TURN,
    "花精灵": TraitTrigger.END_OF_TURN,
    "坚韧铠甲": TraitTrigger.ON_DAMAGED,
    "振奋虫心": TraitTrigger.ON_KILL,
    "飓风": TraitTrigger.ON_ENTER,

    # ── 应对成功后 ────────────────────────────────────────────────
    "圣火骑士": TraitTrigger.ON_ENTER,    # 注册为被动，实际在 trigger_on_counter_success 处理
    "野性感官": TraitTrigger.ON_ENTER,
    "指挥家": TraitTrigger.ON_ENTER,
    "思维之盾": TraitTrigger.ON_ENTER,
    "斗技": TraitTrigger.ON_ENTER,

    # ── 被动（modify_skill_power/modify_damage_taken 中处理）──────
    "翠顶夫人": TraitTrigger.PASSIVE,
    "黑羽夫人": TraitTrigger.PASSIVE,
    "钢铁意志": TraitTrigger.PASSIVE,
    "坚守": TraitTrigger.PASSIVE,
    # 以下被动在 modify_skill_power 中实现，注册为 PASSIVE 供查询
    "\"国王\"的威严": TraitTrigger.PASSIVE,   # 带引号版本
    '"国王"的威严': TraitTrigger.PASSIVE,      # 实际数据中的版本
    "\u201c国王\u201d的威严": TraitTrigger.PASSIVE,  # Unicode弯引号版本
    "不移": TraitTrigger.PASSIVE,
    "勇敢": TraitTrigger.PASSIVE,
    "目空": TraitTrigger.PASSIVE,
    "涂鸦": TraitTrigger.PASSIVE,
    "冰钻": TraitTrigger.PASSIVE,
    "变形活画": TraitTrigger.PASSIVE,
    "坠星": TraitTrigger.PASSIVE,
    "观星": TraitTrigger.PASSIVE,
    "血型吸引": TraitTrigger.PASSIVE,
    "破空": TraitTrigger.PASSIVE,
    "自由飘": TraitTrigger.PASSIVE,
    "侵蚀": TraitTrigger.PASSIVE,
    "守望星": TraitTrigger.PASSIVE,
    "无差别过滤": TraitTrigger.PASSIVE,
    "无忧无虑": TraitTrigger.PASSIVE,
    # 血脉条件被动（已在 modify_skill_power 中实现）
    "天通地明": TraitTrigger.PASSIVE,
    "月光审判": TraitTrigger.PASSIVE,
    "绒粉星光": TraitTrigger.PASSIVE,
    # 张弛有度：周末双攻+40%，其他时间双防+40%（依赖现实星期，注册为入场触发）
    "张弛有度": TraitTrigger.ON_ENTER,
    # 贪心算法：1号位传动忽略，灼烧子效果在 ON_SKILL_USE 中实现
    "贪心算法": TraitTrigger.ON_SKILL_USE,
    # 受伤减免被动
    "偏振": TraitTrigger.PASSIVE,
    "完全偏振": TraitTrigger.PASSIVE,
    "绝对秩序": TraitTrigger.PASSIVE,
    "惊吓": TraitTrigger.PASSIVE,
    "逐魂鸟": TraitTrigger.PASSIVE,

    # ── 入场时修改技能属性 ────────────────────────────────────────
    "快锤": TraitTrigger.ON_ENTER,
    "暴食": TraitTrigger.ON_ENTER,
    "生物电": TraitTrigger.ON_ENTER,
    "超负荷": TraitTrigger.ON_ENTER,
    "连续负荷": TraitTrigger.ON_ENTER,
    "起飞加速": TraitTrigger.ON_ENTER,
    "噼啪！": TraitTrigger.ON_ENTER,
    "囤积": TraitTrigger.ON_ENTER,
    "先知": TraitTrigger.ON_ENTER,
    "预警": TraitTrigger.ON_ENTER,
    "游弋": TraitTrigger.ON_ENTER,
    "嫉妒": TraitTrigger.ON_ENTER,
    "多人宿舍": TraitTrigger.ON_ENTER,

    # ── 回合结束 ──────────────────────────────────────────────────
    "星地善良": TraitTrigger.END_OF_TURN,
    "仁心": TraitTrigger.END_OF_TURN,
    "腐植循环": TraitTrigger.END_OF_TURN,
    "双向光速": TraitTrigger.END_OF_TURN,
    "陨落": TraitTrigger.END_OF_TURN,
    "煤渣草": TraitTrigger.END_OF_TURN,

    # ── 攻击时 ────────────────────────────────────────────────────
    "咔咔冲刺": TraitTrigger.ON_ATTACK,
    "捉迷藏": TraitTrigger.ON_ATTACK,

    # ── 受击时 ────────────────────────────────────────────────────
    "石头大餐": TraitTrigger.ON_DAMAGED,

    # ── 使用技能后 ────────────────────────────────────────────────
    "营养液泡": TraitTrigger.ON_SKILL_USE,
    "泛音列": TraitTrigger.ON_SKILL_USE,
    "哨兵": TraitTrigger.ON_SKILL_USE,
    "系统发育": TraitTrigger.ON_SKILL_USE,
    "倾轧": TraitTrigger.ON_SKILL_USE,
    "威慑": TraitTrigger.ON_SKILL_USE,

    # ── 回合结束（额外）─────────────────────────────────────────
    "对流": TraitTrigger.END_OF_TURN,
    "吟游之弦": TraitTrigger.PASSIVE,     # 印记不替换，被动逻辑
}

# 有此特性的精灵离场时保留 buff
KEEP_BUFF_TRAITS = {"翠顶夫人", "黑羽夫人"}


class TraitProcessor:
    """特性处理器"""

    @staticmethod
    def _grant_devotion(team_state, count: int, seed_key: str):
        """给队伍添加若干次确定性随机奉献。"""
        for idx in range(max(0, count)):
            rng = random.Random(f"{seed_key}:{idx}")
            roll = rng.randrange(5)
            if roll == 0:
                team_state.devotion_poison = min(10, team_state.devotion_poison + 2)
            elif roll == 1:
                team_state.devotion_lifesteal = min(100, team_state.devotion_lifesteal + 10)
            elif roll == 2:
                team_state.devotion_combo = min(10, team_state.devotion_combo + 1)
            elif roll == 3:
                team_state.devotion_power = min(200, team_state.devotion_power + 20)
            else:
                team_state.devotion_energy = min(20, team_state.devotion_energy + 2)

    @staticmethod
    def grant_random_devotion(team_state, count: int, seed_key: str):
        TraitProcessor._grant_devotion(team_state, count, seed_key)

    @staticmethod
    def grant_specific_devotion(team_state, kind: str, count: int = 1):
        for _ in range(max(0, count)):
            if kind == 'poison':
                team_state.devotion_poison = min(10, team_state.devotion_poison + 2)
            elif kind == 'lifesteal':
                team_state.devotion_lifesteal = min(100, team_state.devotion_lifesteal + 10)
            elif kind == 'combo':
                team_state.devotion_combo = min(10, team_state.devotion_combo + 1)
            elif kind == 'power':
                team_state.devotion_power = min(200, team_state.devotion_power + 20)
            elif kind == 'energy':
                team_state.devotion_energy = min(20, team_state.devotion_energy + 2)

    def get_trigger_type(self, trait_name: str) -> Optional[TraitTrigger]:
        return TRAIT_TRIGGERS.get(trait_name)

    def has_keep_buff_trait(self, pet: PetInstance) -> bool:
        return any(t.name in KEEP_BUFF_TRAITS for t in pet.template.traits)

    # ── 触发入口 ─────────────────────────────────────────────────

    def trigger_on_enter(
        self, pet: PetInstance, opponent: Optional[PetInstance],
        is_player: bool, state: BattleState
    ):
        for trait in pet.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_ENTER:
                self._apply(trait.name, pet, opponent, is_player, state, "enter")

    def trigger_on_attack(
        self, attacker: PetInstance, defender: PetInstance,
        damage: int, is_player: bool, state: BattleState
    ):
        for trait in attacker.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_ATTACK:
                self._apply(trait.name, attacker, defender, is_player, state, "attack", damage)

    def trigger_on_damaged(
        self, defender: PetInstance, attacker: PetInstance,
        damage: int, is_player: bool, state: BattleState
    ):
        for trait in defender.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_DAMAGED:
                self._apply(trait.name, defender, attacker, is_player, state, "damaged", damage)

    def trigger_on_skill_use(
        self, pet: PetInstance, opponent: Optional[PetInstance],
        skill, is_player: bool, state: BattleState
    ):
        """使用技能后触发（攻击/状态均可）"""
        for trait in pet.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_SKILL_USE:
                self._apply(trait.name, pet, opponent, is_player, state, "skill_use", 0, skill)

    def trigger_on_death(
        self, pet: PetInstance, killer: Optional[PetInstance],
        is_player: bool, state: BattleState
    ):
        for trait in pet.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_DEATH:
                self._apply(trait.name, pet, killer, is_player, state, "death")

    def trigger_on_kill(
        self, killer: PetInstance, victim: PetInstance,
        is_player: bool, state: BattleState
    ):
        for trait in killer.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_KILL:
                self._apply(trait.name, killer, victim, is_player, state, "kill")
        # 付给恶魔的赎价：击杀时额外扣对方魔力
        for trait in killer.template.traits:
            if trait.name == "付给恶魔的赎价":
                opponent_state = state.opponent if is_player else state.player
                opponent_state.team_state.leader_evolution_uses = max(
                    0, opponent_state.team_state.leader_evolution_uses - 1
                )

    def trigger_on_switch_out(
        self, pet: PetInstance, opponent: Optional[PetInstance],
        is_player: bool, state: BattleState
    ):
        for trait in pet.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.ON_SWITCH_OUT:
                self._apply(trait.name, pet, opponent, is_player, state, "switch_out")

    def trigger_end_of_turn(
        self, pet: PetInstance, opponent: Optional[PetInstance],
        is_player: bool, state: BattleState
    ):
        """回合结束时触发"""
        for trait in pet.template.traits:
            if self.get_trigger_type(trait.name) == TraitTrigger.END_OF_TURN:
                self._apply(trait.name, pet, opponent, is_player, state, "end_of_turn")

    def trigger_on_counter_success(
        self, pet: PetInstance, opponent: Optional[PetInstance],
        is_player: bool, state: BattleState
    ):
        """应对成功后触发"""
        COUNTER_TRAITS = {"圣火骑士", "野性感官", "指挥家", "思维之盾", "斗技"}
        for trait in pet.template.traits:
            if trait.name in COUNTER_TRAITS:
                self._apply(trait.name, pet, opponent, is_player, state, "counter_success")

    def apply_next_pet_gifts(
        self, pet: PetInstance, is_player: bool, state: BattleState
    ):
        """消费上一只精灵离场时留下的礼物"""
        ts = (state.player if is_player else state.opponent).team_state
        if not ts.next_pet_gifts:
            return
        gifts = set(ts.next_pet_gifts)
        ts.next_pet_gifts.clear()

        for gift in gifts:
            if gift == '双防+2':
                pet.stat_modifiers.physical_defense += 2
                pet.stat_modifiers.magical_defense += 2
            elif gift == '双攻+2':
                pet.stat_modifiers.physical_attack += 2
                pet.stat_modifiers.magical_attack += 2
            elif gift == '双防+5':
                pet.stat_modifiers.physical_defense += 5
                pet.stat_modifiers.magical_defense += 5
            elif gift == '速度-5':
                pet.stat_modifiers.speed -= 5
            elif gift == '回复20%生命':
                pet.current_hp = min(pet.max_hp, pet.current_hp + int(pet.max_hp * 0.2))
            elif gift == '免疫冻结':
                pet._immune_freeze = True
            elif gift == '免疫寄生':
                pet._immune_parasite = True
            elif gift == '免疫灼烧':
                pet._immune_burn = True
            elif gift == '中毒5层':
                pet.add_status(StatusEffectType.POISON, 5)
            elif gift == '回复8能量':
                pet.current_energy = min(10, pet.current_energy + 8)
            elif gift.startswith('物攻+'):
                pet.stat_modifiers.physical_attack += int(gift[3:])
            elif gift.startswith('魔攻+'):
                pet.stat_modifiers.magical_attack += int(gift[3:])
            elif gift.startswith('物防+'):
                pet.stat_modifiers.physical_defense += int(gift[3:])
            elif gift.startswith('魔防+'):
                pet.stat_modifiers.magical_defense += int(gift[3:])
            elif gift.startswith('速度+'):
                pet.stat_modifiers.speed += int(gift[3:])

    # ── 被动修正（伤害计算时调用）───────────────────────────────

    def modify_damage_taken(
        self, defender: PetInstance, attacker: Optional[PetInstance],
        damage: int, skill=None
    ) -> int:
        """
        被动特性对受伤的修正：
        - 偏振：受到自己携带技能系别的攻击伤害-40%
        - 完全偏振：抵抗自己携带技能系别的攻击伤害（变为0）
        - 绝对秩序：受到非敌方系别的技能攻击时伤害-50%
        - 惊吓：能量为0的攻击者无法造成伤害
        - 化茧：受到致命伤害时免疫并获得萌化（在 ON_DAMAGED 中处理）
        """
        if damage <= 0:
            return damage

        # 惊吓：能量为0的精灵无法对自己造成伤害
        for trait in defender.template.traits:
            if trait.name == "惊吓" and attacker and attacker.current_energy == 0:
                return 0

        if skill is None:
            return damage

        skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
        if skill_type is None:
            return damage

        # 完全偏振：抵抗携带技能系别的攻击
        for trait in defender.template.traits:
            if trait.name == "完全偏振":
                own_types = {getattr(sk, 'element', None) or getattr(sk, 'type', None)
                             for sk in defender.skills}
                if skill_type in own_types:
                    return 0

        # 偏振：受到自己携带技能系别的攻击伤害-40%
        for trait in defender.template.traits:
            if trait.name == "偏振":
                own_types = {getattr(sk, 'element', None) or getattr(sk, 'type', None)
                             for sk in defender.skills}
                if skill_type in own_types:
                    return int(damage * 0.6)

        # 绝对秩序：受到非敌方系别的技能攻击时伤害-50%
        for trait in defender.template.traits:
            if trait.name == "绝对秩序" and attacker:
                attacker_types = set(attacker.template.types) if hasattr(attacker.template, 'types') else set()
                if skill_type not in attacker_types:
                    return int(damage * 0.5)

        # 逐魂鸟：能耗<=1的攻击技能无法对自己造成伤害
        for trait in defender.template.traits:
            if trait.name == "逐魂鸟" and skill:
                skill_cost = getattr(skill, 'effective_energy_cost', getattr(skill, 'energy_cost', 99))
                if skill_cost <= 1:
                    return 0

        return damage

    def modify_skill_power(
        self, attacker: PetInstance, defender: Optional[PetInstance],
        skill, base_power: int, is_player: bool = True, state: 'BattleState' = None
    ) -> int:
        """
        被动特性对技能威力的修正（攻击计算前调用）
        """
        power = base_power
        if power <= 0:
            return power

        skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
        skill_cost = getattr(skill, 'effective_energy_cost', getattr(skill, 'energy_cost', 0))

        for trait in attacker.template.traits:
            name = trait.name

            # 勇敢：能耗大于3的技能威力+40%
            if name == "勇敢" and skill_cost > 3:
                power = int(power * 1.4)

            # 目空：携带的非光系技能威力+25%
            elif name == "目空" and skill_type != "光":
                power = int(power * 1.25)

            # 涂鸦：使用非本系技能时威力+50%
            elif name == "涂鸦":
                own_types = set(attacker.template.types) if hasattr(attacker.template, 'types') else set()
                if skill_type and skill_type not in own_types:
                    power = int(power * 1.5)

            # "国王"的威严（弯引号）：能耗为1的技能威力+50%
            elif name in ('"国王"的威严', '\u201c国王\u201d的威严', '"国王"的威严') and skill_cost == 1:
                power = int(power * 1.5)

            # 变形活画：攻击时敌方每有1层增益，威力+10%
            elif name == "变形活画" and defender:
                buff_stacks = 0
                m = defender.stat_modifiers
                for v in [m.physical_attack, m.magical_attack, m.physical_defense,
                          m.magical_defense, m.speed]:
                    if v > 0:
                        buff_stacks += v
                power = int(power * (1 + buff_stacks * 0.1))

            # 冰钻：敌方携带技能总能耗每有1点，攻击时威力+10%
            elif name == "冰钻" and defender:
                total_cost = sum(getattr(sk, 'energy_cost', 0) for sk in defender.skills)
                power = int(power * (1 + total_cost * 0.1))

            # 坠星：敌方每有1层星陨印记，技能威力+15%
            elif name == "坠星" and defender and state:
                opp_is_player = not is_player
                _, opp_neg = state.get_marks(opp_is_player)
                opp_pos, _ = state.get_marks(opp_is_player)
                # 星陨印记是负面的，存在 negative mark 中
                star_stacks = 0
                if opp_neg and opp_neg.type_key == StatusEffectType.STAR_FALL_MARK.value:
                    star_stacks = opp_neg.stacks
                # 也检查 status_effects
                star_stacks += defender.get_status_stacks(StatusEffectType.STAR_FALL_MARK)
                if star_stacks > 0:
                    power = int(power * (1 + star_stacks * 0.15))

            # 观星：敌方每有1层星陨印记，地系技能威力+15%
            elif name == "观星" and defender and skill_type == '地' and state:
                opp_is_player = not is_player
                star_stacks = defender.get_status_stacks(StatusEffectType.STAR_FALL_MARK)
                if star_stacks > 0:
                    power = int(power * (1 + star_stacks * 0.15))

            # 血型吸引：敌方每携带1种系别，威力+10
            elif name == "血型吸引" and defender:
                types = {getattr(sk, 'element', None) or getattr(sk, 'type', None)
                         for sk in defender.skills if sk}
                types.discard(None)
                power += len(types) * 10

            # 破空：若先于敌方攻击（通过 _is_first_attacker 标记），威力+75%
            elif name == "破空":
                if attacker.get_runtime_flag('_is_first_attacker', False):
                    power = int(power * 1.75)

            # 圣火骑士：下次攻击威力翻倍
            elif name == "圣火骑士":
                if attacker.get_runtime_flag('_holy_knight_power', False):
                    power = power * 2
                    attacker.set_runtime_flag('_holy_knight_power', False)

            # 斗技：应对后全技能威力永久+20
            elif name == "斗技":
                bonus = attacker.get_runtime_flag('_doji_power_bonus', 0)
                if bonus > 0:
                    power += bonus

            # 不移：无额外效果的攻击技能，威力+30%
            elif name == "不移":
                if not skill.effects and skill.base_power > 0:
                    power = int(power * 1.3)

            elif name in {"\u5929\u901a\u5730\u660e", "澶╅€氬湴鏄?"} and _has_bloodline(defender, "polluted"):
                power = int(power * 2)
            elif name in {"\u6708\u5149\u5ba1\u5224", "鏈堝厜瀹″垽"} and _has_bloodline(defender, "leader"):
                power = int(power * 2)
            elif name in {"\u7ed2\u7c89\u661f\u5149", "缁掔矇鏄熷厜"} and _has_foreign_element_bloodline(attacker, defender):
                power = int(power * 2)

        return power

    def get_extra_hits(self, attacker: PetInstance, skill, defender: Optional[PetInstance] = None) -> int:
        """被动特性对连击数的额外修正"""
        bonus = 0
        for trait in attacker.template.traits:
            name = trait.name
            # 自由飘：每有1层萌化，连击数+2
            if name == "自由飘":
                cute_stacks = getattr(attacker, 'cute_stacks', 0)
                bonus += cute_stacks * 2
            # 侵蚀：敌方每有1层中毒，连击数+1
            elif name == "侵蚀" and defender:
                bonus += defender.get_status_stacks(StatusEffectType.POISON)
        return bonus

    # ── 效果实现 ─────────────────────────────────────────────────

    def _apply(
        self, trait_name: str,
        pet: PetInstance,
        target: Optional[PetInstance],
        is_player: bool,
        state: BattleState,
        context: str,
        value: int = 0,
        skill=None,
    ):
        # ════════════════════════════════════════════════════════
        # 入场特性
        # ════════════════════════════════════════════════════════

        if trait_name == "威吓" and context == "enter" and target:
            target.stat_modifiers.physical_attack -= 1

        elif trait_name == "降压" and context == "enter" and target:
            target.stat_modifiers.magical_attack -= 1

        elif trait_name == "恶臭" and context == "enter" and target:
            target.stat_modifiers.physical_attack -= 1
            target.stat_modifiers.magical_attack -= 1

        elif trait_name == "压迫" and context == "enter" and target:
            target.stat_modifiers.speed -= 1

        elif trait_name == "强运" and context == "enter":
            m = pet.stat_modifiers
            m.physical_attack += 1
            m.magical_attack += 1
            m.physical_defense += 1
            m.magical_defense += 1
            m.speed += 1

        elif trait_name == "竭泽而渔" and context == "enter" and target:
            target.current_energy = max(0, target.current_energy - 2)

        elif trait_name == "土地神" and context == "enter":
            pet.current_energy = min(10, pet.current_energy + 2)

        elif trait_name == "闪电侠" and context == "enter":
            pet.stat_modifiers.speed += 2

        elif trait_name == "专注力" and context == "enter":
            # 入场首回合获得物攻+100%（10层），每次行动后-20%（由 ON_SKILL_USE 处理）
            pet.stat_modifiers.physical_attack += 10

        elif trait_name == "全神贯注" and context == "enter":
            # 入场时获得物攻+100%（10层），每次行动后-20%（2层）
            pet.stat_modifiers.physical_attack += 10

        elif trait_name == "渴求" and context == "enter":
            # 入场时获得50%吸血（用 lifesteal 字段近似，每次攻击回复50%伤害）
            pet.set_runtime_flag('_lifesteal_bonus', pet.get_runtime_flag('_lifesteal_bonus', 0) + 50)

        elif trait_name == "小偷小摸" and context == "enter":
            # 入场时偷取所有敌方精灵2能量
            opp_state = state.opponent if is_player else state.player
            for opp_pet in opp_state.team:
                if opp_pet.is_alive:
                    stolen = min(2, opp_pet.current_energy)
                    opp_pet.current_energy -= stolen
                    pet.current_energy = min(10, pet.current_energy + stolen)

        elif trait_name == "图书守卫者" and context == "enter":
            # 若自己魔力值为1，获得双攻+50%（5层）
            own_state = state.player if is_player else state.opponent
            if own_state.team_state.leader_evolution_uses == 1:
                pet.stat_modifiers.physical_attack += 5
                pet.stat_modifiers.magical_attack += 5

        elif trait_name == "构装契约者" and context == "enter":
            # 若敌方魔力值为1，获得双防+50%（5层）
            opp_state = state.opponent if is_player else state.player
            if opp_state.team_state.leader_evolution_uses == 1:
                pet.stat_modifiers.physical_defense += 5
                pet.stat_modifiers.magical_defense += 5

        elif trait_name == "铃兰晚钟" and context == "enter":
            # 首次入场时，失去自己一半的当前生命
            if not pet.get_runtime_flag('_lillybell_used', False):
                pet.set_runtime_flag('_lillybell_used', True)
                pet.current_hp = max(1, pet.current_hp // 2)

        elif trait_name == "蓄电池" and context == "enter":
            # 每入场1次，永久获得双攻+20%（2层）
            pet.stat_modifiers.physical_attack += 2
            pet.stat_modifiers.magical_attack += 2

        elif trait_name == "超级电池" and context == "enter":
            # 每入场1次，获得双攻永久+30%（3层）
            pet.stat_modifiers.physical_attack += 3
            pet.stat_modifiers.magical_attack += 3

        elif trait_name == "虫群突袭" and context == "enter":
            # 队伍中每有1只其他虫系精灵，获得攻防速+15%（各1.5层，近似为各1层/精灵）
            own_state = state.player if is_player else state.opponent
            bug_count = sum(
                1 for p in own_state.team
                if p is not pet and p.is_alive
                and hasattr(p.template, 'types') and "虫" in p.template.types
            )
            if bug_count > 0:
                bonus = bug_count  # 简化：每只给1层（约10%）
                pet.stat_modifiers.physical_attack += bonus
                pet.stat_modifiers.magical_attack += bonus
                pet.stat_modifiers.physical_defense += bonus
                pet.stat_modifiers.magical_defense += bonus
                pet.stat_modifiers.speed += bonus

        elif trait_name == "虫群鼓舞" and context == "enter":
            # 队伍中每有1只其他虫系精灵，获得攻防速+10%（各1层）
            own_state = state.player if is_player else state.opponent
            bug_count = sum(
                1 for p in own_state.team
                if p is not pet and p.is_alive
                and hasattr(p.template, 'types') and "虫" in p.template.types
            )
            if bug_count > 0:
                pet.stat_modifiers.physical_attack += bug_count
                pet.stat_modifiers.magical_attack += bug_count
                pet.stat_modifiers.physical_defense += bug_count
                pet.stat_modifiers.magical_defense += bug_count
                pet.stat_modifiers.speed += bug_count

        elif trait_name == "壮胆" and context == "enter":
            # 队伍存在虫系精灵，自己获得双攻+50%（5层）
            own_state = state.player if is_player else state.opponent
            has_bug = any(
                p.is_alive and p is not pet
                and hasattr(p.template, 'types') and "虫" in p.template.types
                for p in own_state.team
            )
            if has_bug:
                pet.stat_modifiers.physical_attack += 5
                pet.stat_modifiers.magical_attack += 5

        elif trait_name == "悲悯" and context == "enter":
            # 己方每有1只力竭的精灵，获得双攻+30%（3层/只）
            own_state = state.player if is_player else state.opponent
            dead_count = sum(1 for p in own_state.team if not p.is_alive)
            if dead_count > 0:
                bonus = dead_count * 3
                pet.stat_modifiers.physical_attack += bonus
                pet.stat_modifiers.magical_attack += bonus

        elif trait_name == "悼亡" and context == "enter":
            # 双方每有1只力竭的精灵，获得双攻+30%（3层/只）
            dead_count = sum(
                1 for ps in [state.player, state.opponent]
                for p in ps.team if not p.is_alive
            )
            if dead_count > 0:
                bonus = dead_count * 3
                pet.stat_modifiers.physical_attack += bonus
                pet.stat_modifiers.magical_attack += bonus

        elif trait_name == "抓到你了" and context == "enter" and target:
            # 入场时敌方获得2层冻结
            target.freeze_stacks += 2

        elif trait_name == "衡量" and context == "enter" and target:
            # 复制敌方的增益
            m_target = target.stat_modifiers
            m_self = pet.stat_modifiers
            if m_target.physical_attack > 0:
                m_self.physical_attack += m_target.physical_attack
            if m_target.magical_attack > 0:
                m_self.magical_attack += m_target.magical_attack
            if m_target.physical_defense > 0:
                m_self.physical_defense += m_target.physical_defense
            if m_target.magical_defense > 0:
                m_self.magical_defense += m_target.magical_defense
            if m_target.speed > 0:
                m_self.speed += m_target.speed

        # ════════════════════════════════════════════════════════
        # 攻击时特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "猛毒" and context == "attack" and target:
            target.add_status(StatusEffectType.POISON, 1)

        elif trait_name == "灼热" and context == "attack" and target:
            target.add_status(StatusEffectType.BURN, 2)

        elif trait_name == "冰封" and context == "attack" and target:
            target.freeze_stacks += 1

        elif trait_name == "寄生虫" and context == "attack" and target:
            target.add_status(StatusEffectType.PARASITE, 1)

        elif trait_name == "吸血鬼" and context == "attack":
            if value > 0:
                heal = int(value * 0.15)
                pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "连击" and context == "attack" and target and value > 0:
            # 攻击时，下回合攻击对手连击数+2（用 warmup_hits_bonus 存储）
            pet.warmup_hits_bonus = getattr(pet, 'warmup_hits_bonus', 0) + 2

        elif trait_name == "灵魂灼伤" and context == "attack" and target and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "冰":
                target.add_status(StatusEffectType.BURN, 4)
            elif skill_type == "火":
                target.freeze_stacks += 2

        elif trait_name == "高浓生物碱" and context == "attack" and target:
            target.add_status(StatusEffectType.POISON, 2)

        elif trait_name == "毒腺" and context == "attack" and target and skill:
            skill_cost = getattr(skill, 'effective_energy_cost', getattr(skill, 'energy_cost', 99))
            if skill_cost <= 1:
                target.add_status(StatusEffectType.POISON, 4)

        elif trait_name == "灰色肖像" and context == "attack" and target:
            # 攻击使敌方已有的减益层数+3
            m = target.stat_modifiers
            if m.physical_attack < 0:
                m.physical_attack -= 3
            if m.magical_attack < 0:
                m.magical_attack -= 3
            if m.physical_defense < 0:
                m.physical_defense -= 3
            if m.magical_defense < 0:
                m.magical_defense -= 3
            if m.speed < 0:
                m.speed -= 3
            # 状态减益也+3层
            for st in [StatusEffectType.POISON, StatusEffectType.BURN, StatusEffectType.PARASITE]:
                stacks = target.get_status_stacks(st)
                if stacks > 0:
                    target.add_status(st, 3)

        elif trait_name == "加个雪球" and context == "attack" and target and skill:
            # 使敌方获得冻结时，也会使其获得2层冻结
            # 判断本次技能是否含有冻结效果（近似：由技能效果列表判断）
            pass  # 此特性需在具体冻结施加时触发，此处略（见 捉迷藏 的实现）

        # ════════════════════════════════════════════════════════
        # 使用技能后特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "助燃" and context == "skill_use" and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "火":
                pet.stat_modifiers.physical_attack += 2
                pet.stat_modifiers.magical_attack += 2

        elif trait_name == "爆燃" and context == "skill_use" and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "火":
                pet.stat_modifiers.physical_attack += 3
                pet.stat_modifiers.magical_attack += 3

        elif trait_name == "氧循环" and context == "skill_use" and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "草":
                heal = int(pet.max_hp * 0.1)
                pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "深层氧循环" and context == "skill_use" and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "草":
                heal = int(pet.max_hp * 0.15)
                pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "浸润" and context == "skill_use" and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "水":
                for sk in pet.skills:
                    SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -1)

        elif trait_name == "浪潮" and context == "skill_use" and skill:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "水":
                for sk in pet.skills:
                    SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -2)

        elif trait_name == "扩散侵蚀" and context == "skill_use" and skill and target:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "水":
                poison_mark = target.get_status_stacks(StatusEffectType.POISON_MARK)
                if poison_mark > 0:
                    target.add_status(StatusEffectType.POISON, poison_mark * 2)

        elif trait_name == "碰瓷" and context == "skill_use" and skill and target:
            skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
            if skill_type == "恶":
                target.current_energy = max(0, target.current_energy - 2)

        elif trait_name == "三鼓作气" and context == "skill_use" and skill:
            skill_cost = getattr(skill, 'effective_energy_cost', getattr(skill, 'energy_cost', 0))
            if skill_cost == 3:
                # 永久攻防+20%（2层）
                pet.stat_modifiers.physical_attack += 2
                pet.stat_modifiers.magical_attack += 2
                pet.stat_modifiers.physical_defense += 2
                pet.stat_modifiers.magical_defense += 2

        elif trait_name == "鼓气" and context == "skill_use" and skill:
            skill_cost = getattr(skill, 'effective_energy_cost', getattr(skill, 'energy_cost', 0))
            if skill_cost == 3:
                # 本回合攻防+20%（2层，非永久，但引擎无临时buff，用普通层数代替）
                pet.stat_modifiers.physical_attack += 2
                pet.stat_modifiers.magical_attack += 2
                pet.stat_modifiers.physical_defense += 2
                pet.stat_modifiers.magical_defense += 2

        elif trait_name == "全神贯注" and context == "skill_use":
            # 每次行动后物攻-20%（2层）
            pet.stat_modifiers.physical_attack = max(-10, pet.stat_modifiers.physical_attack - 2)

        elif trait_name == "专注力" and context == "skill_use":
            # 每次行动后物攻-20%（2层）
            pet.stat_modifiers.physical_attack = max(-10, pet.stat_modifiers.physical_attack - 2)

        # ════════════════════════════════════════════════════════
        # 受击时特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "反击" and context == "damaged" and target:
            counter_dmg = int(value * 0.3)
            if counter_dmg > 0:
                target.current_hp = max(0, target.current_hp - counter_dmg)
                if target.current_hp == 0:
                    target.is_alive = False

        elif trait_name == "荆棘" and context == "damaged" and target:
            counter_dmg = int(value * 0.15)
            if counter_dmg > 0:
                target.current_hp = max(0, target.current_hp - counter_dmg)
                if target.current_hp == 0:
                    target.is_alive = False

        elif trait_name == "愤怒" and context == "damaged":
            pet.stat_modifiers.physical_attack += 1

        elif trait_name == "坚韧" and context == "damaged":
            pet.stat_modifiers.physical_defense += 1
            pet.stat_modifiers.magical_defense += 1

        elif trait_name == "再生" and context == "damaged":
            heal = int(pet.max_hp * 0.05)
            pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "化茧" and context == "damaged":
            # 受到致命伤害时，获得1层萌化，并免疫此次伤害
            # 如果 HP <= 0 则回复至 1 并获得萌化（cute_stacks）
            if pet.current_hp <= 0 and not pet.get_runtime_flag('_cocooned', False):
                pet.set_runtime_flag('_cocooned', True)
                pet.current_hp = 1
                pet.is_alive = True
                pet.cute_stacks = getattr(pet, 'cute_stacks', 0) + 1
                # 萌化附带减益：物攻-1层、魔攻-1层（近似）
                pet.stat_modifiers.physical_attack -= 1
                pet.stat_modifiers.magical_attack -= 1

        # ════════════════════════════════════════════════════════
        # 死亡时特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "同归于尽" and context == "death" and target:
            damage = int(pet.max_hp * 0.5)
            target.current_hp = max(0, target.current_hp - damage)
            if target.current_hp == 0:
                target.is_alive = False

        elif trait_name == "遗愿" and context == "death":
            from core.models import FieldMark
            mark = FieldMark(
                type_key=StatusEffectType.ATTACK_MARK.value,
                stacks=3,
                is_positive=True
            )
            state.set_mark(is_player, mark)

        elif trait_name == "爆裂" and context == "death" and target:
            damage = int(pet.max_hp * 0.3)
            target.current_hp = max(0, target.current_hp - damage)
            if target.current_hp == 0:
                target.is_alive = False

        elif trait_name == "涅槃" and context == "death":
            if not pet.get_runtime_flag('_nirvana_used', False):
                pet.set_runtime_flag('_nirvana_used', True)
                pet.is_alive = True
                pet.current_hp = int(pet.max_hp * 0.5)

        elif trait_name == "虚假宝箱" and context == "death" and target:
            # 自己力竭时，敌方获得攻防+20%（2层）
            target.stat_modifiers.physical_attack += 2
            target.stat_modifiers.magical_attack += 2
            target.stat_modifiers.physical_defense += 2
            target.stat_modifiers.magical_defense += 2

        elif trait_name == "付给恶魔的赎价" and context == "death":
            # 被击败时，自己额外损失1点魔力（用首领化次数近似）
            own_state = state.player if is_player else state.opponent
            own_state.team_state.leader_evolution_uses = max(
                0, own_state.team_state.leader_evolution_uses - 1
            )

        # ════════════════════════════════════════════════════════
        # 击杀时特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "收割" and context == "kill":
            heal = int(pet.max_hp * 0.2)
            pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "猎人" and context == "kill":
            pet.stat_modifiers.speed += 2

        elif trait_name == "贪婪" and context == "kill":
            pet.current_energy = min(10, pet.current_energy + 3)

        elif trait_name == "振奋虫心" and context == "kill":
            own_state = state.player if is_player else state.opponent
            self._grant_devotion(
                own_state.team_state, 5,
                f"振奋虫心:{pet.template.name}:{state.turn}"
            )

        # ════════════════════════════════════════════════════════
        # 离场时特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "告别" and context == "switch_out" and target:
            target.add_status(StatusEffectType.POISON_MARK, 1)

        elif trait_name == "快充" and context == "switch_out":
            # 离场时回复10能量（存储到 pet，供下次入场使用）
            pet.current_energy = min(10, pet.current_energy + 10)

        elif trait_name == "防过载保护" and context == "switch_out":
            # 每次行动后脱离（触发 pending_switch_out，由引擎执行换宠）
            pet.pending_switch_out = True

        # ════════════════════════════════════════════════════════
        # 回合结束特性
        # ════════════════════════════════════════════════════════

        elif trait_name == "养分内循环" and context == "end_of_turn":
            pet.current_energy = min(10, pet.current_energy + 6)

        elif trait_name == "养分重吸收" and context == "end_of_turn":
            pet.current_energy = min(10, pet.current_energy + 3)

        elif trait_name == "生长" and context == "end_of_turn":
            heal = int(pet.max_hp * 0.12)
            pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "吸积盘" and context == "end_of_turn" and target:
            target.add_status(StatusEffectType.STAR_FALL_MARK, 2)

        elif trait_name == "毒蘑菇" and context == "end_of_turn":
            # 偷取敌方场上所有精灵1能量
            opp_state = state.opponent if is_player else state.player
            for opp_pet in opp_state.team:
                if opp_pet.is_alive:
                    stolen = min(1, opp_pet.current_energy)
                    opp_pet.current_energy -= stolen
                    pet.current_energy = min(10, pet.current_energy + stolen)

        elif trait_name == "大捞一笔" and context == "end_of_turn":
            # 偷取所有敌方精灵2能量
            opp_state = state.opponent if is_player else state.player
            for opp_pet in opp_state.team:
                if opp_pet.is_alive:
                    stolen = min(2, opp_pet.current_energy)
                    opp_pet.current_energy -= stolen
                    pet.current_energy = min(10, pet.current_energy + stolen)

        elif trait_name == "蚀刻" and context == "end_of_turn" and target:
            # 敌方每2层中毒转化为1层中毒印记
            poison = target.get_status_stacks(StatusEffectType.POISON)
            if poison >= 2:
                convert = poison // 2
                target.status_effects[StatusEffectType.POISON] = poison - convert * 2
                if target.status_effects[StatusEffectType.POISON] == 0:
                    target.remove_status(StatusEffectType.POISON)
                target.add_status(StatusEffectType.POISON_MARK, convert)

        elif trait_name == "复方汤剂" and context == "end_of_turn" and target:
            # 中毒效果触发次数+1（近似：额外施加1层中毒伤害）
            poison = target.get_status_stacks(StatusEffectType.POISON)
            if poison > 0:
                # 施加1次中毒伤害等效：直接扣血
                poison_dmg = max(1, int(target.max_hp * 0.05))
                target.current_hp = max(0, target.current_hp - poison_dmg)
                if target.current_hp == 0:
                    target.is_alive = False

        elif trait_name == "特殊清洁场景" and context == "end_of_turn" and target:
            # 偷取敌方1层印记
            opp_is_player = not is_player
            opp_pos, opp_neg = state.get_marks(opp_is_player)
            if opp_neg and opp_neg.stacks > 0:
                opp_neg.stacks -= 1
                if opp_neg.stacks == 0:
                    state.set_mark(opp_is_player, type('_', (), {
                        'stacks': 0, 'is_positive': False,
                        'type_key': opp_neg.type_key
                    })())
                # 转给己方（己方获得正面印记）
                from core.models import FieldMark
                own_mark = FieldMark(
                    type_key=opp_neg.type_key, stacks=1, is_positive=True
                )
                state.set_mark(is_player, own_mark)

        # ════════════════════════════════════════════════════════
        # 回合结束：石天平
        # ════════════════════════════════════════════════════════

        elif trait_name == "石天平" and context == "end_of_turn" and target and skill:
            # 若使用技能能耗高于敌方，回合结束敌方失去能耗之差的能量
            # 此处 skill 为 None（end_of_turn 无 skill），改为存储上次能耗
            pass  # 需要 on_skill_use 时记录，此处暂时留空

        # ════════════════════════════════════════════════════════
        # 攻击时：毒牙、月牙雪糕、最好的伙伴
        # ════════════════════════════════════════════════════════

        elif trait_name == "毒牙" and context == "attack" and target:
            # 使敌方获得中毒时，也会使其获得魔攻和魔防-40%（4层）
            if target.get_status_stacks(StatusEffectType.POISON) > 0:
                target.stat_modifiers.magical_attack -= 4
                target.stat_modifiers.magical_defense -= 4

        elif trait_name == "月牙雪糕" and context == "attack" and target and skill:
            # 使用攻击技能时，敌方每层冻结视为1层额外星陨印记
            freeze = target.freeze_stacks
            if freeze > 0:
                target.add_status(StatusEffectType.STAR_FALL_MARK, freeze)

        elif trait_name == "最好的伙伴" and context == "attack" and target:
            # 造成克制伤害后，获得攻防速+20%（2层），并回复2能量
            if value > 0 and pet.get_runtime_flag('_last_attack_super_effective', False):
                pet.stat_modifiers.physical_attack += 2
                pet.stat_modifiers.magical_attack += 2
                pet.stat_modifiers.physical_defense += 2
                pet.stat_modifiers.magical_defense += 2
                pet.stat_modifiers.speed += 2
                pet.current_energy = min(10, pet.current_energy + 2)

        # ════════════════════════════════════════════════════════
        # 使用技能后：洄游、奔波命
        # ════════════════════════════════════════════════════════

        elif trait_name == "洄游" and context == "skill_use" and skill:
            # 每次进入蓄力状态，获得全技能能耗永久-1
            if getattr(pet, 'charging_skill', None):
                for sk in pet.skills:
                    SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -1)

        elif trait_name == "奔波命" and context == "skill_use" and skill:
            # 使用防御技能后，回合结束时脱离
            from core.models import SkillCategory
            if getattr(skill, 'category', None) == SkillCategory.DEFENSE:
                pet.pending_switch_out = True

        # ════════════════════════════════════════════════════════
        # 受击时：嫁祸
        # ════════════════════════════════════════════════════════

        elif trait_name == "嫁祸" and context == "damaged":
            # 用 _damage_milestone 追踪
            total_lost = pet.max_hp - pet.current_hp
            milestone = int(total_lost / (pet.max_hp * 0.25))
            prev_milestone = pet.get_runtime_flag('_jiahuo_milestone', 0)
            if milestone > prev_milestone:
                bonus = (milestone - prev_milestone) * 2
                pet.warmup_hits_bonus = getattr(pet, 'warmup_hits_bonus', 0) + bonus
                pet.set_runtime_flag('_jiahuo_milestone', milestone)

        elif trait_name == "坚韧铠甲" and context == "damaged" and value > 0:
            own_state = state.player if is_player else state.opponent
            self._grant_devotion(
                own_state.team_state, 1,
                f"坚韧铠甲:{pet.template.name}:{state.turn}:{value}"
            )

        # ════════════════════════════════════════════════════════
        # 离场时：吉利丁片、茶多酚、美拉德反应、洁癖、下黑手
        # ════════════════════════════════════════════════════════

        elif trait_name == "吉利丁片" and context == "switch_out":
            # 离场后，更换入场的精灵获得双防+20%且免疫冻结
            own_state = state.player if is_player else state.opponent
            own_state.team_state.next_pet_gifts.add('双防+2')
            own_state.team_state.next_pet_gifts.add('免疫冻结')

        elif trait_name == "茶多酚" and context == "switch_out":
            # 离场后，更换入场的精灵回复20%生命且免疫寄生
            own_state = state.player if is_player else state.opponent
            own_state.team_state.next_pet_gifts.add('回复20%生命')
            own_state.team_state.next_pet_gifts.add('免疫寄生')

        elif trait_name == "美拉德反应" and context == "switch_out":
            # 离场后，更换入场的精灵获得双攻+20%且免疫灼烧
            own_state = state.player if is_player else state.opponent
            own_state.team_state.next_pet_gifts.add('双攻+2')
            own_state.team_state.next_pet_gifts.add('免疫灼烧')

        elif trait_name == "洁癖" and context == "switch_out":
            # 离场后，自己的增益和减益会被更换入场的精灵继承
            # 存储当前 stat_modifiers 到 next_pet_gifts（简化：只传递正面buff）
            own_state = state.player if is_player else state.opponent
            m = pet.stat_modifiers
            if m.physical_attack > 0:
                own_state.team_state.next_pet_gifts.add(f'物攻+{m.physical_attack}')
            if m.magical_attack > 0:
                own_state.team_state.next_pet_gifts.add(f'魔攻+{m.magical_attack}')
            if m.physical_defense > 0:
                own_state.team_state.next_pet_gifts.add(f'物防+{m.physical_defense}')
            if m.magical_defense > 0:
                own_state.team_state.next_pet_gifts.add(f'魔防+{m.magical_defense}')
            if m.speed > 0:
                own_state.team_state.next_pet_gifts.add(f'速度+{m.speed}')

        elif trait_name == "下黑手" and context == "switch_out" and target:
            # 敌方精灵离场后，更换入场的精灵获得5层中毒
            opp_state = state.opponent if is_player else state.player
            opp_state.team_state.next_pet_gifts.add('中毒5层')

        # ════════════════════════════════════════════════════════
        # 应对成功后
        # ════════════════════════════════════════════════════════

        elif trait_name == "圣火骑士" and context == "counter_success":
            # 应对成功后，下次攻击威力翻倍（存储标记）
            pet.set_runtime_flag('_holy_knight_power', True)

        elif trait_name == "野性感官" and context == "counter_success":
            # 应对成功后，下次行动先手+1
            pet.priority_bonus += 1

        elif trait_name == "指挥家" and context == "counter_success":
            # 应对成功后，永久获得双攻+20%（2层）
            pet.stat_modifiers.physical_attack += 2
            pet.stat_modifiers.magical_attack += 2

        elif trait_name == "思维之盾" and context == "counter_success":
            # 应对成功后，下次行动技能能耗-5
            pet.next_skill_energy_discount = getattr(pet, 'next_skill_energy_discount', 0) + 5

        elif trait_name == "斗技" and context == "counter_success":
            # 应对成功后，获得全技能威力永久+20（存在 pet 上，由 modify_skill_power 消费）
            pet.set_runtime_flag('_doji_power_bonus', pet.get_runtime_flag('_doji_power_bonus', 0) + 20)

        # ════════════════════════════════════════════════════════
        # 入场积累型
        # ════════════════════════════════════════════════════════

        elif trait_name == "地脉" and context == "enter":
            # 初始能量为0，入场前己方精灵每放1次地系技能，回复3能量
            own_state = state.player if is_player else state.opponent
            pet.current_energy = 0
            energy = min(10, own_state.team_state.earth_skill_count * 3)
            pet.current_energy = energy

        elif trait_name == "地脉馈赠" and context == "enter":
            # 突破能量上限并立即回复10能量，入场前己方精灵每放1次地系技能，回复3能量
            own_state = state.player if is_player else state.opponent
            pet.current_energy = 10 + own_state.team_state.earth_skill_count * 3

        elif trait_name == "打雪仗" and context == "enter":
            # 初始能量为0，入场前己方精灵每放1次冰系技能，回复3能量
            own_state = state.player if is_player else state.opponent
            pet.current_energy = min(10, own_state.team_state.ice_skill_count * 3)

        elif trait_name == "散热" and context == "enter":
            # 初始能量为0，入场前己方精灵每放1次火系技能，回复3能量
            own_state = state.player if is_player else state.opponent
            pet.current_energy = min(10, own_state.team_state.fire_skill_count * 3)

        elif trait_name == "慢热型" and context == "enter":
            # 初始能量为0，入场前己方精灵每成功应对1次，回复5能量
            own_state = state.player if is_player else state.opponent
            pet.current_energy = min(10, own_state.team_state.counter_success_count * 5)

        elif trait_name == "水翼推进" and context == "enter":
            # 己方精灵每使用1次水系技能，入场时获得全技能能耗-1
            own_state = state.player if is_player else state.opponent
            reduction = own_state.team_state.water_skill_count
            for sk in pet.skills:
                SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -reduction)

        elif trait_name == "水翼飞升" and context == "enter":
            # 己方精灵每使用1次水系技能，入场时获得全技能能耗-1，且能耗为0的技能威力+30%
            own_state = state.player if is_player else state.opponent
            reduction = own_state.team_state.water_skill_count
            for sk in pet.skills:
                SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -reduction)
                if sk.energy_cost == 0 and sk.base_power > 0:
                    sk.base_power = int(sk.base_power * 1.3)

        elif trait_name == "蒸汽膨胀" and context == "enter":
            # 己方精灵每使用1次火系技能，入场时获得全技能威力+10
            own_state = state.player if is_player else state.opponent
            bonus = own_state.team_state.fire_skill_count * 10
            for sk in pet.skills:
                if sk.base_power > 0:
                    sk.base_power += bonus

        elif trait_name == "拨浪鼓" and context == "enter":
            # 己方精灵每使用1次状态技能，入场时毒系和萌系技能威力+10
            own_state = state.player if is_player else state.opponent
            bonus = own_state.team_state.status_skill_count * 10
            for sk in pet.skills:
                sk_type = getattr(sk, 'element', None) or getattr(sk, 'type', None)
                if sk_type in ('毒', '萌') and sk.base_power > 0:
                    sk.base_power += bonus

        elif trait_name == "搜刮" and context == "enter":
            # 敌方每使用1次聚能或换宠，入场时获得魔攻+20%（2层）
            opp_state = state.opponent if is_player else state.player
            bonus = opp_state.team_state.gather_energy_count + opp_state.team_state.switch_count
            pet.stat_modifiers.magical_attack += bonus * 2

        elif trait_name == "身经百练" and context == "enter":
            # 己方精灵每应对1次，入场时水系和武系技能威力+20%
            own_state = state.player if is_player else state.opponent
            bonus_pct = own_state.team_state.counter_success_count * 0.2
            for sk in pet.skills:
                sk_type = getattr(sk, 'element', None) or getattr(sk, 'type', None)
                if sk_type in ('水', '武') and sk.base_power > 0:
                    sk.base_power = int(sk.base_power * (1 + bonus_pct))

        elif trait_name == "定向精炼" and context == "enter":
            # 己方精灵每使用1次防御技能，入场时机械系和地面系技能威力+10%
            own_state = state.player if is_player else state.opponent
            bonus_pct = own_state.team_state.defense_skill_count * 0.1
            for sk in pet.skills:
                sk_type = getattr(sk, 'element', None) or getattr(sk, 'type', None)
                if sk_type in ('机械', '地') and sk.base_power > 0:
                    sk.base_power = int(sk.base_power * (1 + bonus_pct))

        elif trait_name == "守护者" and context == "enter":
            # 己方其他精灵每有1层萌化，全技能能耗-1
            own_state = state.player if is_player else state.opponent
            total_cute = sum(
                getattr(p, 'cute_stacks', 0)
                for p in own_state.team
                if p is not pet and p.is_alive
            )
            for sk in pet.skills:
                SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -total_cute)

        # ════════════════════════════════════════════════════════
        # 其他入场型
        # ════════════════════════════════════════════════════════

        elif trait_name == "得寸进尺" and context == "enter":
            # 天气为雨天，或处于其他水系环境中时，获得双攻+100%（10层）
            if state.weather in ('雨天', '水系环境', '暴雨'):
                pet.stat_modifiers.physical_attack += 10
                pet.stat_modifiers.magical_attack += 10

        elif trait_name == "御驾亲征" and context == "enter":
            # 大幅提升种族资质（提升各属性20%近似 2层buff）
            pet.stat_modifiers.physical_attack += 2
            pet.stat_modifiers.magical_attack += 2
            pet.stat_modifiers.physical_defense += 2
            pet.stat_modifiers.magical_defense += 2
            pet.stat_modifiers.speed += 2

        elif trait_name == "保守派" and context == "enter":
            # 总技能能耗小于4时，自己获得双防+80%（8层）
            total_cost = sum(getattr(sk, 'energy_cost', 0) for sk in pet.skills)
            if total_cost < 4:
                pet.stat_modifiers.physical_defense += 8
                pet.stat_modifiers.magical_defense += 8

        elif trait_name == "冻土" and context == "enter":
            # 每携带1个冰系技能进入战斗，地系技能威力+10%
            ice_count = sum(
                1 for sk in pet.skills
                if (getattr(sk, 'element', None) or getattr(sk, 'type', None)) == '冰'
            )
            if ice_count > 0:
                for sk in pet.skills:
                    if (getattr(sk, 'element', None) or getattr(sk, 'type', None)) == '地' and sk.base_power > 0:
                        sk.base_power = int(sk.base_power * (1 + ice_count * 0.1))

        elif trait_name == "消波块" and context == "enter":
            # 每携带1个水系技能进入战斗，地系技能能耗-1
            water_count = sum(
                1 for sk in pet.skills
                if (getattr(sk, 'element', None) or getattr(sk, 'type', None)) == '水'
            )
            if water_count > 0:
                for sk in pet.skills:
                    if (getattr(sk, 'element', None) or getattr(sk, 'type', None)) == '地':
                        SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -water_count)

        elif trait_name == "溶解腐蚀" and context == "enter":
            # 每携带1个毒系技能进入战斗，水系技能使敌方获得2层中毒（标记到 pet）
            poison_count = sum(
                1 for sk in pet.skills
                if (getattr(sk, 'element', None) or getattr(sk, 'type', None)) == '毒'
            )
            pet.set_runtime_flag('_dissolve_corrosion', poison_count)  # 在 ON_SKILL_USE 中消费

        elif trait_name == "夺目" and context == "enter":
            # 非光系技能威力+25%
            for sk in pet.skills:
                sk_type = getattr(sk, 'element', None) or getattr(sk, 'type', None)
                if sk_type != '光' and sk.base_power > 0:
                    sk.base_power = int(sk.base_power * 1.25)

        elif trait_name == "飓风" and context == "enter":
            # 若其他翼系精灵携带相同技能，则自己所有技能获得迅捷
            # 被敌方精灵击败时，己方额外损失1点魔力（在 ON_DEATH 中处理）
            own_state = state.player if is_player else state.opponent
            my_skill_names = {sk.name for sk in pet.skills}
            has_wing_ally_with_same = any(
                p.is_alive and p is not pet
                and hasattr(p.template, 'types') and '翼' in p.template.types
                and any(sk.name in my_skill_names for sk in p.skills)
                for p in own_state.team
            )
            if has_wing_ally_with_same:
                pet.set_runtime_flag('_hurricane_swift', True)  # 在 action_generator / engine 中读取

        elif trait_name == "张弛有度" and context == "enter":
            # 周末（周六/日）双攻+40%（4层），其他时间双防+40%（4层）
            import datetime
            weekday = datetime.datetime.now().weekday()  # 0=周一 … 6=周日
            if weekday >= 5:  # 周六=5，周日=6
                pet.stat_modifiers.physical_attack += 4
                pet.stat_modifiers.magical_attack += 4
            else:
                pet.stat_modifiers.physical_defense += 4
                pet.stat_modifiers.magical_defense += 4

        # ════════════════════════════════════════════════════════
        # 入场时修改技能属性
        # ════════════════════════════════════════════════════════

        elif trait_name == "快锤" and context == "enter":
            # 携带的能耗小于3的技能，获得迅捷（标记 _swift_low_cost，由引擎在执行时判断）
            pet.set_runtime_flag('_swift_low_cost', True)

        elif trait_name == "暴食" and context == "enter":
            # 携带的龙系技能获得迅捷
            pet.set_runtime_flag('_swift_dragon', True)

        elif trait_name == "生物电" and context == "enter":
            # 携带的电系技能获得迸发：能耗-2（入场时直接修改技能能耗）
            for sk in pet.skills:
                sk_type = getattr(sk, 'element', None) or getattr(sk, 'type', None)
                if sk_type == '电':
                    SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, -2)

        elif trait_name == "超负荷" and context == "enter":
            # 攻击技能获得迸发：敌方获得全技能能耗+1（标记，在 ON_ATTACK 中消费）
            from core.models import SkillCategory
            pet.set_runtime_flag('_overload_burst', True)

        elif trait_name == "连续负荷" and context == "enter":
            # 自己技能的迸发效果延长1回合
            pet.set_runtime_flag('_extend_burst', True)

        elif trait_name == "起飞加速" and context == "enter":
            # 本场战斗首次使用的技能获得迅捷（标记，首次使用后清除）
            pet.set_runtime_flag('_takeoff_speed', True)

        elif trait_name == "噼啪！" and context == "enter":
            # 入场后首次行动，所选技能使用次数+1（标记）
            pet.set_runtime_flag('_crackle_first', True)

        elif trait_name == "囤积" and context == "enter":
            # 每有1能量，获得双防+10%（1层）
            bonus = pet.current_energy
            pet.stat_modifiers.physical_defense += bonus
            pet.stat_modifiers.magical_defense += bonus

        elif trait_name == "先知" and context == "enter" and target:
            # 若敌方技能足够击败自己，回合开始时获得速度+50（近似：入场时给速度buff）
            # 用固定速度buff代替，因为引擎无"回合开始"钩子
            # 简化：给速度+5层（50%加成近似）和双攻+5层
            pet.stat_modifiers.speed += 5
            pet.stat_modifiers.physical_attack += 5
            pet.stat_modifiers.magical_attack += 5

        elif trait_name == "预警" and context == "enter" and target:
            # 若敌方技能足够击败自己，回合开始时获得速度+50
            pet.stat_modifiers.speed += 5

        elif trait_name == "游弋" and context == "enter":
            # 蓄力时可使用任一携带技能，且获得双防+100%（10层）
            # 双防加成在蓄力状态下生效（近似：始终给予）
            if pet.charging_skill:
                pet.stat_modifiers.physical_defense += 10
                pet.stat_modifiers.magical_defense += 10

        elif trait_name == "嫉妒" and context == "enter":
            # 蓄力状态下，可以使用任一携带技能（标记，由 action_generator 判断）
            pet.set_runtime_flag('_jealous_charging', True)

        elif trait_name == "多人宿舍" and context == "enter":
            # 自己的能量可以超过能量上限（标记）
            pet.set_runtime_flag('_no_energy_cap', True)

        # ════════════════════════════════════════════════════════
        # 回合结束特性（新增）
        # ════════════════════════════════════════════════════════

        elif trait_name == "星地善良" and context == "end_of_turn":
            # 若场上己方精灵能量为0，自己立即替换此精灵
            own_state = state.player if is_player else state.opponent
            active = own_state.get_active_pet()
            if active and active.current_energy == 0 and active is not pet:
                # 触发换宠（pet 是自己，active 是场上精灵）
                # 实际 pet 即为场上精灵，此处 active == pet
                pass
            # 修正：pet 就是场上精灵，检查自己能量是否为0
            if pet.current_energy == 0:
                pet.pending_switch_out = True

        elif trait_name == "仁心" and context == "end_of_turn":
            # 敌方受到灼烧伤害时，自己回复等量生命
            # 近似：回合结束时，若敌方有灼烧，按层数回复生命
            if target:
                burn = target.get_status_stacks(StatusEffectType.BURN)
                if burn > 0:
                    heal = int(target.max_hp * 0.05 * burn)
                    pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "腐植循环" and context == "end_of_turn":
            # 每回复1能量，同时回复5%生命（近似：若能量未满，回复生命）
            energy_gained = min(3, 10 - pet.current_energy)  # 聚能等效
            if energy_gained > 0:
                heal = int(pet.max_hp * 0.05 * energy_gained)
                pet.current_hp = min(pet.max_hp, pet.current_hp + heal)

        elif trait_name == "双向光速" and context == "end_of_turn":
            # 主效果已在 ExtendedBattleEngine 中统一处理
            pass

        elif trait_name == "陨落" and context == "end_of_turn":
            # 主效果已在 ExtendedBattleEngine 中统一处理
            pass

        elif trait_name == "煤渣草" and context == "end_of_turn":
            # 在场时，所有灼烧的衰减变为增长（回合结束灼烧不减反增）
            # 先对自己处理（若有灼烧）
            for p in [pet, target]:
                if p and p.is_alive:
                    burn = p.get_status_stacks(StatusEffectType.BURN)
                    if burn > 0:
                        # 正常灼烧在 status_processor 中减少1层，此处补回2层（净增1层）
                        p.add_status(StatusEffectType.BURN, 2)

        elif trait_name == "扫拖一体" and context == "end_of_turn" and target:
            # 回合结束时驱散敌方1层印记（奉献部分忽略）
            opp_is_player = not is_player
            opp_pos, opp_neg = state.get_marks(opp_is_player)
            dispelled = False
            # 优先驱散负面印记（对对手是负面的 = 对己方是正面的，这里 opp_neg 是对敌方的负面印记）
            # 洛克王国中"印记"一般是指对自身有效的场地印记
            # 这里驱散敌方场上1层印记（正面或负面各一层）
            if opp_neg and opp_neg.stacks > 0:
                opp_neg.stacks -= 1
                dispelled = True
                if opp_neg.stacks == 0:
                    state.set_mark(opp_is_player, None)
            elif opp_pos and opp_pos.stacks > 0:
                opp_pos.stacks -= 1
                dispelled = True
                if opp_pos.stacks == 0:
                    state.set_mark(opp_is_player, None)
            if dispelled:
                own_state = state.player if is_player else state.opponent
                self._grant_devotion(
                    own_state.team_state, 1,
                    f"扫拖一体:{pet.template.name}:{state.turn}"
                )

        elif trait_name == "花精灵" and context == "end_of_turn":
            own_state = state.player if is_player else state.opponent
            self._grant_devotion(
                own_state.team_state, 1,
                f"花精灵:{pet.template.name}:{state.turn}"
            )

        # ════════════════════════════════════════════════════════
        # 攻击时：咔咔冲刺、捉迷藏
        # ════════════════════════════════════════════════════════

        elif trait_name == "咔咔冲刺" and context == "attack":
            # 若先于敌方行动，行动后获得连击数+1（warmup_hits_bonus）
            if pet.get_runtime_flag('_is_first_attacker', False):
                pet.warmup_hits_bonus = getattr(pet, 'warmup_hits_bonus', 0) + 1

        elif trait_name == "捉迷藏" and context == "attack" and target and skill:
            # 使敌方获得冻结时，也会使其获得全技能能耗+1
            # 判断本次技能是否含冻结效果
            from core.models import EffectType
            has_freeze_effect = any(
                (e.type == EffectType.APPLY_STATUS and '冻结' in e.desc)
                or (e.type == EffectType.APPLY_STATUS and e.status_type == 'freeze')
                for e in skill.effects
            )
            if has_freeze_effect or target.freeze_stacks > 0:
                for sk in target.skills:
                    SlotEffectsProcessor.apply_energy_cost_delta(target, sk, 1)

        # ════════════════════════════════════════════════════════
        # 受击时：石头大餐
        # ════════════════════════════════════════════════════════

        elif trait_name == "石头大餐" and context == "damaged":
            # 能量不足时，消耗5%生命代替1能量（入场后被动，此处在受击时检查并补充）
            # 实际应在使用技能时触发，此处近似：受击后若能量为0，扣血补能量
            if pet.current_energy == 0 and pet.current_hp > 0:
                cost_hp = int(pet.max_hp * 0.05)
                if pet.current_hp > cost_hp:
                    pet.current_hp -= cost_hp
                    pet.current_energy = min(1, 10)

        # ════════════════════════════════════════════════════════
        # 使用技能后：营养液泡、泛音列、哨兵
        # ════════════════════════════════════════════════════════

        elif trait_name == "营养液泡" and context == "skill_use":
            # 获得增益时，额外获得层数+2（在使用有buff效果的技能后触发）
            from core.models import EffectType
            if skill:
                has_buff = any(e.type == EffectType.STAT_BUFF and e.target == 'self' for e in skill.effects)
                if has_buff:
                    # 给自身所有正面属性额外+2
                    m = pet.stat_modifiers
                    for attr in ['physical_attack', 'magical_attack', 'physical_defense',
                                 'magical_defense', 'speed']:
                        v = getattr(m, attr)
                        if v > 0:
                            setattr(m, attr, v + 2)

        elif trait_name == "泛音列" and context == "skill_use" and target and skill:
            # 使用状态技能后，敌方获得【聒噪】效果（速度-3层，持续3回合近似）
            from core.models import SkillCategory
            if getattr(skill, 'category', None) == SkillCategory.STATUS:
                target.stat_modifiers.speed -= 3

        elif trait_name == "哨兵" and context == "skill_use":
            # 回合开始时若敌方技能足够击败自己，自己获得速度+50，行动后脱离
            # 近似：每次使用技能后脱离（模拟"行动后脱离"）
            pet.pending_switch_out = True

        # ════════════════════════════════════════════════════════
        # 不朽：力竭3回合后复活
        # ════════════════════════════════════════════════════════

        elif trait_name == "不朽" and context == "death":
            if not pet.get_runtime_flag('_immortal_used', False):
                pet.set_runtime_flag('_immortal_used', True)
                # 记录死亡回合，3回合后复活
                # 近似：标记为"等待复活"，由回合结束处理器检查
                immortal_revive_turn = pet.get_runtime_flag('_immortal_revive_turn', -1)
                pet.set_runtime_flag('_immortal_revive_turn', immortal_revive_turn)
                if immortal_revive_turn < 0:
                    # 此处无法获取当前回合数，使用固定延迟3
                    pet.set_runtime_flag('_immortal_death_mark', 3)
                    pet.is_alive = True   # 暂时保持存活标记
                    pet.current_hp = 1    # 以1HP维持

        # ════════════════════════════════════════════════════════
        # 离场时：木桶戏法
        # ════════════════════════════════════════════════════════

        elif trait_name == "木桶戏法" and context == "switch_out":
            # 离场后，更换入场的精灵以"木桶状态"登场（双防+50%，速度-50%近似）
            own_state = state.player if is_player else state.opponent
            own_state.team_state.next_pet_gifts.add('双防+5')
            own_state.team_state.next_pet_gifts.add('速度-5')

        # ════════════════════════════════════════════════════════
        # 使用技能后：系统发育、倾轧、威慑
        # ════════════════════════════════════════════════════════

        elif trait_name == "系统发育" and context == "skill_use" and skill:
            # 获得能量或生命时，会将等量分配给场下的精灵
            # 近似：使用有治疗效果的技能后，将10%生命分配给1只存活队友
            from core.models import EffectType, SkillCategory
            own_state = state.player if is_player else state.opponent
            has_heal = any(e.type == EffectType.HEAL for e in skill.effects)
            has_energy = any(e.type == EffectType.ENERGY_RESTORE and e.target == 'self'
                             for e in skill.effects)
            if has_heal or has_energy:
                bench = [p for p in own_state.team
                         if p.is_alive and p is not pet]
                if bench:
                    import random
                    target_pet = random.choice(bench)
                    if has_heal:
                        heal = int(pet.max_hp * 0.1)
                        target_pet.current_hp = min(target_pet.max_hp, target_pet.current_hp + heal)
                    if has_energy:
                        target_pet.current_energy = min(10, target_pet.current_energy + 1)

        elif trait_name == "倾轧" and context == "skill_use" and skill:
            # 携带的技能受能耗变化效果的影响翻倍（近似：若有 energy_cost_permanent 效果则翻倍）
            from core.models import EffectType
            for eff in skill.effects:
                if eff.type == EffectType.ENERGY_RESTORE and 'energy_cost_permanent' in (eff.desc or ''):
                    # 额外再执行一次能耗变化
                    for sk in pet.skills:
                        if eff.desc == 'energy_cost_permanent_self':
                            SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, int(eff.value))
                        elif eff.desc == 'energy_cost_permanent':
                            SlotEffectsProcessor.apply_energy_cost_delta(pet, sk, int(eff.value))

        elif trait_name == "威慑" and context == "skill_use" and target and skill:
            # 打断敌方时（应对成功后），被打断的技能进入2回合冷却
            # 近似：若应对成功（counter_success），则给对方当前技能2回合冷却
            if pet.get_runtime_flag('_just_countered', False):
                pet.set_runtime_flag('_just_countered', False)
                if target and hasattr(target, 'skill_cooldowns'):
                    current_skill = target.get_runtime_flag('_current_skill_name', None)
                    if current_skill:
                        target.skill_cooldowns[current_skill] = 2

        # ════════════════════════════════════════════════════════
        # 回合结束：对流
        # ════════════════════════════════════════════════════════

        elif trait_name == "贪心算法" and context == "skill_use" and target:
            # 1号位技能获得传动1，且使用后使敌方获得6层灼烧
            greedy_skill = pet.get_runtime_flag("_slot_trait_greedy_skill", None)
            if skill is not None and greedy_skill == skill.name:
                target.add_status(StatusEffectType.BURN, 6)

        elif trait_name == "对流" and context == "end_of_turn":
            # 自己的能耗增加变为能耗降低；能耗降低变为能耗增加
            # 近似：每回合检查能耗变化方向并反转（对所有技能能耗做镜像处理）
            # 实现：记录初始能耗，若当前能耗高于初始则降低，反之亦然
            # 由于引擎无法追踪"变化方向"，此处做简化：每回合随机反转能耗delta
            pass  # 此特性依赖"能耗变化事件"，当前无法精确实现，跳过
