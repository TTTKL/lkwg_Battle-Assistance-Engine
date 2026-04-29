"""
战斗引擎
集成状态效果、印记、应对系统、特性、技能效果等完整机制
所有扩展状态直接存储在 BattleState / PetInstance 上，支持正确的状态拷贝。
"""
from typing import Tuple, Optional, List
import copy

from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, FieldMark,
    DamageType, SkillCategory, EffectType, Effect
)
from core.status_effects import StatusEffectType
from engine.status_processor import StatusProcessor
from engine.mark_effects import MarkEffectsProcessor
from engine.trait_processor import TraitProcessor
from engine.slot_effects import SlotEffectsProcessor
from engine.end_turn import process_end_turn
from engine.action_phase import resolve_skill_phase
from engine.pre_action import prepare_actions_for_turn
from engine.skill_damage import resolve_skill_damage
from engine.energy_costs import (
    compute_effective_skill_energy_cost,
    get_runtime_skill_energy_delta,
)
from data_loader import DataLoader


class ExtendedBattleEngine:
    """扩展的战斗引擎"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.status_processor = StatusProcessor(data_loader)
        self.trait_processor = TraitProcessor()

    # ── 公开接口 ──────────────────────────────────────────────────

    def apply_action(
        self,
        state: BattleState,
        player_action: Action,
        opponent_action: Action
    ) -> BattleState:
        """应用双方行动，返回新状态（原状态不变）"""
        new_state = state.copy()
        player_action, opponent_action = prepare_actions_for_turn(
            new_state,
            player_action,
            opponent_action,
            self._process_turn_start_skill_position_changes,
            self._force_send_out_if_needed,
            self._expire_turn_limited_flags,
            self._switch_pet,
            self._gather_energy,
            self._apply_leader_evolution,
            self._apply_willpower_strike,
        )

        resolve_skill_phase(
            new_state,
            player_action,
            opponent_action,
            self._check_counter,
            self._force_send_out_if_needed,
            self._execute_skill,
            self._determine_order,
            self.trait_processor.trigger_on_counter_success,
        )

        # 处理折返（技能执行后离场）
        self._handle_pending_switch_out(new_state, True)
        self._handle_pending_switch_out(new_state, False)

        # 回合结束处理
        self._end_turn_processing(new_state)
        new_state.turn += 1
        new_state.turn_prepared = False

        # 50回合强制结束
        if new_state.turn >= new_state.max_turns:
            self._force_end_battle(new_state)

        return new_state

    def is_battle_over(self, state: BattleState) -> bool:
        return state.is_battle_over_by_hearts()

    def get_winner_by_hearts(self, state: BattleState) -> Optional[str]:
        return state.get_winner_by_hearts()

    # ── 内部：聚能 / 首领化 / 愿力冲击 ──────────────────────────

    def _gather_energy(self, player_state: PlayerState):
        pet = player_state.get_active_pet()
        if pet and pet.is_alive:
            pet.current_energy = min(10, pet.current_energy + 3)
            player_state.team_state.gather_energy_count += 1

    def _apply_leader_evolution(self, state: BattleState, is_player: bool):
        """首领化：消耗1次，出战精灵进入首领化状态（大幅强化）
        仅限首领血脉精灵使用。"""
        ps = state.player if is_player else state.opponent
        pet = ps.get_active_pet()
        if not pet or not pet.is_alive:
            return
        if getattr(pet.template, "bloodline", "unknown") != "leader":
            return
        if ps.team_state.leader_evolution_uses <= 0:
            return
        ps.team_state.leader_evolution_uses -= 1
        # 首领化效果：全属性+30%（3层buff）
        pet.stat_modifiers.physical_attack += 3
        pet.stat_modifiers.magical_attack += 3
        pet.stat_modifiers.physical_defense += 3
        pet.stat_modifiers.magical_defense += 3
        pet.stat_modifiers.speed += 3
        # 恢复血量（30%最大血量）
        pet.current_hp = min(pet.max_hp, pet.current_hp + int(pet.max_hp * 0.3))

    def _apply_willpower_strike(self, state: BattleState, is_player: bool, skill: Optional[Skill]):
        """愿力冲击：消耗1次，释放强化版技能
        首领血脉精灵不能使用愿力冲击。"""
        ps = state.player if is_player else state.opponent
        pet = ps.get_active_pet()
        if not pet or not pet.is_alive:
            return
        if getattr(pet.template, "bloodline", "unknown") == "leader":
            return
        if ps.team_state.willpower_strike_uses <= 0:
            return
        ps.team_state.willpower_strike_uses -= 1
        if skill:
            # 愿力冲击：威力+50%，同时按血脉属性结算
            boosted = Skill(
                name=skill.name + "（愿力）",
                element=skill.element,
                category=skill.category,
                damage_type=skill.damage_type,
                base_power=int(skill.base_power * 1.5),
                energy_cost=skill.energy_cost,
                hits=skill.hits,
                priority=skill.priority,
                effects=skill.effects,
                counters=skill.counters,
                cooldown=skill.cooldown,
            )
            original_payment_skill = skill.name
            attacker = (state.player if is_player else state.opponent).get_active_pet()
            previous_override = attacker.get_runtime_flag('_payment_skill_name_override', None) if attacker else None
            if attacker:
                attacker.set_runtime_flag('_payment_skill_name_override', original_payment_skill)
            try:
                self._execute_skill(state, is_player, boosted, False)
            finally:
                if attacker:
                    if previous_override is None:
                        attacker.pop_runtime_flag('_payment_skill_name_override', None)
                    else:
                        attacker.set_runtime_flag('_payment_skill_name_override', previous_override)

    # ── 内部：换精灵 ─────────────────────────────────────────────

    def _apply_entering_pet(
        self,
        state: BattleState,
        is_player: bool,
        target_index: int,
        inheritable_flags=None,
        count_as_switch: bool = True,
        allow_swift: bool = True,
    ) -> None:
        ps = state.player if is_player else state.opponent
        ps.active_index = target_index
        entering = ps.get_active_pet()
        if not entering:
            return
        if count_as_switch:
            ps.team_state.switch_count += 1
        SlotEffectsProcessor.restore_initial_skill_order(entering)
        self._apply_inheritable_flags(entering, inheritable_flags or {})
        self._handle_on_enter_skill_growth(entering)

        self.status_processor.apply_field_mark_on_enter(entering, is_player, state)
        self.trait_processor.apply_next_pet_gifts(entering, is_player, state)

        opponent_ps = state.opponent if is_player else state.player
        opp = opponent_ps.get_active_pet()
        self.trait_processor.trigger_on_enter(entering, opp, is_player, state)
        if entering.get_runtime_flag('_extend_burst', False):
            entering.burst_turns_remaining = max(entering.burst_turns_remaining, 2)

        suppress_swift = ps.team_state.suppress_next_pet_swift
        ps.team_state.suppress_next_pet_swift = False
        if allow_swift and not suppress_swift:
            for swift_skill in entering.skills:
                if any(e.type == EffectType.SWIFT for e in swift_skill.effects):
                    if (entering.current_energy >= swift_skill.energy_cost and
                            entering.skill_cooldowns.get(swift_skill.name, 0) <= 0):
                        self._execute_skill(state, is_player, swift_skill, False)
                        break

    def _switch_pet(self, state: BattleState, is_player: bool, target_index: int):
        ps = state.player if is_player else state.opponent
        if not (0 <= target_index < len(ps.team)):
            return
        if not ps.team[target_index].is_alive:
            return

        # 当前精灵离场：清除 buff/debuff（除非有翠顶/黑羽夫人特性）
        current = ps.get_active_pet()
        opponent_ps = state.opponent if is_player else state.player
        opp = opponent_ps.get_active_pet()
        inheritable_flags = self._extract_switch_out_inheritable_flags(current, opp)
        if current:
            self._handle_switch_out_skill_growth(current)
            keep_buffs = self.trait_processor.has_keep_buff_trait(current)
            self._clear_switch_out_runtime_flags(current)
            current.clear_on_switch_out(keep_buffs=keep_buffs)

            # 触发离场特性
            self.trait_processor.trigger_on_switch_out(current, opp, is_player, state)

        self._apply_entering_pet(
            state,
            is_player,
            target_index,
            inheritable_flags=inheritable_flags,
            count_as_switch=True,
            allow_swift=True,
        )

    def _force_send_out_if_needed(self, state: BattleState, is_player: bool, target_index: Optional[int]) -> None:
        if target_index is None:
            return
        ps = state.player if is_player else state.opponent
        current = ps.get_active_pet()
        if current and current.is_alive:
            return
        if not (0 <= target_index < len(ps.team)):
            return
        if not ps.team[target_index].is_alive:
            return

        # 力竭后的补位不算“主动换宠”，因此：
        # 1. 不触发离场特性 / 不走 switch_out 清场
        # 2. 不计 switched_this_turn / switch_count
        # 3. 不触发迅捷
        ps.team_state.suppress_next_pet_swift = False
        self._apply_entering_pet(
            state,
            is_player,
            target_index,
            inheritable_flags={},
            count_as_switch=False,
            allow_swift=False,
        )

    def _handle_pending_switch_out(self, state: BattleState, is_player: bool):
        """处理折返/紧急脱离：技能打完后自动换下一只存活精灵"""
        ps = state.player if is_player else state.opponent
        pet = ps.get_active_pet()
        if pet and pet.pending_switch_out and pet.is_alive:
            alive = [(i, p) for i, p in enumerate(ps.team) if p.is_alive and i != ps.active_index]
            if alive:
                self._switch_pet(state, is_player, alive[0][0])

    # ── 内部：先手判定 ───────────────────────────────────────────

    def _check_counter(self, my_skill: Skill, opponent_skill: Skill) -> bool:
        if not my_skill or not my_skill.counters:
            return False
        return opponent_skill.category.value in my_skill.counters

    def _determine_order(
        self,
        player_pet: PetInstance,
        opponent_pet: PetInstance,
        player_skill: Skill,
        opponent_skill: Skill
    ) -> Tuple[str, str]:
        # 技能优先级 + 精灵 priority_bonus（迅捷效果）
        p_priority = player_skill.priority + self._get_effective_priority_bonus_for_skill(player_pet)
        o_priority = opponent_skill.priority + self._get_effective_priority_bonus_for_skill(opponent_pet)

        if p_priority > o_priority:
            return ("player", "opponent")
        elif o_priority > p_priority:
            return ("opponent", "player")

        p_speed = player_pet.get_effective_stat("速度")
        o_speed = opponent_pet.get_effective_stat("速度")
        if p_speed > o_speed:
            return ("player", "opponent")
        elif o_speed > p_speed:
            return ("opponent", "player")
        # 同速时确定性打破平局：基于精灵 ID + 当前回合的哈希
        # 在搜索树中保证确定性；在模拟中跨回合交替先手
        p_hash = hash((player_pet.template.id, player_pet.template.name))
        o_hash = hash((opponent_pet.template.id, opponent_pet.template.name))
        if p_hash != o_hash:
            return ("player", "opponent") if p_hash > o_hash else ("opponent", "player")
        return ("player", "opponent")

    # ── 内部：技能执行 ───────────────────────────────────────────

    def _execute_skill(
        self,
        state: BattleState,
        is_player: bool,
        skill: Skill,
        counter_success: bool
    ):
        attacker = (state.player if is_player else state.opponent).get_active_pet()
        defender = (state.opponent if is_player else state.player).get_active_pet()
        if not attacker or not defender or not attacker.is_alive:
            return
        if attacker.get_runtime_flag('_skip_skill_this_turn', False):
            attacker.pop_runtime_flag('_skip_skill_this_turn', None)
            return
        allowed_slots = SlotEffectsProcessor.get_allowed_skill_slots(attacker)
        if allowed_slots is not None:
            slot_index = SlotEffectsProcessor.get_skill_slot_index(attacker, skill)
            if slot_index not in allowed_slots:
                return

        payment_skill_name, payment_skill = self._get_payment_skill(attacker, skill)

        borrowed_skill = self._resolve_borrowed_skill(state, is_player, attacker, skill)
        if borrowed_skill is not None:
            skill = borrowed_skill

        transformed_skill = self._resolve_transform_skill(state, is_player, attacker, skill)
        if transformed_skill is not None:
            skill = transformed_skill
        skill = self._resolve_dynamic_skill_effects(attacker, skill)

        if skill.name == '荟萃':
            self._execute_all_normal_skills(state, is_player, attacker)
            return
        if skill.name == '疾风连袭':
            self._execute_gale_combo(state, is_player, attacker)
            return

        # 检查蓄力
        if self._handle_charge(state, is_player, attacker, skill):
            return  # 本回合是蓄力回合，不实际释放

        # 记录当前执行的技能名（供应对能耗永久降低效果使用）
        attacker.set_runtime_flag('_current_skill_name', payment_skill_name)
        attacker.set_runtime_flag('_last_attack_super_effective', False)
        explicit_swift_skill = any(e.type == EffectType.SWIFT for e in skill.effects)
        burst_active_for_skill = any(e.type == EffectType.BURST for e in skill.effects) and attacker.burst_turns_remaining > 0

        # 快锤/暴食/飓风：特定系别技能获得迅捷（临时提升先手加成）
        skill_type = getattr(skill, 'element', None)
        skill_cost = getattr(payment_skill, 'energy_cost', getattr(skill, 'energy_cost', 0))
        if attacker.get_runtime_flag('_swift_low_cost', False) and skill_cost < 3:
            attacker.priority_bonus += 1
        if attacker.get_runtime_flag('_swift_dragon', False) and skill_type == '龙':
            attacker.priority_bonus += 1
        if attacker.get_runtime_flag('_hurricane_swift', False):
            attacker.priority_bonus += 1
        if SlotEffectsProcessor.is_trait_slot_swift(attacker, skill):
            attacker.priority_bonus += 1

        # 应用印记对技能的修改
        modified_energy = compute_effective_skill_energy_cost(
            state,
            is_player,
            attacker,
            payment_skill,
            counter_success=counter_success,
            include_forced_runtime=True,
        )
        setattr(skill, 'effective_energy_cost', modified_energy)
        setattr(payment_skill, 'effective_energy_cost', modified_energy)
        modified_power, _ = MarkEffectsProcessor.apply_mark_effects_to_skill(
            skill, attacker, is_player, counter_success, state
        )

        # DYNAMIC_POWER：威力计算
        for eff in skill.effects:
            if eff.type == EffectType.DYNAMIC_POWER:
                if eff.desc == 'sum_enemy_energy_cost':
                    # 冰锋横扫：威力=敌方技能总能耗×10
                    total_cost = sum(sk.energy_cost for sk in defender.skills)
                    modified_power = total_cost * int(eff.value)  # value=10
                elif eff.desc == 'consume_all_energy':
                    # 消耗全部能量型
                    modified_power = skill.base_power * max(1, attacker.current_energy)
                else:
                    modified_power = skill.base_power * max(1, attacker.current_energy)
                break

        ignore_external_modifiers = (skill.name == '水星水' and counter_success)
        if not ignore_external_modifiers:
            modified_power = SlotEffectsProcessor.get_skill_power(modified_power, attacker, skill)

        if skill.name == '怨力打击':
            charged_hit_power = attacker.pop_runtime_flag('_charged_hit_power', 0)
            if charged_hit_power > 0:
                modified_power = max(modified_power, int(charged_hit_power))

        if skill.name == '漫反射':
            first_by_element = {}
            for own_skill in attacker.skills:
                first_by_element.setdefault(own_skill.element, own_skill.name)
            if first_by_element.get(skill.element) == skill.name:
                modified_power += 35
        if skill.name == '雷暴' and burst_active_for_skill:
            previous_burst_names = attacker.get_runtime_flag('_burst_triggered_skill_names_order', [])
            unique_names = self._get_unique_replayable_burst_names(previous_burst_names)
            modified_power += 10 * len(unique_names)
            modified_energy += len(unique_names)

        # 奉献：强化啃咬/虫群类技能
        team_state = (state.player if is_player else state.opponent).team_state
        devotion_combo_bonus = 0
        devotion_lifesteal_bonus = 0
        devotion_poison_bonus = 0
        devotion_impact_count = 0
        modified_power, modified_energy, devotion_combo_bonus, devotion_lifesteal_bonus = (
            self.status_processor.apply_devotion_to_skill(
                skill.name, modified_power, modified_energy, team_state
            )
        )
        if skill.name in ['啃咬', '虫群']:
            devotion_poison_bonus = team_state.devotion_poison
            devotion_impact_count = self.status_processor.get_devotion_impact_count(team_state)

        # 体重技能：以重制重、吨位压制、砂糖弹球（基于精灵体重的动态威力）
        if skill.name in ('以重制重', '吨位压制', '砂糖弹球'):
            atk_w = getattr(attacker.template, 'weight_kg', 0.0) or 30.0  # 默认30KG
            def_w = getattr(defender.template, 'weight_kg', 0.0) or 30.0
            if skill.name == '以重制重':
                # 敌方体重越高，威力越高；上限120
                modified_power = max(40, min(120, int(def_w * 1.0)))
            elif skill.name == '吨位压制':
                # 敌方体重越低，威力越高；最大120
                modified_power = max(40, min(120, int(120 - def_w * 0.5)))
            elif skill.name == '砂糖弹球':
                # 双方体重差越大，威力越高
                modified_power = max(40, min(120, int(abs(atk_w - def_w) * 1.0)))

        # 蓄水：能耗折扣
        if SlotEffectsProcessor.get_next_skill_energy_delta(attacker) != 0:
            attacker.next_skill_energy_discount = 0

        # 暴风眼/热身运动：连击加成（在 _compute_total_hits 前设置）
        if getattr(attacker, 'storm_eye_active', False):
            attacker.storm_eye_active = False
            attacker.warmup_hits_bonus = getattr(attacker, 'warmup_hits_bonus', 0) + max(1, skill.hits)
        # warmup_hits_bonus 在 _compute_total_hits 中消费

        # POWER_BONUS：条件威力加成（加法/乘法）
        # 条件文本存于技能描述中，当前统一将条件加成纳入计算（近似处理）
        for eff in skill.effects:
            if eff.type == EffectType.POWER_BONUS:
                if eff.desc == 'multiply':
                    # value 存为 倍率×100，如 value=200 表示2倍
                    multiplier = eff.value / 100
                    modified_power = int(modified_power * multiplier)
                else:
                    # 加法型：直接加到威力
                    modified_power += int(eff.value)

        if skill.base_power > 0 and skill.damage_type:
            modified_power += attacker.get_runtime_flag('_next_attack_power_bonus_flat', 0)
            modified_power = int(modified_power * attacker.get_runtime_flag('_next_attack_power_multiplier', 1.0))

        # 扣除能量（石头大餐：能量不足时消耗5%生命代替1能量）
        if attacker.current_energy < modified_energy:
            if any(t.name == "石头大餐" for t in attacker.template.traits):
                shortfall = modified_energy - attacker.current_energy
                cost_hp = int(attacker.max_hp * 0.05 * shortfall)
                if attacker.current_hp > cost_hp:
                    attacker.current_hp -= cost_hp
                    attacker.current_energy = min(attacker.current_energy + shortfall, 10)
            if attacker.current_energy < modified_energy:
                return
        attacker.current_energy = max(0, attacker.current_energy - modified_energy)

        # 设置冷却
        if getattr(payment_skill, 'cooldown', 0) > 0:
            attacker.skill_cooldowns[payment_skill_name] = payment_skill.cooldown

        total_damage = resolve_skill_damage(
            state,
            is_player,
            attacker,
            defender,
            skill,
            modified_power,
            ignore_external_modifiers,
            devotion_combo_bonus,
            devotion_lifesteal_bonus,
            devotion_poison_bonus,
            devotion_impact_count,
            self.trait_processor,
            self.status_processor,
            self._compute_total_hits_with_defender,
            self._calculate_damage_with_power,
            self._apply_heal_or_reversed_damage,
        )

        # 死亡处理
        if not defender.is_alive:
            self.trait_processor.trigger_on_death(defender, attacker, not is_player, state)
            self.trait_processor.trigger_on_kill(attacker, defender, is_player, state)
            self._deduct_hearts(defender, not is_player, state)

        # 龙噬印记：释放5能耗技能后标记（威力已在 apply_mark_effects_to_skill 中提升），清除临时标记
        MarkEffectsProcessor.check_dragon_bite_trigger(skill, attacker, is_player, state)
        if hasattr(attacker, 'dragon_bite_active'):
            attacker.dragon_bite_active = False

        # 应用技能效果（buff/debuff、状态、治疗、离场等）
        self._apply_skill_effects(state, is_player, attacker, defender, skill, counter_success, total_damage)

        if skill.name == '彗星' and attacker.is_alive:
            attacker.current_hp = 0

        self._handle_post_use_skill_growth(state, is_player, attacker, skill, counter_success)
        if not defender.is_alive:
            self._handle_kill_skill_growth(attacker)
        if counter_success:
            self._handle_counter_success_skill_growth(attacker)

        if explicit_swift_skill:
            history = list(attacker.get_runtime_flag('_swift_triggered_skill_names_order', []))
            history.append(skill.name)
            attacker.set_runtime_flag('_swift_triggered_skill_names_order', history)
        if burst_active_for_skill:
            history = list(attacker.get_runtime_flag('_burst_triggered_skill_names_order', []))
            history.append(skill.name)
            attacker.set_runtime_flag('_burst_triggered_skill_names_order', history)
            if skill.name == '雷暴':
                self._apply_raiden_storm_extra_burst_effects(state, is_player, attacker, defender, counter_success)

        self._process_post_effect_knockout(defender, attacker, not is_player, state)
        self._process_post_effect_knockout(attacker, None, is_player, state)

        # 使用技能后特性触发（助燃/爆燃/氧循环/浸润/碰瓷等）
        self.trait_processor.trigger_on_skill_use(attacker, defender, skill, is_player, state)

        # 更新己方技能类别使用计数（供入场积累型特性使用）
        self._update_skill_type_count(state, is_player, skill)
        self._consume_post_skill_flags(attacker, skill)

    def _compute_total_hits(self, skill: Skill, attacker: Optional[PetInstance] = None) -> int:
        total = skill.hits
        for eff in skill.effects:
            if eff.type == EffectType.EXTRA_HITS:
                total += int(eff.value)
        if attacker is not None:
            total += SlotEffectsProcessor.get_skill_hits_delta(attacker, skill)
            # 应对"本技能变为N连击"效果
            extra = getattr(attacker, 'counter_extra_hits', 0)
            if extra > 0:
                total = extra
                attacker.counter_extra_hits = 0
            # 热身运动/暴风眼：连击加成
            warmup = getattr(attacker, 'warmup_hits_bonus', 0)
            if warmup != 0:
                total += warmup
                attacker.warmup_hits_bonus = 0
            overload_bonus = attacker.get_runtime_flag('_overload_circuit_bonus_hits', 0)
            overload_bonus_turn = attacker.get_runtime_flag('_overload_circuit_bonus_turn', None)
            if overload_bonus > 0 and overload_bonus_turn is not None:
                total += overload_bonus
                attacker.pop_runtime_flag('_overload_circuit_bonus_hits', None)
                attacker.pop_runtime_flag('_overload_circuit_bonus_turn', None)
            # 自由飘/侵蚀：被动连击加成（需要 defender 参数）
        return max(1, total)

    def _resolve_borrowed_skill(
        self,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        skill: Skill,
    ) -> Optional[Skill]:
        """借用：确定性地借用队友的一个非借用技能。"""
        if skill.name != '借用':
            return None

        ps = state.player if is_player else state.opponent
        candidates = []
        for idx, pet in enumerate(ps.team):
            if idx == ps.active_index or not pet.is_alive:
                continue
            for teammate_skill in pet.skills:
                if teammate_skill.name != '借用':
                    candidates.append(teammate_skill)

        if not candidates:
            return None

        seed = state.turn + sum(ord(ch) for ch in attacker.template.name)
        chosen = candidates[seed % len(candidates)]
        attacker.set_runtime_flag('_borrowed_skill_name', chosen.name)
        return copy.deepcopy(chosen)

    def _resolve_transform_skill(
        self,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        skill: Skill,
    ) -> Optional[Skill]:
        if skill.name == '取念':
            opponent_ps = state.opponent if is_player else state.player
            candidates = []
            for pet in opponent_ps.team:
                for candidate_skill in pet.skills:
                    if candidate_skill.name != '取念':
                        candidates.append(candidate_skill.name)
            if not candidates:
                return None
            seed = state.turn + sum(ord(ch) for ch in attacker.template.name)
            chosen_name = sorted(candidates)[seed % len(candidates)]
            chosen_skill = self.data_loader.skills.get(chosen_name)
            if chosen_skill is None:
                chosen_skill = next((copy.deepcopy(sk) for pet in opponent_ps.team for sk in pet.skills if sk.name == chosen_name), None)
            else:
                chosen_skill = copy.deepcopy(chosen_skill)
            if chosen_skill is None:
                return None
            chosen_skill.energy_cost = max(0, chosen_skill.energy_cost - 2)
            attacker.set_runtime_flag('_copied_skill_name', chosen_skill.name)
            return chosen_skill

        if skill.name == '复写':
            carried_names = {sk.name for sk in attacker.skills}
            candidates = [
                name for name in attacker.template.learnable_skills
                if name not in carried_names and name in self.data_loader.skills
            ]
            if not candidates:
                return None
            seed = state.turn + sum(ord(ch) for ch in attacker.template.name)
            chosen_name = sorted(candidates)[seed % len(candidates)]
            chosen_skill = copy.deepcopy(self.data_loader.skills[chosen_name])
            chosen_skill.energy_cost = max(0, chosen_skill.energy_cost - 2)
            attacker.set_runtime_flag('_copied_skill_name', chosen_skill.name)
            return chosen_skill

        return None

    def _resolve_dynamic_skill_effects(
        self,
        attacker: PetInstance,
        skill: Skill,
    ) -> Skill:
        """按当前携带技能动态重建特定技能的效果列表。"""
        if skill.name != '折射':
            return skill

        resolved = copy.deepcopy(skill)
        carried_elements = {
            own_skill.element
            for own_skill in attacker.skills
            if own_skill.name != skill.name and own_skill.element
        }
        effects: List[Effect] = []

        if '普通' in carried_elements:
            effects.append(Effect(EffectType.POWER_BONUS, 'opponent', 20))
        if '翼' in carried_elements:
            effects.append(Effect(EffectType.EXTRA_HITS, 'self', 1))
        if '恶' in carried_elements:
            effects.append(Effect(EffectType.LIFESTEAL, 'self', 0.3))
        if '水' in carried_elements:
            effects.append(Effect(EffectType.ENERGY_RESTORE, 'self', -1, desc='energy_cost_permanent'))
        if '草' in carried_elements:
            effects.append(Effect(EffectType.HEAL, 'self', 0.15))
        if '电' in carried_elements:
            effects.append(Effect(EffectType.STAT_BUFF, 'self', 50, desc='速度_flat'))
        if '武' in carried_elements:
            effects.append(Effect(EffectType.STAT_BUFF, 'self', 4, desc='物攻'))
        if '光' in carried_elements:
            effects.append(Effect(EffectType.STAT_BUFF, 'self', 4, desc='魔攻'))
        if '机械' in carried_elements:
            effects.append(Effect(EffectType.STAT_BUFF, 'self', 3, desc='物防'))
            effects.append(Effect(EffectType.STAT_BUFF, 'self', 3, desc='魔防'))

        if '火' in carried_elements:
            effects.append(Effect(EffectType.APPLY_STATUS, 'opponent', 4, status_type='burn', stacks=4))
        if '冰' in carried_elements:
            effects.append(Effect(EffectType.APPLY_STATUS, 'opponent', 2, status_type='freeze', stacks=2))
        if '毒' in carried_elements:
            effects.append(Effect(EffectType.APPLY_STATUS, 'opponent', 2, status_type='poison', stacks=2))
        if '幻' in carried_elements:
            effects.append(
                Effect(
                    EffectType.APPLY_MARK,
                    'opponent',
                    -1,
                    status_type=StatusEffectType.STAR_FALL_MARK.value,
                    stacks=1,
                )
            )
        if '幽' in carried_elements:
            effects.append(Effect(EffectType.ENERGY_RESTORE, 'opponent', -2))
        if '地' in carried_elements:
            effects.append(Effect(EffectType.STAT_DEBUFF, 'opponent', 40, desc='速度_flat'))
            effects.append(Effect(EffectType.ENERGY_RESTORE, 'opponent', 0, desc='hits_debuff:2'))
        if '虫' in carried_elements:
            effects.append(Effect(EffectType.STAT_DEBUFF, 'opponent', 4, desc='物防'))
        if '龙' in carried_elements:
            effects.append(Effect(EffectType.STAT_DEBUFF, 'opponent', 4, desc='魔防'))
        if '萌' in carried_elements:
            effects.append(Effect(EffectType.STAT_DEBUFF, 'opponent', 3, desc='物攻'))
            effects.append(Effect(EffectType.STAT_DEBUFF, 'opponent', 3, desc='魔攻'))

        resolved.effects = effects
        return resolved

    def _compute_modified_skill_energy(
        self,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        skill: Skill,
        counter_success: bool = False,
        extra_multiplier: int = 1,
    ) -> int:
        return compute_effective_skill_energy_cost(
            state,
            is_player,
            attacker,
            skill,
            counter_success=counter_success,
            extra_multiplier=extra_multiplier,
        )

    def _execute_all_normal_skills(self, state: BattleState, is_player: bool, attacker: PetInstance) -> None:
        normal_skills = [
            sk for sk in attacker.skills
            if sk.element == '普通' and sk.name != '荟萃'
        ]
        for normal_skill in normal_skills:
            cost = self._compute_modified_skill_energy(
                state, is_player, attacker, normal_skill, counter_success=False, extra_multiplier=2
            )
            if attacker.current_energy < cost:
                continue
            original_multiplier = attacker.get_runtime_flag('_forced_energy_multiplier', None)
            attacker.set_runtime_flag('_forced_energy_multiplier', 2)
            try:
                self._execute_skill(state, is_player, copy.deepcopy(normal_skill), False)
            finally:
                if original_multiplier is None:
                    attacker.pop_runtime_flag('_forced_energy_multiplier', None)
                else:
                    attacker.set_runtime_flag('_forced_energy_multiplier', original_multiplier)

    def _execute_gale_combo(self, state: BattleState, is_player: bool, attacker: PetInstance) -> None:
        swift_history = attacker.get_runtime_flag('_swift_triggered_skill_names_order', [])
        if not swift_history:
            return
        triggered_names = set(swift_history)
        swift_skills = [
            sk for sk in attacker.skills
            if any(e.type == EffectType.SWIFT for e in sk.effects) and sk.name in triggered_names
        ]
        if not swift_skills:
            return

        extra_cost = sum(sk.energy_cost for sk in swift_skills) // 2
        combo_skill = self._get_owned_skill(attacker, '疾风连袭')
        if combo_skill is None:
            return
        original_multiplier = attacker.get_runtime_flag('_forced_energy_multiplier', None)
        original_flat = attacker.get_runtime_flag('_forced_flat_energy_delta', None)
        attacker.set_runtime_flag('_forced_flat_energy_delta', extra_cost)
        try:
            # 支付疾风连袭自身能耗
            temp_skill = copy.deepcopy(combo_skill)
            temp_skill.name = '疾风连袭（能耗）'
            temp_skill.base_power = 0
            temp_skill.damage_type = None
            temp_skill.effects = []
            previous_override = attacker.get_runtime_flag('_payment_skill_name_override', None)
            attacker.set_runtime_flag('_payment_skill_name_override', combo_skill.name)
            try:
                self._execute_skill(state, is_player, temp_skill, False)
            finally:
                if previous_override is None:
                    attacker.pop_runtime_flag('_payment_skill_name_override', None)
                else:
                    attacker.set_runtime_flag('_payment_skill_name_override', previous_override)
        finally:
            if original_flat is None:
                attacker.pop_runtime_flag('_forced_flat_energy_delta', None)
            else:
                attacker.set_runtime_flag('_forced_flat_energy_delta', original_flat)
            if original_multiplier is None:
                attacker.pop_runtime_flag('_forced_energy_multiplier', None)
            else:
                attacker.set_runtime_flag('_forced_energy_multiplier', original_multiplier)

        for swift_skill in swift_skills:
            self._execute_skill(state, is_player, copy.deepcopy(swift_skill), False)
        combo_skill.energy_cost += 1

    @staticmethod
    def _get_unique_replayable_burst_names(burst_history: list) -> List[str]:
        unique_names = []
        for name in burst_history:
            if name != '雷暴' and name not in unique_names:
                unique_names.append(name)
        return unique_names

    def _apply_raiden_storm_extra_burst_effects(
        self,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        defender: PetInstance,
        counter_success: bool,
    ) -> None:
        burst_history = attacker.get_runtime_flag('_burst_triggered_skill_names_order', [])
        unique_names = self._get_unique_replayable_burst_names(burst_history)

        for burst_skill_name in unique_names:
            source_skill = self.data_loader.skills.get(burst_skill_name)
            if source_skill is None:
                continue
            replay_skill = copy.deepcopy(source_skill)
            replay_skill.energy_cost = 0
            replay_skill.cooldown = 0
            replay_skill.effects = [
                effect for effect in replay_skill.effects
                if effect.type not in (EffectType.BURST, EffectType.SWIFT)
            ]
            self._execute_skill(state, is_player, replay_skill, counter_success=False)

    def _compute_total_hits_with_defender(
        self, skill: Skill, attacker: Optional[PetInstance],
        defender: Optional[PetInstance] = None
    ) -> int:
        """含 defender 的版本，用于处理侵蚀/自由飘等被动连击特性"""
        total = self._compute_total_hits(skill, attacker)
        if attacker is not None:
            extra = self.trait_processor.get_extra_hits(attacker, skill, defender)
            total += extra
        return max(1, total)

    def _handle_charge(
        self, state: BattleState, is_player: bool,
        attacker: PetInstance, skill: Skill
    ) -> bool:
        """
        处理蓄力技能。
        如果技能有 CHARGE 效果且上回合没有蓄力，则本回合蓄力（返回 True）。
        如果上回合已蓄力此技能，则正常释放并重置（返回 False）。
        """
        has_charge_eff = any(e.type == EffectType.CHARGE for e in skill.effects)
        if not has_charge_eff:
            return False
        if attacker.charging_skill == skill.name:
            # 已蓄力，本回合释放（威力翻倍在 mark_effects 中处理）
            attacker.charging_skill = None
            return False
        else:
            # 开始蓄力
            attacker.charging_skill = skill.name
            return True

    # ── 内部：伤害计算 ───────────────────────────────────────────

    def _calculate_damage_with_power(
        self,
        attacker: PetInstance,
        defender: PetInstance,
        skill: Skill,
        state: BattleState,
        power: int,
        ignore_external_modifiers: bool = False,
    ) -> int:
        if skill.damage_type == DamageType.PHYSICAL:
            attack = attacker.stats["物攻"] if ignore_external_modifiers else attacker.get_effective_stat("物攻")
            defense = defender.stats["物防"] if ignore_external_modifiers else defender.get_effective_stat("物防")
        else:
            attack = attacker.stats["魔攻"] if ignore_external_modifiers else attacker.get_effective_stat("魔攻")
            defense = defender.stats["魔防"] if ignore_external_modifiers else defender.get_effective_stat("魔防")

        base_damage = (attack / max(1, defense)) * 0.9 * power
        stab = 1.5 if skill.element in attacker.template.types else 1.0

        type_effectiveness = self.data_loader.get_combined_type_effectiveness(
            skill.element,
            defender.template.types,
        )

        # ── 天气效果（wiki 确认）──────────────────────────────────────
        weather_bonus = 1.0
        weather = state.weather
        if not ignore_external_modifiers and weather == '下雨' and skill.element == '水':
            weather_bonus = 1.5   # 水系技能提升50%
        elif not ignore_external_modifiers and weather == '沙暴':
            pass  # 沙暴：地系技能能耗-2（在行动生成/技能执行时处理，不影响伤害）
        elif not ignore_external_modifiers and weather == '暴风雪':
            pass  # 暴风雪：每回合施加冰冻（在 _end_turn_processing 中处理）

        if type_effectiveness > 1.0:
            attacker.set_runtime_flag('_last_attack_super_effective', True)
        return max(1, int(base_damage * stab * type_effectiveness * weather_bonus))

    # ── 内部：技能效果系统 ───────────────────────────────────────

    def _apply_skill_effects(
        self,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        defender: PetInstance,
        skill: Skill,
        counter_success: bool,
        total_damage: int
    ):
        """应用技能的所有附加效果"""
        # 焚烧烙印预处理：记录驱散前的对手印记层数
        opp_is_player = not is_player
        pre_dispel_opp_marks = 0
        has_burn_per_mark = any(
            e.desc == 'burn_per_mark_dispelled' for e in skill.effects
        )
        if has_burn_per_mark:
            pos_m, neg_m = state.get_marks(opp_is_player)
            if pos_m:
                pre_dispel_opp_marks += pos_m.stacks
            if neg_m:
                pre_dispel_opp_marks += neg_m.stacks
            # 也计算自己的印记
            own_pos, own_neg = state.get_marks(is_player)
            if own_pos:
                pre_dispel_opp_marks += own_pos.stacks
            if own_neg:
                pre_dispel_opp_marks += own_neg.stacks

        for eff in skill.effects:
            target_pet = self._resolve_target(eff.target, attacker, defender)
            if target_pet is None:
                continue
            target_is_player = is_player if eff.target == "self" else not is_player

            # ── buff / debuff ─────────────────────────────────────
            if eff.type == EffectType.STAT_BUFF:
                slot_index = SlotEffectsProcessor.get_skill_slot_index(attacker, skill)
                matched, resolved_desc = self._slot_condition_matches(eff.desc, slot_index)
                if matched:
                    slot_eff = Effect(
                        type=eff.type,
                        target=eff.target,
                        value=eff.value,
                        conditional=eff.conditional,
                        desc=resolved_desc,
                    )
                    self._apply_stat_modifier(target_pet, slot_eff, positive=True)

            elif eff.type == EffectType.STAT_DEBUFF:
                slot_index = SlotEffectsProcessor.get_skill_slot_index(attacker, skill)
                matched, resolved_desc = self._slot_condition_matches(eff.desc, slot_index)
                if not matched:
                    continue
                eff = Effect(
                    type=eff.type,
                    target=eff.target,
                    value=eff.value,
                    conditional=eff.conditional,
                    desc=resolved_desc,
                )
                if eff.desc == 'double_debuff_stacks':
                    # 落井下毒：敌方减益层数翻倍
                    m = defender.stat_modifiers
                    if m.physical_attack < 0:
                        m.physical_attack *= 2
                    if m.magical_attack < 0:
                        m.magical_attack *= 2
                    if m.physical_defense < 0:
                        m.physical_defense *= 2
                    if m.magical_defense < 0:
                        m.magical_defense *= 2
                    if m.speed < 0:
                        m.speed *= 2
                elif eff.desc == 'poison_to_debuff':
                    # 腐化：敌方每有1层中毒，获得双攻-30%（约3层）
                    poison_stacks = defender.get_status_stacks(StatusEffectType.POISON)
                    if poison_stacks > 0:
                        debuff_layers = max(1, poison_stacks * 3 // 10)
                        defender.stat_modifiers.physical_attack -= debuff_layers
                        defender.stat_modifiers.magical_attack -= debuff_layers
                else:
                    self._apply_stat_modifier(target_pet, eff, positive=False)

            # ── 状态效果 ──────────────────────────────────────────
            elif eff.type == EffectType.APPLY_STATUS:
                # 眩晕单独处理（不用 StatusEffectType，直接用 stun_turns）
                if eff.status_type == 'stun':
                    target_pet.stun_turns += max(1, int(eff.stacks))
                else:
                    st = self._parse_status_type(eff.status_type)
                    if st is not None:
                        target_pet.add_status(st, eff.stacks)

            # ── 印记 ──────────────────────────────────────────────
            elif eff.type == EffectType.APPLY_MARK:
                st = self._parse_status_type(eff.status_type)
                if st is not None:
                    stacks = eff.stacks
                    if skill.name == '超新星馈赠' and st == StatusEffectType.STAR_FALL_MARK:
                        stacks += attacker.get_runtime_flag('_supernova_gift_bonus', 0)
                    mark = FieldMark(
                        type_key=st.value,
                        stacks=stacks,
                        is_positive=eff.value > 0  # value>0 正面，<0 负面
                    )
                    self._add_or_set_mark(state, target_is_player, mark.type_key, mark.stacks, mark.is_positive)

            # ── 治疗 ──────────────────────────────────────────────
            elif eff.type == EffectType.HEAL:
                if eff.desc == 'swap_hp_ratio':
                    # 恶念交换：与敌方交换生命比例
                    if attacker.max_hp > 0 and defender.max_hp > 0:
                        a_ratio = attacker.current_hp / attacker.max_hp
                        d_ratio = defender.current_hp / defender.max_hp
                        attacker.current_hp = max(1, int(attacker.max_hp * d_ratio))
                        defender.current_hp = max(1, int(defender.max_hp * a_ratio))
                else:
                    heal = int(target_pet.max_hp * eff.value)
                    self._apply_heal_or_reversed_damage(target_pet, heal)

            # ── 能量恢复 / 能耗永久变化 / 天气变更 / 特殊效果 ─────────
            elif eff.type == EffectType.ENERGY_RESTORE:
                if eff.desc == 'energy_cost_permanent':
                    # 永久改变全部技能能耗（赤子之心等）
                    delta = int(eff.value)
                    for sk in target_pet.skills:
                        SlotEffectsProcessor.apply_energy_cost_delta(target_pet, sk, delta)
                elif eff.desc == 'energy_cost_permanent_self':
                    # 永久改变当前执行的技能能耗（水炮/冲撞/重击等）
                    delta = int(eff.value)
                    sk_name = attacker.get_runtime_flag('_current_skill_name', None)
                    if sk_name:
                        for sk in attacker.skills:
                            if sk.name == sk_name:
                                SlotEffectsProcessor.apply_energy_cost_delta(attacker, sk, delta)
                                break
                elif eff.desc and eff.desc.startswith('set_weather:'):
                    weather_key = eff.desc.split(':', 1)[1]
                    weather_map = {'rain': '下雨', 'sandstorm': '沙暴', 'blizzard': '暴风雪'}
                    state.weather = weather_map.get(weather_key, weather_key)
                elif eff.desc == 'half_enemy_energy_cost':
                    # 雾气环绕：回复能量=敌方技能总能耗/2
                    total_cost = sum(sk.energy_cost for sk in defender.skills)
                    restore = max(1, total_cost // 2)
                    attacker.current_energy = min(10, attacker.current_energy + restore)
                elif eff.desc == 'convert_mark_to_burn':
                    # 炎爆术：将敌方印记转换为三倍灼烧
                    opp_is_player = not is_player
                    pos_mark, neg_mark = state.get_marks(opp_is_player)
                    total_stacks = 0
                    if pos_mark:
                        total_stacks += pos_mark.stacks
                    if neg_mark:
                        total_stacks += neg_mark.stacks
                    if total_stacks > 0:
                        burn_stacks = total_stacks * 3
                        defender.add_status(StatusEffectType.BURN, burn_stacks)
                        # 清除敌方印记
                        if opp_is_player:
                            state.player_positive_mark = None
                            state.player_negative_mark = None
                        else:
                            state.opponent_positive_mark = None
                            state.opponent_negative_mark = None
                elif eff.desc and eff.desc.startswith('hits_debuff:'):
                    # 耀眠/震击：减少敌方下回合技能连击数
                    penalty = int(eff.desc.split(':', 1)[1])
                    defender.warmup_hits_bonus = getattr(defender, 'warmup_hits_bonus', 0) - penalty
                elif eff.desc == 'storm_eye_buff':
                    # 暴风眼：自己获得连击数+100%（近似：下回合加倍连击）
                    attacker.storm_eye_active = True
                elif eff.desc == 'warmup_hits_bonus':
                    # 热身运动：自己获得连击数+3
                    attacker.warmup_hits_bonus = getattr(attacker, 'warmup_hits_bonus', 0) + 3
                elif eff.desc == 'next_skill_energy_discount':
                    # 蓄水：下次使用技能能耗-6
                    attacker.next_skill_energy_discount = 6
                elif eff.desc == 'swap_adjacent_skills':
                    SlotEffectsProcessor.swap_adjacent_skills(attacker, skill)
                elif eff.desc == 'adjacent_power_permanent':
                    SlotEffectsProcessor.adjust_adjacent_skill_power(attacker, skill, int(eff.value))
                elif eff.desc == 'grant_random_devotion':
                    team_state = (state.player if is_player else state.opponent).team_state
                    self.trait_processor.grant_random_devotion(
                        team_state,
                        int(eff.value),
                        f"skill:{skill.name}:{attacker.template.name}:{state.turn}"
                    )
                elif eff.desc and eff.desc.startswith('grant_specific_devotion:'):
                    team_state = (state.player if is_player else state.opponent).team_state
                    kind = eff.desc.split(':', 1)[1]
                    self.trait_processor.grant_specific_devotion(team_state, kind, int(eff.value))
                elif eff.desc == 'all_attack_energy_cost_up':
                    # 聒噪由 _handle_post_use_skill_growth 精确处理，这里避免重复近似结算。
                    pass
                elif eff.desc == 'swap_current_skills':
                    self._swap_selected_skills(attacker, defender)
                elif eff.desc.startswith('heal_to_damage:'):
                    multiplier = int(eff.desc.split(':', 1)[1])
                    target_pet.set_runtime_flag('_heal_to_damage_multiplier', multiplier)
                elif eff.desc == 'burn_per_mark_dispelled':
                    # 焚烧烙印：按驱散前的印记总数施加灼烧（5层/印记）
                    if pre_dispel_opp_marks > 0:
                        defender.add_status(StatusEffectType.BURN, pre_dispel_opp_marks * 5)
                else:
                    target_pet.current_energy = min(10, max(0, target_pet.current_energy + int(eff.value)))

            # ── 驱散 ──────────────────────────────────────────────
            elif eff.type == EffectType.DISPEL_BUFF:
                if eff.desc == 'swap_buffs_debuffs':
                    # 欺诈契约：与敌方交换增益和减益
                    am, dm = attacker.stat_modifiers, defender.stat_modifiers
                    am.physical_attack, dm.physical_attack = dm.physical_attack, am.physical_attack
                    am.magical_attack, dm.magical_attack = dm.magical_attack, am.magical_attack
                    am.physical_defense, dm.physical_defense = dm.physical_defense, am.physical_defense
                    am.magical_defense, dm.magical_defense = dm.magical_defense, am.magical_defense
                    am.speed, dm.speed = dm.speed, am.speed
                else:
                    target_pet.stat_modifiers.physical_attack = min(0, target_pet.stat_modifiers.physical_attack)
                    target_pet.stat_modifiers.magical_attack = min(0, target_pet.stat_modifiers.magical_attack)
                    target_pet.stat_modifiers.physical_defense = min(0, target_pet.stat_modifiers.physical_defense)
                    target_pet.stat_modifiers.magical_defense = min(0, target_pet.stat_modifiers.magical_defense)
                    target_pet.stat_modifiers.speed = min(0, target_pet.stat_modifiers.speed)

            elif eff.type == EffectType.DISPEL_DEBUFF:
                target_pet.stat_modifiers.physical_attack = max(0, target_pet.stat_modifiers.physical_attack)
                target_pet.stat_modifiers.magical_attack = max(0, target_pet.stat_modifiers.magical_attack)
                target_pet.stat_modifiers.physical_defense = max(0, target_pet.stat_modifiers.physical_defense)
                target_pet.stat_modifiers.magical_defense = max(0, target_pet.stat_modifiers.magical_defense)
                target_pet.stat_modifiers.speed = max(0, target_pet.stat_modifiers.speed)

            elif eff.type == EffectType.DISPEL_MARK:
                if target_is_player:
                    state.player_positive_mark = None
                    state.player_negative_mark = None
                else:
                    state.opponent_positive_mark = None
                    state.opponent_negative_mark = None

            # ── 萌化 ──────────────────────────────────────────────
            elif eff.type == EffectType.CUTE:
                if eff.desc == 'transfer_cute':
                    # 反弹：将自己萌化层数转移给敌方
                    self_cute = getattr(attacker, 'cute_stacks', 0)
                    if self_cute > 0:
                        self._apply_cute_effect(defender, self_cute)
                        self._restore_cute_form(attacker, self_cute)
                elif eff.desc == 'reverse_cute':
                    # 逆向演化：解除自己萌化，转移给敌方
                    self_cute = getattr(attacker, 'cute_stacks', 0)
                    if self_cute > 0:
                        self._apply_cute_effect(defender, self_cute)
                        self._restore_cute_form(attacker, self_cute)
                        # 恢复自身因萌化损失的属性
                        attacker.stat_modifiers.physical_attack = max(0, attacker.stat_modifiers.physical_attack)
                        attacker.stat_modifiers.magical_attack = max(0, attacker.stat_modifiers.magical_attack)
                else:
                    # 清除对手所有增益 + 施加减益
                    self._apply_cute_effect(defender, int(eff.value))

            # ── 折返 ──────────────────────────────────────────────
            elif eff.type == EffectType.RETURN:
                attacker.pending_switch_out = True

            # ── 离场 ──────────────────────────────────────────────
            elif eff.type == EffectType.SWITCH_OUT:
                target_pet.pending_switch_out = True

            # ── 复活 ──────────────────────────────────────────────
            elif eff.type == EffectType.REVIVE:
                ps = state.player if target_is_player else state.opponent
                for pet in ps.team:
                    if not pet.is_alive:
                        pet.is_alive = True
                        pet.current_hp = int(pet.max_hp * max(0.1, eff.value))
                        break  # 只复活第一只死亡的精灵

            # ── 应对额外效果 ──────────────────────────────────────
            elif eff.type == EffectType.COUNTER and counter_success:
                self._apply_counter_bonus(
                    state, is_player, attacker, defender, eff.desc, total_damage
                )

            # ── 迅捷 ──────────────────────────────────────────────
            elif eff.type == EffectType.SWIFT:
                # wiki: 迅捷 = 主动换精灵入场时立即释放该技能
                # 此效果在 _switch_pet 中检测并触发，技能效果本身无需额外处理
                pass

    def _resolve_target(self, target_str: str, attacker: PetInstance, defender: PetInstance) -> Optional[PetInstance]:
        if target_str == "self":
            return attacker
        elif target_str == "opponent":
            return defender
        return None

    def _apply_heal_or_reversed_damage(self, pet: PetInstance, heal: int) -> int:
        if heal <= 0:
            return 0

        multiplier = pet.get_runtime_flag('_heal_to_damage_multiplier', 0)
        if multiplier > 0:
            pet.pop_runtime_flag('_heal_to_damage_multiplier', None)
            damage = heal * multiplier
            pet.current_hp = max(0, pet.current_hp - damage)
            return -damage

        actual = min(heal, pet.max_hp - pet.current_hp)
        pet.current_hp += actual
        return actual

    def _swap_selected_skills(self, attacker: PetInstance, defender: PetInstance):
        attacker_skill_name = attacker.get_runtime_flag('_selected_skill_name', attacker.get_runtime_flag('_current_skill_name', ''))
        defender_skill_name = defender.get_runtime_flag('_selected_skill_name', defender.get_runtime_flag('_current_skill_name', ''))
        if not attacker_skill_name or not defender_skill_name:
            return

        attacker_index = next((i for i, sk in enumerate(attacker.skills) if sk.name == attacker_skill_name), None)
        defender_index = next((i for i, sk in enumerate(defender.skills) if sk.name == defender_skill_name), None)
        if attacker_index is None or defender_index is None:
            return

        attacker.skills[attacker_index], defender.skills[defender_index] = (
            defender.skills[defender_index],
            attacker.skills[attacker_index],
        )

    def _process_post_effect_knockout(
        self,
        pet: PetInstance,
        killer: Optional[PetInstance],
        is_player: bool,
        state: BattleState,
    ):
        if not pet or not pet.is_alive or pet.current_hp > 0:
            return

        pet.is_alive = False
        self.trait_processor.trigger_on_death(pet, killer, is_player, state)
        if killer is not None:
            self.trait_processor.trigger_on_kill(killer, pet, not is_player, state)
        self._deduct_hearts(pet, is_player, state)

    def _get_owned_skill(self, pet: PetInstance, skill_name: str) -> Optional[Skill]:
        for skill in pet.skills:
            if skill.name == skill_name:
                return skill
        return None

    def _get_payment_skill(self, pet: PetInstance, invoked_skill: Skill) -> tuple[str, Skill]:
        override_name = pet.get_runtime_flag('_payment_skill_name_override', None)
        if override_name:
            return override_name, self._get_owned_skill(pet, override_name) or invoked_skill

        selected_name = pet.get_runtime_flag('_selected_skill_name', None)
        if selected_name and selected_name == invoked_skill.name:
            return selected_name, self._get_owned_skill(pet, selected_name) or invoked_skill

        return invoked_skill.name, self._get_owned_skill(pet, invoked_skill.name) or invoked_skill

    def _get_effective_priority_bonus_for_skill(self, pet: PetInstance) -> int:
        extra = pet.get_runtime_flag('_next_skill_priority_bonus', 0) if pet.get_runtime_flag('_next_skill_priority_armed', False) else 0
        return pet.priority_bonus + extra

    def _append_temporary_energy_rule(self, pet: PetInstance, rule: dict) -> None:
        rules = list(pet.get_runtime_flag('_temporary_energy_rules', []))
        rules.append(rule)
        pet.set_runtime_flag('_temporary_energy_rules', rules)

    def _get_runtime_skill_energy_delta(self, pet: PetInstance, skill: Skill, current_turn: int) -> int:
        return get_runtime_skill_energy_delta(pet, skill, current_turn)

    def _clear_switch_out_runtime_flags(self, pet: PetInstance) -> None:
        for key in [
            '_temporary_energy_rules',
            '_permanent_all_skill_energy_delta',
            '_mental_disruption_energy_delta',
            '_permanent_attack_skill_energy_delta',
            '_next_attack_power_bonus_flat',
            '_next_attack_power_multiplier',
            '_next_skill_priority_bonus',
            '_skip_skill_this_turn',
            '_self_reenter_at_end_turn',
            '_grant_extra_hit_next_turn',
            '_qi_skill_counter_discount',
            '_forced_energy_multiplier',
            '_forced_flat_energy_delta',
            '_payment_skill_name_override',
        ]:
            pet.pop_runtime_flag(key, None)

    @staticmethod
    def _has_trait(pet: Optional[PetInstance], trait_name: str) -> bool:
        return bool(pet and any(trait.name == trait_name for trait in pet.template.traits))

    def _extract_switch_out_inheritable_flags(
        self,
        pet: Optional[PetInstance],
        opposing_pet: Optional[PetInstance],
    ) -> dict:
        inheritable = {}
        if not pet or not opposing_pet:
            return inheritable

        # 对手施加的技能增耗统一视为 debuff；黑羽夫人在场时转移给下一只入场精灵。
        if self._has_trait(opposing_pet, '黑羽夫人'):
            for key in (
                '_temporary_energy_rules',
                '_permanent_all_skill_energy_delta',
                '_mental_disruption_energy_delta',
                '_permanent_attack_skill_energy_delta',
            ):
                value = pet.get_runtime_flag(key, None)
                if value:
                    inheritable[key] = copy.deepcopy(value)

        return inheritable

    @staticmethod
    def _apply_inheritable_flags(pet: Optional[PetInstance], inheritable: dict) -> None:
        if not pet or not inheritable:
            return
        for key, value in inheritable.items():
            pet.set_runtime_flag(key, value)

    def _consume_post_skill_flags(self, pet: PetInstance, skill: Skill) -> None:
        if skill.base_power > 0 and skill.damage_type:
            pet.pop_runtime_flag('_next_attack_power_bonus_flat', None)
            pet.pop_runtime_flag('_next_attack_power_multiplier', None)
        if pet.get_runtime_flag('_next_skill_priority_armed', False):
            pet.pop_runtime_flag('_next_skill_priority_bonus', None)
            pet.pop_runtime_flag('_next_skill_priority_armed', None)

    def _add_or_set_mark(self, state: BattleState, is_player: bool, type_key: str, stacks: int, is_positive: bool) -> None:
        pos_mark, neg_mark = state.get_marks(is_player)
        current = pos_mark if is_positive else neg_mark
        if current and current.type_key == type_key:
            current.stacks += stacks
            return
        state.set_mark(is_player, FieldMark(type_key=type_key, stacks=stacks, is_positive=is_positive))

    def _apply_mirror_reflect_transformation(self, pet: PetInstance) -> None:
        pending_name = pet.get_runtime_flag('_mirror_reflect_pending_name', '')
        if not pending_name:
            return
        current_skill_name = pet.get_runtime_flag('_current_skill_name', '')
        if not current_skill_name:
            pet.pop_runtime_flag('_mirror_reflect_pending_name', None)
            return
        replacement = self.data_loader.skills.get(pending_name)
        if replacement is None:
            pet.pop_runtime_flag('_mirror_reflect_pending_name', None)
            return
        for idx, skill in enumerate(pet.skills):
            if skill.name == current_skill_name:
                pet.skills[idx] = copy.deepcopy(replacement)
                break
        pet.pop_runtime_flag('_mirror_reflect_pending_name', None)

    def _handle_switch_out_skill_growth(self, pet: Optional[PetInstance]):
        if not pet:
            return
        skill = self._get_owned_skill(pet, '感电')
        if skill is not None:
            skill.hits += 1

    def _handle_on_enter_skill_growth(self, pet: Optional[PetInstance]):
        if not pet:
            return
        skill = self._get_owned_skill(pet, '落雷')
        if skill is not None:
            skill.base_power += 20

    def _handle_counter_success_skill_growth(self, pet: PetInstance):
        skill = self._get_owned_skill(pet, '叠势')
        if skill is not None:
            skill.hits += 2
        skill = self._get_owned_skill(pet, '能量刃')
        if skill is not None:
            skill.base_power += 90
        skill = self._get_owned_skill(pet, '气沉丹田')
        if skill is not None:
            discount = min(10, pet.get_runtime_flag('_qi_skill_counter_discount', 0) + 3)
            pet.set_runtime_flag('_qi_skill_counter_discount', discount)
            skill.energy_cost = max(0, 10 - discount)

    def _handle_kill_skill_growth(self, pet: PetInstance):
        skill = self._get_owned_skill(pet, '流星火雨')
        if skill is not None:
            skill.base_power += 75
        skill = self._get_owned_skill(pet, '阳火增辉')
        if skill is not None:
            skill.base_power = max(1, skill.base_power * 2)
        skill = self._get_owned_skill(pet, '趁火打劫')
        if skill is not None:
            skill.hits += 2

    def _handle_post_use_skill_growth(
        self, state: BattleState, is_player: bool, pet: PetInstance, skill: Skill, counter_success: bool
    ):
        owned_skill = self._get_owned_skill(pet, skill.name)
        if owned_skill is not None:
            if skill.name == '孢子爆散':
                owned_skill.hits += 2
            elif skill.name == '乘胜追击':
                owned_skill.hits += 1
            elif skill.name == '撒娇':
                owned_skill.base_power += 20
            elif skill.name == '吹火':
                owned_skill.base_power += 20
            elif skill.name == '迫近攻击':
                owned_skill.base_power += 45
            elif skill.name == '过载回路':
                self._self_reenter_active_pet(state, is_player)

        opponent = (state.opponent if is_player else state.player).get_active_pet()
        own_team_state = (state.player if is_player else state.opponent).team_state

        if skill.name == '激怒' and opponent is not None:
            excluded_name = opponent.get_runtime_flag('_selected_skill_name', opponent.get_runtime_flag('_current_skill_name', ''))
            self._append_temporary_energy_rule(opponent, {
                'kind': 'all_except_skill',
                'excluded_skill_name': excluded_name,
                'delta': 3,
                'start_turn': state.turn + 1,
                'end_turn': state.turn + 3,
            })
        elif skill.name == '操控' and opponent is not None:
            selected_name = opponent.get_runtime_flag('_selected_skill_name', opponent.get_runtime_flag('_current_skill_name', ''))
            if selected_name:
                self._append_temporary_energy_rule(opponent, {
                    'kind': 'skill_name',
                    'skill_name': selected_name,
                    'delta': 7,
                    'start_turn': state.turn + 1,
                    'end_turn': state.turn + 3,
                })
        elif skill.name == '精神扰乱' and opponent is not None:
            delta = 3 if counter_success and 'defense' in skill.counters else 1
            opponent.set_runtime_flag(
                '_mental_disruption_energy_delta',
                opponent.get_runtime_flag('_mental_disruption_energy_delta', 0) + delta
            )
        elif skill.name == '聒噪' and opponent is not None:
            self._append_temporary_energy_rule(opponent, {
                'kind': 'all_attack',
                'delta': 3,
                'start_turn': state.turn + 1,
                'end_turn': state.turn + 3,
            })
        elif skill.name == '摇篮曲' and opponent is not None:
            opponent.set_runtime_flag(
                '_permanent_all_skill_energy_delta',
                opponent.get_runtime_flag('_permanent_all_skill_energy_delta', 0) + 3
            )
            if counter_success and 'defense' in skill.counters:
                opponent.set_runtime_flag('_skip_skill_this_turn', True)
                opponent.stun_turns += 1
        elif skill.name == '有效预防' and counter_success:
            pet.set_runtime_flag('_next_skill_priority_bonus', pet.get_runtime_flag('_next_skill_priority_bonus', 0) + 1)
            pet.set_runtime_flag('_next_skill_priority_armed', False)
        elif skill.name == '伺机而动':
            pet.set_runtime_flag('_next_attack_power_bonus_flat', pet.get_runtime_flag('_next_attack_power_bonus_flat', 0) + 70)
        elif skill.name == '持续高温' and counter_success:
            pet.set_runtime_flag('_next_attack_power_multiplier', max(2.0, pet.get_runtime_flag('_next_attack_power_multiplier', 1.0)))
        elif skill.name == '热身':
            multiplier = 4.0 if counter_success and 'defense' in skill.counters else 2.0
            pet.set_runtime_flag('_next_attack_power_multiplier', max(multiplier, pet.get_runtime_flag('_next_attack_power_multiplier', 1.0)))
        elif skill.name == '淬火' and counter_success:
            pet.set_runtime_flag('_next_attack_power_multiplier', max(2.0, pet.get_runtime_flag('_next_attack_power_multiplier', 1.0)))
        elif skill.name == '电磁偏转' and counter_success:
            pet.set_runtime_flag('_overload_circuit_bonus_turn', state.turn + 1)
            pet.set_runtime_flag('_overload_circuit_bonus_hits', 1)
        elif skill.name == '富养化':
            own_ps = state.player if is_player else state.opponent
            for idx, teammate in enumerate(own_ps.team):
                if idx == own_ps.active_index:
                    continue
                teammate.current_energy = min(10, teammate.current_energy + 3)
        elif skill.name == '击鼓传花':
            m = pet.stat_modifiers
            if m.physical_attack > 0:
                own_team_state.next_pet_gifts.add(f'物攻+{m.physical_attack}')
            if m.magical_attack > 0:
                own_team_state.next_pet_gifts.add(f'魔攻+{m.magical_attack}')
            if m.physical_defense > 0:
                own_team_state.next_pet_gifts.add(f'物防+{m.physical_defense}')
            if m.magical_defense > 0:
                own_team_state.next_pet_gifts.add(f'魔防+{m.magical_defense}')
            if m.speed > 0:
                own_team_state.next_pet_gifts.add(f'速度+{m.speed}')
            pet.pending_switch_out = True
        elif skill.name == '超新星馈赠':
            pet.set_runtime_flag('_supernova_gift_bonus', pet.get_runtime_flag('_supernova_gift_bonus', 0) + 1)
        elif skill.name == '心灵洞悉' and opponent is not None:
            pos_mark, neg_mark = state.get_marks(not is_player)
            total_marks = 0
            if pos_mark:
                total_marks += pos_mark.stacks
            if neg_mark:
                total_marks += neg_mark.stacks
            if total_marks > 0:
                self._add_or_set_mark(
                    state, not is_player, StatusEffectType.STAR_FALL_MARK.value, total_marks, False
                )
        elif skill.name == '放晴':
            increase = 100 if counter_success and 'defense' in skill.counters else 50
            for own_skill in pet.skills:
                if own_skill.element == '光':
                    own_skill.base_power += increase
        elif skill.name == '贮藏':
            zero_cost_count = sum(1 for own_skill in pet.skills if max(0, own_skill.energy_cost) == 0)
            pet.stat_modifiers.physical_attack += zero_cost_count * 5
            pet.stat_modifiers.magical_attack += zero_cost_count * 5
        elif skill.name == '加大功率':
            own_team_state.next_pet_gifts.add('回复8能量')
            own_team_state.suppress_next_pet_swift = True
            pet.pending_switch_out = True
        elif skill.name == '甜心续航':
            self._try_apply_cute_with_rewards(pet, heal_pct=0.4, energy_gain=4)
            if opponent is not None:
                self._try_apply_cute_with_rewards(opponent, heal_pct=0.4, energy_gain=4)
        elif skill.name == '玩具乐园':
            own_ps = state.player if is_player else state.opponent
            for idx, teammate in enumerate(own_ps.team):
                self._try_apply_cute_with_rewards(teammate, heal_pct=0.0, energy_gain=0)
                teammate.stat_modifiers.physical_attack += 3
                teammate.stat_modifiers.magical_attack += 3
                teammate.stat_modifiers.physical_defense += 3
                teammate.stat_modifiers.magical_defense += 3
                teammate.stats["速度"] = max(1, teammate.stats.get("速度", 100) + 20)
        elif skill.name == '气沉丹田':
            pet.set_runtime_flag('_qi_skill_counter_discount', 0)
            owned_skill = self._get_owned_skill(pet, '气沉丹田')
            if owned_skill is not None:
                owned_skill.energy_cost = 10

        skill_type = getattr(skill, 'element', None)
        if skill_type == '火' and skill.name != '山火':
            target = self._get_owned_skill(pet, '山火')
            if target is not None:
                target.base_power = max(1, target.base_power * 2)
        if skill_type == '草' and skill.name != '光能聚集':
            target = self._get_owned_skill(pet, '光能聚集')
            if target is not None:
                target.base_power += 60
        if owned_skill is not None and skill.name != '过曝':
            target = self._get_owned_skill(pet, '过曝')
            if target is not None and skill_type and target.element != skill_type:
                target.base_power += 30

    def _apply_stat_modifier(self, pet: PetInstance, eff: Effect, positive: bool):
        """应用属性修正（buff/debuff）"""
        sign = 1 if positive else -1
        stat_name = eff.desc.lower()
        value = int(eff.value) * sign
        is_flat = '_flat' in stat_name  # buff_flat 直接加到速度数值而非层数

        if "物攻" in stat_name or "physical_attack" in stat_name:
            pet.stat_modifiers.physical_attack += value
        elif "魔攻" in stat_name or "magical_attack" in stat_name:
            pet.stat_modifiers.magical_attack += value
        elif "物防" in stat_name or "physical_defense" in stat_name:
            pet.stat_modifiers.physical_defense += value
        elif "魔防" in stat_name or "magical_defense" in stat_name:
            pet.stat_modifiers.magical_defense += value
        elif "速度" in stat_name or "spd" in stat_name or "speed" in stat_name:
            if is_flat:
                # buff_flat：直接修改速度种族值（持久性速度变化）
                pet.stats["速度"] = max(1, pet.stats.get("速度", 100) + value)
            else:
                pet.stat_modifiers.speed += value
        elif "全攻" in stat_name or "all_attack" in stat_name:
            pet.stat_modifiers.physical_attack += value
            pet.stat_modifiers.magical_attack += value
        elif "全防" in stat_name or "all_defense" in stat_name:
            pet.stat_modifiers.physical_defense += value
            pet.stat_modifiers.magical_defense += value

    @staticmethod
    def _slot_condition_matches(effect_desc: str, slot_index: int) -> tuple[bool, str]:
        for prefix, valid_slots in (
            ('slot_13:', {0, 2}),
            ('slot_1:', {0}),
            ('slot_3:', {2}),
        ):
            if effect_desc.startswith(prefix):
                return slot_index in valid_slots, effect_desc.split(':', 1)[1]
        return True, effect_desc

    def _apply_cute_effect(self, defender: PetInstance, stacks: int):
        """萌化效果：清除对手增益，施加减益"""
        # 清除增益
        m = defender.stat_modifiers
        m.physical_attack = min(0, m.physical_attack)
        m.magical_attack = min(0, m.magical_attack)
        m.physical_defense = min(0, m.physical_defense)
        m.magical_defense = min(0, m.magical_defense)
        m.speed = min(0, m.speed)
        # 施加减益（默认降攻防各stacks层）
        m.physical_attack -= stacks
        m.magical_attack -= stacks
        for _ in range(max(0, stacks)):
            self._regress_cute_form(defender)
        defender.cute_stacks = getattr(defender, 'cute_stacks', 0) + stacks

    def _get_previous_cute_template(self, pet: Optional[PetInstance]) -> Optional[PetTemplate]:
        if not pet:
            return None

        evolution = getattr(pet.template, 'evolution', []) or []
        names = [item.get('name') for item in evolution if isinstance(item, dict) and item.get('name')]
        if not names:
            return None

        current_name = pet.template.name
        previous_name = None
        if current_name in names:
            idx = names.index(current_name)
            if idx > 0:
                previous_name = names[idx - 1]
        else:
            previous_name = names[-1]

        if not previous_name:
            return None
        return self.data_loader.pets.get(previous_name)

    @staticmethod
    def _apply_template_to_pet(pet: PetInstance, template: PetTemplate) -> None:
        hp_ratio = pet.current_hp / max(1, pet.max_hp)
        current_base_stats = getattr(pet.template, 'stats', {}) or {}
        stat_deltas = {
            stat_name: pet.stats.get(stat_name, 0) - current_base_stats.get(stat_name, 0)
            for stat_name in set(current_base_stats) | set(pet.stats)
        }

        pet.template = template
        pet.stats = {
            stat_name: max(1, template.stats.get(stat_name, 0) + stat_deltas.get(stat_name, 0))
            for stat_name in template.stats
        }
        pet.max_hp = max(1, pet.stats.get('生命', template.stats.get('生命', pet.max_hp)))
        if pet.is_alive:
            pet.current_hp = max(1, min(pet.max_hp, int(round(pet.max_hp * hp_ratio))))
        else:
            pet.current_hp = 0

    def _regress_cute_form(self, pet: Optional[PetInstance]) -> bool:
        previous_template = self._get_previous_cute_template(pet)
        if not pet or previous_template is None:
            return False

        history = list(pet.get_runtime_flag('_cute_form_history', []))
        history.append(pet.template)
        pet.set_runtime_flag('_cute_form_history', history)
        self._apply_template_to_pet(pet, previous_template)
        return True

    def _restore_cute_form(self, pet: Optional[PetInstance], stacks: int) -> None:
        if not pet or stacks <= 0:
            return

        history = list(pet.get_runtime_flag('_cute_form_history', []))
        restored = 0
        while history and restored < stacks:
            template = history.pop()
            self._apply_template_to_pet(pet, template)
            restored += 1
        pet.set_runtime_flag('_cute_form_history', history)
        pet.cute_stacks = max(0, getattr(pet, 'cute_stacks', 0) - restored)

    def _can_be_cuted(self, pet: PetInstance) -> bool:
        return self._get_previous_cute_template(pet) is not None

    def _try_apply_cute_with_rewards(self, pet: Optional[PetInstance], heal_pct: float, energy_gain: int) -> bool:
        if not pet or not pet.is_alive or not self._can_be_cuted(pet):
            return False
        self._apply_cute_effect(pet, 1)
        if heal_pct > 0:
            pet.current_hp = min(pet.max_hp, pet.current_hp + int(pet.max_hp * heal_pct))
        if energy_gain > 0:
            pet.current_energy = min(10, pet.current_energy + energy_gain)
        return True

    @staticmethod
    def _parse_status_type(name: str) -> Optional[StatusEffectType]:
        """把字符串映射到 StatusEffectType"""
        mapping = {
            "poison": StatusEffectType.POISON,
            "中毒": StatusEffectType.POISON,
            "poison_mark": StatusEffectType.POISON_MARK,
            "中毒印记": StatusEffectType.POISON_MARK,
            "burn": StatusEffectType.BURN,
            "灼烧": StatusEffectType.BURN,
            "freeze": StatusEffectType.FREEZE,
            "冻结": StatusEffectType.FREEZE,
            "parasite": StatusEffectType.PARASITE,
            "寄生": StatusEffectType.PARASITE,
            "star_fall_mark": StatusEffectType.STAR_FALL_MARK,
            "星陨印记": StatusEffectType.STAR_FALL_MARK,
            "descent_mark": StatusEffectType.DESCENT_MARK,
            "降灵印记": StatusEffectType.DESCENT_MARK,
            "thorn": StatusEffectType.THORN,
            "棘刺": StatusEffectType.THORN,
            "frost_mark": StatusEffectType.FROST_MARK,
            "凝霜印记": StatusEffectType.FROST_MARK,
            "photosynthesis_mark": StatusEffectType.PHOTOSYNTHESIS_MARK,
            "光合印记": StatusEffectType.PHOTOSYNTHESIS_MARK,
        }
        return mapping.get(name)

    def _process_turn_start_skill_position_changes(self, state: BattleState):
        for ps in (state.player, state.opponent):
            pet = ps.get_active_pet()
            if not pet or not pet.is_alive:
                continue

            current_positions = {skill.name: idx for idx, skill in enumerate(pet.skills)}
            for skill in pet.skills:
                if skill.name != '齿轮扭矩':
                    continue
                current_index = current_positions.get(skill.name)
                previous_index = pet.get_runtime_flag('_gear_torque_previous_slot', None)
                if previous_index is not None and current_index is not None and previous_index != current_index:
                    skill.base_power += 20
                pet.set_runtime_flag('_gear_torque_previous_slot', current_index)

            pet.set_runtime_flag('_previous_skill_positions', current_positions)

    def _expire_turn_limited_flags(self, pet: PetInstance, current_turn: int):
        bonus_turn = pet.get_runtime_flag('_overload_circuit_bonus_turn', None)
        if bonus_turn is not None and current_turn > bonus_turn:
            pet.pop_runtime_flag('_overload_circuit_bonus_turn', None)
            pet.pop_runtime_flag('_overload_circuit_bonus_hits', None)
        rules = [
            rule for rule in pet.get_runtime_flag('_temporary_energy_rules', [])
            if current_turn <= rule.get('end_turn', -1)
        ]
        pet.set_runtime_flag('_temporary_energy_rules', rules)
        qi_skill = self._get_owned_skill(pet, '气沉丹田')
        if qi_skill is not None:
            qi_discount = pet.get_runtime_flag('_qi_skill_counter_discount', 0)
            qi_skill.energy_cost = max(0, 10 - qi_discount)

    def _self_reenter_active_pet(self, state: BattleState, is_player: bool):
        ps = state.player if is_player else state.opponent
        current = ps.get_active_pet()
        if not current or not current.is_alive:
            return

        opponent_ps = state.opponent if is_player else state.player
        opp = opponent_ps.get_active_pet()
        inheritable_flags = self._extract_switch_out_inheritable_flags(current, opp)

        self._handle_switch_out_skill_growth(current)
        keep_buffs = self.trait_processor.has_keep_buff_trait(current)
        self._clear_switch_out_runtime_flags(current)
        current.clear_on_switch_out(keep_buffs=keep_buffs)

        self.trait_processor.trigger_on_switch_out(current, opp, is_player, state)

        ps.team_state.switch_count += 1
        self._apply_inheritable_flags(current, inheritable_flags)
        self.status_processor.apply_field_mark_on_enter(current, is_player, state)
        self.trait_processor.apply_next_pet_gifts(current, is_player, state)
        self.trait_processor.trigger_on_enter(current, opp, is_player, state)
        if current.get_runtime_flag('_extend_burst', False):
            current.burst_turns_remaining = max(current.burst_turns_remaining, 2)

        current.set_runtime_flag('_overload_circuit_bonus_turn', state.turn + 1)
        current.set_runtime_flag('_overload_circuit_bonus_hits', 1)

    # ── 内部：心数扣除 ───────────────────────────────────────────

    def _deduct_hearts(self, pet: PetInstance, is_player: bool, state: BattleState):
        """精灵死亡时扣除心数"""
        hearts = 1
        # 传说精灵额外扣1心
        if pet.template.is_legendary or "传说" in pet.template.name:
            hearts += 1
        # 卡瓦重少扣1心
        if "卡瓦重" in pet.template.name:
            hearts -= 1
        hearts = max(0, hearts)

        if is_player:
            state.player_hearts -= hearts
        else:
            state.opponent_hearts -= hearts

    # ── 内部：强制结束 ───────────────────────────────────────────

    def _force_end_battle(self, state: BattleState):
        """50回合到时强制结束：按局面优势确定性判定胜者"""
        # 优先比较心数
        if state.player_hearts != state.opponent_hearts:
            if state.player_hearts > state.opponent_hearts:
                state.opponent_hearts = 0
            else:
                state.player_hearts = 0
            return

        # 心数相同时比较存活精灵总HP
        p_hp = sum(p.current_hp for p in state.player.team if p.is_alive)
        o_hp = sum(p.current_hp for p in state.opponent.team if p.is_alive)
        if p_hp > o_hp:
            state.opponent_hearts = 0
        elif o_hp > p_hp:
            state.player_hearts = 0
        else:
            # 完全平局：比较存活数量
            p_alive = sum(1 for p in state.player.team if p.is_alive)
            o_alive = sum(1 for p in state.opponent.team if p.is_alive)
            if p_alive > o_alive:
                state.opponent_hearts = 0
            elif o_alive > p_alive:
                state.player_hearts = 0
            else:
                # 彻底平局
                state.player_hearts = 0
                state.opponent_hearts = 0

    # ── 内部：回合结束 ───────────────────────────────────────────

    def _end_turn_processing(self, state: BattleState):
        process_end_turn(
            state,
            self.status_processor,
            self.trait_processor,
            self._deduct_hearts,
            self._apply_mirror_reflect_transformation,
            self._self_reenter_active_pet,
            self._get_end_of_turn_trigger_count,
        )

    # ── 内部：应对附加效果 ───────────────────────────────────────

    def _get_end_of_turn_trigger_count(self, state: BattleState) -> int:
        """返回当前局面全局回合末效果的触发次数。"""
        modifier = 0
        for pet in [state.player.get_active_pet(), state.opponent.get_active_pet()]:
            if not pet or not pet.is_alive:
                continue
            for trait in pet.template.traits:
                if trait.name == "双向光速":
                    modifier += 1
                elif trait.name == "陨落":
                    modifier -= 1
        return max(0, 1 + modifier)

    def _update_skill_type_count(self, state: BattleState, is_player: bool, skill):
        """更新己方技能类别使用计数，供入场积累型特性消费"""
        ts = (state.player if is_player else state.opponent).team_state
        skill_type = getattr(skill, 'element', None) or getattr(skill, 'type', None)
        from core.models import SkillCategory
        category = getattr(skill, 'category', None)
        if skill_type == '地':
            ts.earth_skill_count += 1
        if skill_type == '冰':
            ts.ice_skill_count += 1
        if skill_type == '火':
            ts.fire_skill_count += 1
        if skill_type == '水':
            ts.water_skill_count += 1
        if category is not None and hasattr(SkillCategory, 'STATUS') and category == SkillCategory.STATUS:
            ts.status_skill_count += 1
        if category is not None and hasattr(SkillCategory, 'DEFENSE') and category == SkillCategory.DEFENSE:
            ts.defense_skill_count += 1

    def _apply_counter_bonus(
        self,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        defender: PetInstance,
        desc: str,
        total_damage: int
    ):
        """
        解析并执行应对技能的附加效果。
        desc 格式：'attack:效果|defense:效果|status:效果'
        三段均可选，以 '|' 分隔，各段前缀决定触发类型（此处统一执行，触发判断在调用方）。
        """
        if not desc:
            return

        for segment in desc.split('|'):
            segment = segment.strip()
            if ':' not in segment:
                continue
            prefix, content = segment.split(':', 1)
            content = content.strip()
            prefix = prefix.strip().lower()

            # ── attack/defense/status 三类效果 ──────────────────
            if prefix in ('attack', 'defense', 'status'):
                self._parse_counter_effect(
                    content, prefix, state, is_player, attacker, defender, total_damage
                )

    def _parse_counter_effect(
        self,
        content: str,
        prefix: str,
        state: BattleState,
        is_player: bool,
        attacker: PetInstance,
        defender: PetInstance,
        total_damage: int
    ):
        """解析单条应对效果文本并执行"""
        import re

        # ── 自身回复生命 ──────────────────────────────────────────
        m = re.search(r'自己回复(\d+)%生命', content)
        if m:
            pct = int(m.group(1)) / 100
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + int(attacker.max_hp * pct))
            return

        # ── 防御改为回复生命（defense:改为回复50%生命）────────────
        if prefix == 'defense' and '改为回复' in content and '生命' in content:
            m = re.search(r'改为回复(\d+)%生命', content)
            if m:
                pct = int(m.group(1)) / 100
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + int(attacker.max_hp * pct))
            return

        # ── 回复能量 ──────────────────────────────────────────────
        if '回复3能量' in content:
            attacker.current_energy = min(10, attacker.current_energy + 3)
            return
        m = re.search(r'己方队伍获得(\d+)次随机奉献', content)
        if m:
            team_state = (state.player if is_player else state.opponent).team_state
            self.trait_processor.grant_random_devotion(
                team_state,
                int(m.group(1)),
                f"counter:{attacker.template.name}:{state.turn}:{prefix}"
            )
            return
        if '回复能量' in content:
            attacker.current_energy = min(10, attacker.current_energy + 1)
            return

        # ── 敌方失去能量 ──────────────────────────────────────────
        m = re.search(r'敌方失去(\d+)能量', content)
        if m:
            defender.current_energy = max(0, defender.current_energy - int(m.group(1)))
            return

        # ── 防御改为敌方失去能量（defense:改为敌方失去6能量）────────
        if prefix == 'defense' and '改为敌方失去' in content and '能量' in content:
            m = re.search(r'改为敌方失去(\d+)能量', content)
            if m:
                defender.current_energy = max(0, defender.current_energy - int(m.group(1)))
            return

        # ── 敌方脱离（强制换宠）──────────────────────────────────
        if content == '敌方脱离':
            defender.pending_switch_out = True
            return

        # ── 自己脱离 / 自己回合结束返场 ──────────────────────────
        if content == '自己脱离':
            attacker.pending_switch_out = True
            return
        if content == '自己回合结束返场':
            attacker.set_runtime_flag('_self_reenter_at_end_turn', True)
            return
        if content == '回合结束时使敌方精灵返场':
            defender.set_runtime_flag('_self_reenter_at_end_turn', True)
            return
        if content == '本技能变为被应对的技能':
            mirrored_name = defender.get_runtime_flag('_selected_skill_name', defender.get_runtime_flag('_current_skill_name', ''))
            if mirrored_name:
                attacker.set_runtime_flag('_mirror_reflect_pending_name', mirrored_name)
            return

        # ── 敌方冻结 ─────────────────────────────────────────────
        m = re.search(r'敌方获得(\d+)层冻结', content)
        if m:
            defender.freeze_stacks += int(m.group(1))
            return

        # ── 敌方获得印记 ─────────────────────────────────────────
        m = re.search(r'敌方获得(\d+)层(.+?)印记', content)
        if m:
            stacks = int(m.group(1))
            mark_name = m.group(2) + '印记'
            st = self._parse_status_type(mark_name)
            if st is None:
                st = self._parse_status_type(m.group(2))
            if st:
                from core.models import FieldMark
                mark = FieldMark(type_key=st.value, stacks=stacks, is_positive=False)
                state.set_mark(not is_player, mark)
            return

        # ── 敌方萌化 ─────────────────────────────────────────────
        m = re.search(r'敌方获得(\d+)层萌化', content)
        if m:
            self._apply_cute_effect(defender, int(m.group(1)))
            return

        # ── 下一次行动获得先手+1 ──────────────────────────────────
        if '下一次行动获得先手' in content:
            attacker.set_runtime_flag('_next_skill_priority_bonus', attacker.get_runtime_flag('_next_skill_priority_bonus', 0) + 1)
            return

        # ── 本次技能威力倍率 ─────────────────────────────────────
        # 注：此效果在技能执行前已由 COUNTER 触发时注入 modified_power，
        # 此处仅作标记记录，实际威力在 _execute_skill 中已生效。
        m = re.search(r'本次技能威力变为(\d+(?:\.\d+)?)倍', content)
        if m:
            # 已在威力计算前应用，无需重复处理
            return
        if '本次技能威力翻倍' in content:
            return

        # ── 本技能变为多连击 ────────────────────────────────────
        m = re.search(r'本技能变为(\d+)连击', content)
        if m:
            # 连击数在 _compute_total_hits 中动态计算，
            # 此处将临时值写入 attacker.counter_extra_hits 供其读取
            attacker.counter_extra_hits = int(m.group(1))
            return

        # ── 本次攻击吸血100% ───────────────────────────────────
        if '本次攻击吸血100%' in content:
            if total_damage > 0:
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + total_damage)
            return

        # ── 自己获得物攻+100% ──────────────────────────────────
        m = re.search(r'自己获得物攻\+(\d+)%', content)
        if m:
            pct = int(m.group(1))
            # 换算为层数：每层约10%，100%≈10层
            attacker.stat_modifiers.physical_attack += pct // 10
            return

        # ── 本次技能能耗永久减少 ────────────────────────────────
        m = re.search(r'本次技能能耗永久-(\d+)', content)
        if m:
            # 永久降低技能能耗（直接修改 Skill 对象）
            # 注意：Skill 对象是共享引用，需谨慎（此处遵循 wiki 设计）
            # 在实际对局中可通过 attacker 的技能列表找到对应技能
            reduction = int(m.group(1))
            for sk in attacker.skills:
                if sk.name == attacker.get_runtime_flag('_current_skill_name', ''):
                    SlotEffectsProcessor.apply_energy_cost_delta(attacker, sk, -reduction)
            return

        m = re.search(r'两侧技能能耗永久-(\d+)', content)
        if m:
            reduction = int(m.group(1))
            current_skill_name = attacker.get_runtime_flag('_current_skill_name', '')
            current_skill = None
            for sk in attacker.skills:
                if sk.name == current_skill_name:
                    current_skill = sk
                    break
            if current_skill is not None:
                for adjacent in SlotEffectsProcessor.get_adjacent_skills(attacker, current_skill):
                    SlotEffectsProcessor.apply_energy_cost_delta(attacker, adjacent, -reduction)
            return

        m = re.search(r'两侧技能(?:的)?威力永久\+(\d+)', content)
        if m:
            increase = int(m.group(1))
            current_skill_name = attacker.get_runtime_flag('_current_skill_name', '')
            current_skill = None
            for sk in attacker.skills:
                if sk.name == current_skill_name:
                    current_skill = sk
                    break
            if current_skill is not None:
                SlotEffectsProcessor.adjust_adjacent_skill_power(attacker, current_skill, increase)
            return

        # ── 防御：速度永久提升 ────────────────────────────────
        if prefix == 'defense' and '速度+' in content:
            m = re.search(r'速度\+(\d+)', content)
            if m:
                attacker.stats['速度'] = attacker.stats.get('速度', 100) + int(m.group(1))
            return

        # ── 防御：额外获得X层（通用：叠加印记层数）────────────
        if prefix == 'defense' and '额外获得' in content and '层' in content:
            m = re.search(r'额外获得(\d+)层', content)
            if m:
                # 叠加到自身正面印记
                pos_mark, _ = state.get_marks(is_player)
                if pos_mark:
                    pos_mark.stacks += int(m.group(1))
            return

        # ── 对敌方造成物理伤害（额外伤害）────────────────────────
        if '对敌方造成物理伤害' in content and defender.is_alive:
            phys_atk = attacker.get_effective_stat('物攻')
            phys_def = defender.get_effective_stat('物防')
            extra = max(1, int(phys_atk / max(1, phys_def) * 0.9 * 30))
            defender.current_hp = max(0, defender.current_hp - extra)
            if defender.current_hp == 0:
                defender.is_alive = False
            return
