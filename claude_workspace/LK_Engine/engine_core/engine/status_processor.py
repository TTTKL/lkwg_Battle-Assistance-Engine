"""
状态处理引擎
处理中毒、灼烧、冻结、印记等状态效果的触发和结算
状态现在直接存储在 PetInstance 上（status_effects 字典）
"""
from core.status_effects import StatusEffectType
from core.models import PetInstance, BattleState, FieldMark
from data_loader import DataLoader
from engine.slot_effects import SlotEffectsProcessor


class StatusProcessor:
    """状态处理器"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    # ── 回合结束效果 ─────────────────────────────────────────────

    def process_end_of_turn_effects(
        self,
        pet: PetInstance,
        opponent_pet: PetInstance,
        is_player: bool,
        state: BattleState
    ) -> int:
        """处理回合结束时的状态效果，返回造成的总伤害"""
        total_damage = 0

        # 1. 中毒：每层3%最大生命值毒系伤害，毒系免疫
        poison_stacks = pet.get_status_stacks(StatusEffectType.POISON)
        if poison_stacks > 0:
            if '毒' not in pet.template.types:
                dmg = int(pet.max_hp * 0.03 * poison_stacks)
                eff = self._calc_effectiveness('毒', pet)
                dmg = int(dmg * eff)
                pet.current_hp = max(0, pet.current_hp - dmg)
                total_damage += dmg

        # 2. 中毒印记：每层3%最大生命值毒系伤害，对所有系有效
        pm_stacks = pet.get_status_stacks(StatusEffectType.POISON_MARK)
        if pm_stacks > 0:
            dmg = int(pet.max_hp * 0.03 * pm_stacks)
            eff = self._calc_effectiveness('毒', pet)
            dmg = int(dmg * eff)
            pet.current_hp = max(0, pet.current_hp - dmg)
            total_damage += dmg

        # 3. 灼烧：每层2%最大生命火系伤害，火系免疫，每回合衰减一半（最少1层）
        burn_stacks = pet.get_status_stacks(StatusEffectType.BURN)
        if burn_stacks > 0 and '火' not in pet.template.types:
            dmg = int(pet.max_hp * 0.02 * burn_stacks)
            eff = self._calc_effectiveness('火', pet)
            dmg = int(dmg * eff)
            pet.current_hp = max(0, pet.current_hp - dmg)
            total_damage += dmg
            # 衰减
            decay = max(1, burn_stacks // 2)
            new_stacks = burn_stacks - decay
            if new_stacks <= 0:
                pet.remove_status(StatusEffectType.BURN)
            else:
                pet.status_effects[StatusEffectType.BURN] = new_stacks

        # 4. 寄生：每层吸取6%最大生命，并恢复对手等额血量
        parasite_stacks = pet.get_status_stacks(StatusEffectType.PARASITE)
        if parasite_stacks > 0:
            drain = int(pet.max_hp * 0.06 * parasite_stacks)
            pet.current_hp = max(0, pet.current_hp - drain)
            if opponent_pet and opponent_pet.is_alive:
                opponent_pet.current_hp = min(opponent_pet.max_hp, opponent_pet.current_hp + drain)
            total_damage += drain

        # 5. 光合印记：回合结束获得1能量
        pos_mark, _ = state.get_marks(is_player)
        if pos_mark and pos_mark.type_key == StatusEffectType.PHOTOSYNTHESIS_MARK.value:
            pet.current_energy = min(10, pet.current_energy + 1)

        # 检查力竭
        if pet.current_hp <= 0:
            pet.is_alive = False

        return total_damage

    def _calc_effectiveness(self, element: str, pet: PetInstance) -> float:
        return self.data_loader.get_combined_type_effectiveness(element, pet.template.types)

    # ── 冻结致死 ─────────────────────────────────────────────────

    def check_freeze_death(self, pet: PetInstance) -> bool:
        """每层冻结占5%最大生命；当前HP≤冻结HP时力竭"""
        stacks = pet.freeze_stacks
        if stacks > 0:
            frozen_hp = int(pet.max_hp * 0.05 * stacks)
            if pet.current_hp <= frozen_hp:
                pet.current_hp = 0
                pet.is_alive = False
                return True
        return False

    # ── 入场印记效果 ─────────────────────────────────────────────

    def apply_field_mark_on_enter(
        self,
        pet: PetInstance,
        is_player: bool,
        state: BattleState
    ):
        """精灵入场时应用场地印记效果"""
        _, neg_mark = state.get_marks(is_player)

        if neg_mark:
            key = neg_mark.type_key
            stacks = neg_mark.stacks

            # 降灵印记：入场时每层失去1能量
            if key == StatusEffectType.DESCENT_MARK.value:
                pet.current_energy = max(0, pet.current_energy - stacks)

            # 棘刺：入场时每层造成6%最大生命伤害
            elif key == StatusEffectType.THORN.value:
                dmg = int(pet.max_hp * 0.06 * stacks)
                pet.current_hp = max(0, pet.current_hp - dmg)
                if pet.current_hp == 0:
                    pet.is_alive = False

            # 凝霜（减速）印记：速度-10固定值（wiki: 速度-10，非层数debuff）
            elif key == StatusEffectType.FROST_MARK.value:
                pet.stats["速度"] = max(1, pet.stats.get("速度", 100) - 10 * stacks)

        # 设置迸发状态（入场首回合）
        pet.burst_turns_remaining = 1
        pet.just_entered = True

    # ── 星陨印记引爆 ─────────────────────────────────────────────

    def trigger_star_fall_mark(
        self,
        defender: PetInstance,
        attacker: PetInstance,
        damage_element: str,
        is_player_defender: bool,
        state: BattleState
    ) -> int:
        """
        触发星陨印记（wiki: 造成伤害后消除所有层数，每层造成30威力的魔法伤害）
        注意：wiki描述为"造成伤害后触发"，即任何攻击伤害都会触发，不限属性。
        返回额外伤害。
        """
        _, neg_mark = state.get_marks(is_player_defender)
        if neg_mark and neg_mark.type_key == StatusEffectType.STAR_FALL_MARK.value:
            stacks = neg_mark.stacks
            # 每层30威力的魔法伤害，受幻系属性克制影响
            base_power = 30 * stacks
            # 使用攻击者魔攻 vs 防御者魔防计算（魔法伤害）
            mag_atk = attacker.get_effective_stat('魔攻')
            mag_def = defender.get_effective_stat('魔防')
            base_damage = (mag_atk / max(1, mag_def)) * 0.9 * base_power
            # 幻系属性克制
            eff = self.data_loader.get_combined_type_effectiveness('幻', defender.template.types)
            extra = max(1, int(base_damage * eff))

            # 守望星：消耗一半层数，仍造成满层伤害
            has_watch_star = any(t.name == "守望星" for t in defender.template.traits)
            if has_watch_star:
                consumed = max(1, stacks // 2)
                neg_mark.stacks -= consumed
                if neg_mark.stacks <= 0:
                    if is_player_defender:
                        state.player_negative_mark = None
                    else:
                        state.opponent_negative_mark = None
            else:
                # 清空印记
                if is_player_defender:
                    state.player_negative_mark = None
                else:
                    state.opponent_negative_mark = None

            return extra
        return 0

    # ── 奉献效果 ─────────────────────────────────────────────────

    def apply_devotion_to_skill(self, skill_name: str, base_power: int,
                                 base_energy: int, team_state):
        """应用奉献效果到啃咬/虫群技能，返回 (power, energy, combo, lifesteal)"""
        if skill_name not in ['啃咬', '虫群']:
            return base_power, base_energy, 0, 0
        power = base_power + team_state.devotion_power
        energy = max(0, base_energy - team_state.devotion_energy)
        return power, energy, team_state.devotion_combo, team_state.devotion_lifesteal

    def get_devotion_impact_count(self, team_state) -> int:
        """统计技能会被多少次奉献效果影响。"""
        return (
            team_state.devotion_poison // 2
            + team_state.devotion_lifesteal // 10
            + team_state.devotion_combo
            + team_state.devotion_power // 20
            + team_state.devotion_energy // 2
        )

    # ── 技能位传动 ───────────────────────────────────────────────

    def process_skill_transmission(self, pet: PetInstance):
        """回合开始时处理技能位传动"""
        SlotEffectsProcessor.process_skill_transmission(pet)

    # ── 离场清除 ─────────────────────────────────────────────────

    def clear_buffs_on_switch(self, pet: PetInstance, keep_buffs: bool = False):
        """离场时清除状态（冻结保留）"""
        pet.clear_on_switch_out(keep_buffs=keep_buffs)
