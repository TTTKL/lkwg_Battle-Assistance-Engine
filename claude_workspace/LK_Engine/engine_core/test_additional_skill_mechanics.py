import unittest
import copy
import json
import shutil
from pathlib import Path

from core.models import (
    Action,
    ActionType,
    BattleState,
    DamageType,
    Effect,
    EffectType,
    FieldMark,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
    Trait,
)
from core.status_effects import StatusEffectType
from data_loader import DataLoader
from game_analysis_engine import GameAnalysisEngine
from engine.action_generator import ActionGenerator
from engine.extended_battle_engine import ExtendedBattleEngine
from api import _format_state, _build_action_panel


def make_skill(
    name: str,
    power: int = 0,
    energy: int = 0,
    element: str = "普通",
    category: SkillCategory = SkillCategory.STATUS,
    damage_type: DamageType = DamageType.PHYSICAL,
    effects=None,
    hits: int = 1,
    counters=None,
) -> Skill:
    return Skill(
        name=name,
        element=element,
        category=category,
        damage_type=damage_type if power > 0 else None,
        base_power=power,
        energy_cost=energy,
        effects=effects or [],
        hits=hits,
        counters=counters or [],
    )


def make_pet(name: str, skills, hp: int = 100) -> PetInstance:
    template = PetTemplate(
        id=1,
        name=name,
        types=["普通"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 100, "魔防": 100, "速度": 100},
        traits=[],
        learnable_skills=[],
    )
    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=100,
        stats=template.stats.copy(),
        skills=skills,
        current_energy=10,
    )


def make_cutable_pet(name: str, skills, hp: int = 100) -> PetInstance:
    pet = make_pet(name, skills, hp)
    pet.template.evolution = [{"to": "next"}]
    return pet


def make_refraction_skill() -> Skill:
    """构造与 battle_data 现状一致的折射技能，验证运行时动态改写是否生效。"""
    return make_skill(
        "折射",
        power=50,
        energy=4,
        element="光",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.MAGICAL,
        effects=[
            Effect(EffectType.APPLY_STATUS, "opponent", 2, status_type="poison", stacks=2),
            Effect(EffectType.APPLY_STATUS, "opponent", 4, status_type="burn", stacks=4),
            Effect(EffectType.APPLY_STATUS, "opponent", 2, status_type="freeze", stacks=2),
            Effect(
                EffectType.APPLY_MARK,
                "opponent",
                -1,
                status_type=StatusEffectType.STAR_FALL_MARK.value,
                stacks=1,
            ),
            Effect(EffectType.LIFESTEAL, "self", 0.3),
        ],
    )


class AdditionalSkillMechanicsTest(unittest.TestCase):
    def setUp(self):
        self.engine = ExtendedBattleEngine(DataLoader())

    def test_refraction_only_applies_effects_for_carried_elements(self):
        refraction = make_refraction_skill()
        fire = make_skill("火焰辅助", element="火")
        evil = make_skill("恶意辅助", element="恶")
        wing = make_skill("翼风辅助", element="翼")
        player = make_pet("玩家", [refraction, fire, evil, wing], hp=70)
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )

        attacker_after = new_state.player.get_active_pet()
        defender_after = new_state.opponent.get_active_pet()
        _, opponent_neg_mark = new_state.get_marks(False)

        self.assertGreater(attacker_after.current_hp, 70)
        self.assertEqual(defender_after.get_status_stacks(StatusEffectType.BURN), 2)
        self.assertEqual(defender_after.get_status_stacks(StatusEffectType.POISON), 0)
        self.assertEqual(defender_after.get_status_stacks(StatusEffectType.FREEZE), 0)
        self.assertIsNone(opponent_neg_mark)

        baseline_refraction = make_refraction_skill()
        baseline_player = make_pet("玩家", [baseline_refraction, fire, evil], hp=70)
        baseline_opponent = make_pet("对手", [make_skill("待机")], hp=100)
        baseline_state = BattleState(
            player=PlayerState(team=[baseline_player], active_index=0),
            opponent=PlayerState(team=[baseline_opponent], active_index=0),
        )
        baseline_after = self.engine.apply_action(
            baseline_state,
            Action(type=ActionType.USE_SKILL, skill=baseline_refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )

        self.assertLess(
            defender_after.current_hp,
            baseline_after.opponent.get_active_pet().current_hp,
            "携带翼系技能时，折射应因连击+1造成更高伤害",
        )

    def test_refraction_applies_ground_water_and_normal_branches(self):
        refraction = make_refraction_skill()
        ground = make_skill("地面辅助", element="地")
        water = make_skill("水流辅助", element="水")
        normal = make_skill("普通辅助", element="普通")
        player = make_pet("玩家", [refraction, ground, water, normal], hp=100)
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )

        attacker_after = new_state.player.get_active_pet()
        defender_after = new_state.opponent.get_active_pet()

        self.assertEqual(attacker_after.skills[0].energy_cost, 3)
        self.assertEqual(attacker_after.skills[1].energy_cost, 0)
        self.assertEqual(attacker_after.skills[2].energy_cost, 0)
        self.assertEqual(attacker_after.skills[3].energy_cost, 0)
        self.assertEqual(defender_after.stats["速度"], 60)
        self.assertEqual(getattr(defender_after, "warmup_hits_bonus", 0), -2)

        baseline_refraction = make_refraction_skill()
        baseline_player = make_pet("玩家", [baseline_refraction, ground, water], hp=100)
        baseline_opponent = make_pet("对手", [make_skill("待机")], hp=100)
        baseline_state = BattleState(
            player=PlayerState(team=[baseline_player], active_index=0),
            opponent=PlayerState(team=[baseline_opponent], active_index=0),
        )
        baseline_after = self.engine.apply_action(
            baseline_state,
            Action(type=ActionType.USE_SKILL, skill=baseline_refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )

        self.assertLess(
            defender_after.current_hp,
            baseline_after.opponent.get_active_pet().current_hp,
            "携带普通系技能时，折射应因威力+20造成更高伤害",
        )

    def test_formatted_state_exposes_energy_cost_marker_after_refraction_water_branch(self):
        refraction = make_refraction_skill()
        bubble = make_skill("气泡", element="水")
        player = make_pet("迪莫", [refraction, bubble], hp=100)
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )

        formatted = _format_state(new_state)
        active_pet = formatted["player"]["team"][formatted["player"]["active_index"]]
        markers = active_pet.get("energy_cost_markers") or []
        marker_texts = {item.get("text") for item in markers}

        self.assertIn("消耗-1", marker_texts)

    def test_best_partner_does_not_refund_energy_without_type_advantage(self):
        refraction = make_refraction_skill()
        player = make_pet("迪莫", [refraction], hp=100)
        player.template.traits = [Trait(name="最好的伙伴", desc="")]
        opponent = make_pet("对手", [make_skill("待机", element="光")], hp=100)
        opponent.template.types = ["光"]
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )

        attacker_after = new_state.player.get_active_pet()
        self.assertEqual(attacker_after.current_energy, 6)
        self.assertEqual(attacker_after.stat_modifiers.physical_attack, 0)
        self.assertEqual(attacker_after.stat_modifiers.speed, 0)

    def test_switch_out_effect_can_force_opponent_switch(self):
        force_switch = make_skill(
            "驱逐",
            effects=[Effect(EffectType.SWITCH_OUT, "opponent", 0)],
        )
        player = make_pet("玩家", [force_switch])
        opponent_a = make_pet("对手A", [make_skill("待机")])
        opponent_b = make_pet("对手B", [make_skill("后备")])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent_a, opponent_b], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=force_switch),
            Action(type=ActionType.GATHER_ENERGY),
        )

        self.assertEqual(new_state.opponent.active_index, 1)
        self.assertEqual(new_state.opponent.get_active_pet().template.name, "对手B")

    def test_hidden_terms_swaps_selected_skills_between_both_sides(self):
        hidden_terms = make_skill(
            "隐藏条款",
            effects=[Effect(EffectType.ENERGY_RESTORE, "self", 0, desc="swap_current_skills")],
        )
        slash = make_skill("斩击", power=40, energy=3, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [hidden_terms])
        opponent = make_pet("对手", [slash])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=hidden_terms),
            Action(type=ActionType.USE_SKILL, skill=slash),
        )

        self.assertEqual(new_state.player.get_active_pet().skills[0].name, "斩击")
        self.assertEqual(new_state.opponent.get_active_pet().skills[0].name, "隐藏条款")

    def test_fake_invoice_turns_next_heal_into_damage(self):
        fake_invoice = make_skill(
            "伪造账单",
            effects=[Effect(EffectType.ENERGY_RESTORE, "opponent", 0, desc="heal_to_damage:2")],
        )
        heal_skill = make_skill(
            "治疗术",
            effects=[Effect(EffectType.HEAL, "self", 0.2)],
        )
        player = make_pet("玩家", [fake_invoice])
        opponent = make_pet("对手", [heal_skill], hp=60)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=fake_invoice),
            Action(type=ActionType.GATHER_ENERGY),
        )
        hp_before = state.opponent.get_active_pet().current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=heal_skill),
        )

        self.assertLess(state.opponent.get_active_pet().current_hp, hp_before)

    def test_borrow_uses_teammate_skill_stats(self):
        borrow = make_skill("借用", power=0, energy=1)
        borrowed = make_skill("高能光束", power=80, energy=4, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [borrow])
        teammate = make_pet("队友", [borrowed])
        opponent = make_pet("对手", [make_skill("待机")])
        state = BattleState(
            player=PlayerState(team=[player, teammate], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=borrow),
            Action(type=ActionType.GATHER_ENERGY),
        )

        self.assertLess(new_state.opponent.get_active_pet().current_hp, 100)
        self.assertEqual(new_state.player.get_active_pet().current_energy, 9)
        self.assertEqual(new_state.player.get_active_pet().get_runtime_flag("_borrowed_skill_name"), "高能光束")

    def test_transform_skill_pays_displayed_skill_cost(self):
        copy_skill = make_skill("取念", power=0, energy=2)
        enemy_skill = make_skill("终极打击", power=90, energy=5, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [copy_skill])
        opponent = make_pet("对手", [enemy_skill])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=copy_skill),
            Action(type=ActionType.GATHER_ENERGY),
        )

        self.assertLess(new_state.opponent.get_active_pet().current_hp, 100)
        self.assertEqual(new_state.player.get_active_pet().current_energy, 8)
        self.assertEqual(new_state.player.get_active_pet().get_runtime_flag("_copied_skill_name"), "终极打击")

    def test_comet_consumes_all_self_hp_after_use(self):
        comet = make_skill("彗星", power=80, energy=3, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [comet], hp=100)
        opponent = make_pet("对手", [make_skill("待机")])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=comet),
            Action(type=ActionType.GATHER_ENERGY),
        )

        self.assertFalse(new_state.player.get_active_pet().is_alive)
        self.assertEqual(new_state.player.get_active_pet().current_hp, 0)
        self.assertEqual(new_state.player_hearts, 3)

    def test_switch_enter_counter_and_use_growth_skills(self):
        electric = make_skill("感电", power=30, energy=2, category=SkillCategory.ATTACK, hits=1)
        thunder = make_skill("落雷", power=50, energy=3, category=SkillCategory.ATTACK)
        stack_force = make_skill("叠势", power=40, energy=3, category=SkillCategory.ATTACK, counters=["attack"])
        energy_blade = make_skill("能量刃", power=40, energy=3, category=SkillCategory.ATTACK, counters=["attack"])
        spore = make_skill("孢子爆散", power=40, energy=3, category=SkillCategory.ATTACK, hits=1)
        flame_other = make_skill("小火苗", power=20, energy=2, element="火", category=SkillCategory.ATTACK)
        wildfire = make_skill("山火", power=30, energy=3, element="火", category=SkillCategory.ATTACK)

        player_a = make_pet("玩家A", [electric, stack_force, energy_blade, spore])
        player_b = make_pet("玩家B", [thunder, flame_other, wildfire])
        enemy_attack = make_skill("敌方攻击", power=40, energy=3, category=SkillCategory.ATTACK)
        opponent = make_pet("对手", [enemy_attack])

        state = BattleState(
            player=PlayerState(team=[player_a, player_b], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.SWITCH_PET, target_index=1),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.team[0].skills[0].hits, 2)
        self.assertEqual(state.player.get_active_pet().skills[0].base_power, 70)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.SWITCH_PET, target_index=0),
            Action(type=ActionType.GATHER_ENERGY),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=stack_force),
            Action(type=ActionType.USE_SKILL, skill=enemy_attack),
        )
        grown_pet = state.player.get_active_pet()
        self.assertEqual(grown_pet.skills[1].hits, 3)
        self.assertEqual(grown_pet.skills[2].base_power, 130)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=spore),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().skills[3].hits, 3)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.SWITCH_PET, target_index=1),
            Action(type=ActionType.GATHER_ENERGY),
        )
        before_power = state.player.get_active_pet().skills[2].base_power
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=flame_other),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().skills[2].base_power, before_power * 2)

    def test_gear_torque_only_grows_after_slot_change_at_turn_start(self):
        filler_a = make_skill("填充A", power=10, energy=1, category=SkillCategory.ATTACK)
        gear = make_skill("齿轮扭矩", power=80, energy=3, element="机械", category=SkillCategory.ATTACK)
        filler_b = make_skill("填充B", power=10, energy=1, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [filler_a, gear, filler_b])
        opponent = make_pet("对手", [make_skill("待机")])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().skills[1].base_power, 80)

    def test_anger_and_manipulate_apply_delayed_energy_debuffs(self):
        anger = make_skill("激怒", energy=1)
        manipulate = make_skill("操控", energy=1)
        attack_a = make_skill("攻击A", power=30, energy=1, category=SkillCategory.ATTACK)
        attack_b = make_skill("攻击B", power=30, energy=1, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [anger, manipulate])
        opponent = make_pet("对手", [attack_a, attack_b])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=anger),
            Action(type=ActionType.USE_SKILL, skill=attack_a),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=attack_b),
        )
        self.assertEqual(state.opponent.get_active_pet().current_energy, 5)

        state = BattleState(
            player=PlayerState(team=[make_pet("玩家", [manipulate])], active_index=0),
            opponent=PlayerState(team=[make_pet("对手", [attack_a, attack_b])], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=manipulate),
            Action(type=ActionType.USE_SKILL, skill=attack_a),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=attack_a),
        )
        self.assertEqual(state.opponent.get_active_pet().current_energy, 1)

    def test_mental_disruption_clears_on_switch(self):
        disrupt = make_skill("精神扰乱", energy=1)
        attack = make_skill("攻击", power=30, energy=2, category=SkillCategory.ATTACK)
        player = make_pet("玩家", [disrupt])
        opponent_a = make_pet("对手A", [attack])
        opponent_b = make_pet("对手B", [attack])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent_a, opponent_b], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=disrupt),
            Action(type=ActionType.GATHER_ENERGY),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=attack),
        )
        self.assertEqual(state.opponent.get_active_pet().current_energy, 7)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.SWITCH_PET, target_index=1),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.SWITCH_PET, target_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=attack),
        )
        self.assertEqual(state.opponent.get_active_pet().current_energy, 5)

    def test_mental_disruption_is_inherited_when_black_feather_is_active(self):
        disrupt = make_skill("精神扰乱", energy=1)
        attack = make_skill("攻击", power=30, energy=2, category=SkillCategory.ATTACK)
        player = make_pet("黑羽方", [disrupt])
        player.template.traits = [Trait(name="黑羽夫人", desc="")]
        opponent_a = make_pet("对手A", [attack])
        opponent_b = make_pet("对手B", [attack])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent_a, opponent_b], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=disrupt),
            Action(type=ActionType.GATHER_ENERGY),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.SWITCH_PET, target_index=1),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=attack),
        )

        self.assertEqual(state.opponent.get_active_pet().current_energy, 7)

    def test_temporary_energy_debuff_is_inherited_when_black_feather_is_active(self):
        anger = make_skill("激怒", energy=1)
        attack_a = make_skill("攻击A", power=30, energy=1, category=SkillCategory.ATTACK)
        attack_b = make_skill("攻击B", power=30, energy=1, category=SkillCategory.ATTACK)
        player = make_pet("黑羽方", [anger])
        player.template.traits = [Trait(name="黑羽夫人", desc="")]
        opponent_a = make_pet("对手A", [attack_a, attack_b])
        opponent_b = make_pet("对手B", [attack_a, attack_b])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent_a, opponent_b], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=anger),
            Action(type=ActionType.USE_SKILL, skill=attack_a),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.SWITCH_PET, target_index=1),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.USE_SKILL, skill=attack_b),
        )

        self.assertEqual(state.opponent.get_active_pet().current_energy, 6)

    def test_preventive_priority_and_next_attack_buffs_are_consumed(self):
        preventive = make_skill("有效预防", energy=1, category=SkillCategory.DEFENSE, counters=["attack"])
        wait = make_skill("待机", energy=1, category=SkillCategory.STATUS)
        ambush = make_skill("伺机而动", energy=1)
        attack = make_skill("攻击", power=30, energy=2, category=SkillCategory.ATTACK)
        enemy_attack = make_skill("敌攻", power=30, energy=2, category=SkillCategory.ATTACK)

        slow_template_skills = [preventive, wait, ambush, attack]
        player = make_pet("慢速方", slow_template_skills)
        player.stats["速度"] = 50
        opponent = make_pet("对手", [enemy_attack])
        opponent.stats["速度"] = 120
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=preventive),
            Action(type=ActionType.USE_SKILL, skill=enemy_attack),
        )
        self.assertEqual(state.player.get_active_pet().get_runtime_flag('_next_skill_priority_bonus', 0), 1)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=wait),
            Action(type=ActionType.USE_SKILL, skill=enemy_attack),
        )
        self.assertIsNone(state.player.get_active_pet().get_runtime_flag('_next_skill_priority_bonus', None))

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=ambush),
            Action(type=ActionType.GATHER_ENERGY),
        )
        hp_before = state.opponent.get_active_pet().current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=attack),
            Action(type=ActionType.GATHER_ENERGY),
        )
        boosted_damage = hp_before - state.opponent.get_active_pet().current_hp
        self.assertGreater(boosted_damage, 30)
        self.assertIsNone(state.player.get_active_pet().get_runtime_flag('_next_attack_power_bonus_flat', None))

    def test_concentrate_restart_and_redirect_support_flags(self):
        concentrate = make_skill("集中", energy=1, category=SkillCategory.DEFENSE, counters=["attack"])
        redirect = make_skill("电磁偏转", energy=1, category=SkillCategory.DEFENSE, counters=["attack"])
        restart = make_skill("强制重启", energy=1, category=SkillCategory.STATUS, counters=["status"])
        attack = make_skill("攻击", power=20, energy=2, category=SkillCategory.ATTACK)
        status = make_skill("状态技", energy=1, category=SkillCategory.STATUS)
        player = make_pet("玩家", [concentrate, redirect, attack])
        teammate = make_pet("队友", [attack])
        opponent = make_pet("对手", [attack, status])
        state = BattleState(
            player=PlayerState(team=[player, teammate], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=concentrate),
            Action(type=ActionType.USE_SKILL, skill=attack),
        )
        self.assertEqual(state.player.active_index, 0)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=redirect),
            Action(type=ActionType.USE_SKILL, skill=attack),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=attack),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertLess(state.opponent.get_active_pet().current_hp, 60)

        state = BattleState(
            player=PlayerState(team=[make_pet("玩家", [restart])], active_index=0),
            opponent=PlayerState(team=[make_pet("对手", [status])], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=restart),
            Action(type=ActionType.USE_SKILL, skill=status),
        )
        self.assertEqual(state.opponent.active_index, 0)

    def test_bench_energy_gift_and_mark_growth_skills(self):
        nourish = make_skill("富养化", energy=1)
        gift = make_skill("击鼓传花", energy=1)
        supernova = make_skill(
            "超新星馈赠",
            energy=1,
            effects=[Effect(EffectType.APPLY_MARK, "opponent", -1, status_type=StatusEffectType.STAR_FALL_MARK.value, stacks=2)],
        )
        insight = make_skill("心灵洞悉", energy=1)
        player = make_pet("玩家", [nourish, gift, supernova, insight])
        player.stat_modifiers.physical_attack = 3
        bench = make_pet("后备", [attack := make_skill("攻击", power=20, energy=2, category=SkillCategory.ATTACK)])
        bench.current_energy = 4
        bench.is_alive = False
        opponent = make_pet("对手", [attack])
        state = BattleState(
            player=PlayerState(team=[player, bench], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=nourish),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.team[1].current_energy, 7)

        state.player.team[1].is_alive = True
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=gift),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.active_index, 1)
        self.assertEqual(state.player.get_active_pet().stat_modifiers.physical_attack, 3)

        state = BattleState(
            player=PlayerState(team=[make_pet("玩家", [supernova, insight])], active_index=0),
            opponent=PlayerState(team=[make_pet("对手", [attack])], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=supernova),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.opponent_negative_mark.stacks, 2)
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=supernova),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.opponent_negative_mark.stacks, 5)
        state.player_positive_mark = FieldMark(type_key=StatusEffectType.PHOTOSYNTHESIS_MARK.value, stacks=2, is_positive=True)
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=insight),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.opponent_negative_mark.stacks, 10)

    def test_power_up_sweet_endurance_toy_park_mercury_diffuse_and_qi(self):
        swift_attack = make_skill(
            "迅捷攻击",
            power=20,
            energy=2,
            category=SkillCategory.ATTACK,
            effects=[Effect(EffectType.SWIFT, "self", 0)],
        )
        power_up = make_skill("加大功率", energy=1)
        sweet = make_skill("甜心续航", energy=1)
        toy = make_skill("玩具乐园", energy=1)
        mercury = make_skill("水星水", power=40, energy=2, element="水", category=SkillCategory.ATTACK, damage_type=DamageType.MAGICAL, counters=["status"])
        diffuse = make_skill("漫反射", power=40, energy=2, element="火", category=SkillCategory.ATTACK)
        qi = make_skill("气沉丹田", energy=4, category=SkillCategory.DEFENSE, counters=["attack"])
        enemy_status = make_skill("敌方状态", energy=1)
        enemy_attack = make_skill("敌方攻击", power=20, energy=2, category=SkillCategory.ATTACK)

        player = make_pet("玩家", [power_up])
        bench = make_pet("后备", [swift_attack])
        bench.current_energy = 1
        opponent = make_pet("对手", [enemy_attack])
        state = BattleState(
            player=PlayerState(team=[player, bench], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=power_up),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.active_index, 1)
        self.assertEqual(state.player.get_active_pet().current_energy, 9)
        self.assertEqual(state.opponent.get_active_pet().current_hp, 100)

        player = make_cutable_pet("玩家", [sweet, toy])
        bench = make_cutable_pet("后备", [enemy_attack])
        opponent = make_cutable_pet("对手", [enemy_attack], hp=50)
        player.template.evolution = [{"name": "玩家幼态"}]
        bench.template.evolution = [{"name": "后备幼态"}]
        opponent.template.evolution = [{"name": "对手幼态"}]
        self.engine.data_loader.pets["玩家幼态"] = PetTemplate(
            id=101,
            name="玩家幼态",
            types=["普通"],
            stats={"生命": 80, "物攻": 80, "魔攻": 80, "物防": 80, "魔防": 80, "速度": 80},
            traits=[],
            learnable_skills=[],
            evolution=[],
        )
        self.engine.data_loader.pets["后备幼态"] = PetTemplate(
            id=102,
            name="后备幼态",
            types=["普通"],
            stats={"生命": 75, "物攻": 75, "魔攻": 75, "物防": 75, "魔防": 75, "速度": 75},
            traits=[],
            learnable_skills=[],
            evolution=[],
        )
        self.engine.data_loader.pets["对手幼态"] = PetTemplate(
            id=103,
            name="对手幼态",
            types=["普通"],
            stats={"生命": 70, "物攻": 70, "魔攻": 70, "物防": 70, "魔防": 70, "速度": 70},
            traits=[],
            learnable_skills=[],
            evolution=[],
        )
        player.current_hp = 60
        state = BattleState(
            player=PlayerState(team=[player, bench], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=sweet),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().current_hp, state.player.get_active_pet().max_hp)
        self.assertEqual(state.opponent.get_active_pet().current_hp, 63)
        self.assertEqual(getattr(state.player.get_active_pet(), 'cute_stacks', 0), 1)
        self.assertEqual(state.player.get_active_pet().template.name, "玩家幼态")
        self.assertEqual(state.opponent.get_active_pet().template.name, "对手幼态")

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=toy),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.team[1].stats["速度"], 95)
        self.assertEqual(getattr(state.player.team[1], 'cute_stacks', 0), 1)
        self.assertEqual(state.player.team[1].template.name, "后备幼态")

        player = make_pet("玩家", [mercury])
        opponent = make_pet("对手", [enemy_status], hp=100)
        player.stat_modifiers.magical_attack = -5
        opponent.stat_modifiers.magical_defense = 5
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
            weather='下雨',
        )
        hp_before = opponent.current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=mercury),
            Action(type=ActionType.USE_SKILL, skill=enemy_status),
        )
        self.assertLess(state.opponent.get_active_pet().current_hp, hp_before)

        fire_a = make_skill("火A", power=40, energy=2, element="火", category=SkillCategory.ATTACK)
        diffuse = make_skill("漫反射", power=40, energy=2, element="火", category=SkillCategory.ATTACK)
        player = make_pet("玩家", [fire_a, diffuse])
        opponent = make_pet("对手", [enemy_status], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        hp_before = opponent.current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=diffuse),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertLess(hp_before - state.opponent.get_active_pet().current_hp, 60)

        player = make_pet("玩家", [qi])
        opponent = make_pet("对手", [enemy_attack])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=qi),
            Action(type=ActionType.USE_SKILL, skill=enemy_attack),
        )
        self.assertEqual(state.player.get_active_pet().skills[0].energy_cost, 7)
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=qi),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().skills[0].energy_cost, 7)

    def test_take_thought_copy_and_compendium(self):
        enemy_pool_skill = make_skill("敌方库技能", power=50, energy=4, element="火", category=SkillCategory.ATTACK)
        self.engine.data_loader.skills["敌方库技能"] = copy.deepcopy(enemy_pool_skill)
        take_thought = make_skill("取念", energy=1)
        player = make_pet("玩家", [take_thought])
        opponent_active = make_pet("对手A", [make_skill("取念")])
        opponent_dead = make_pet("对手B", [enemy_pool_skill])
        opponent_dead.is_alive = False
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent_active, opponent_dead], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=take_thought),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().get_runtime_flag('_copied_skill_name'), "敌方库技能")
        self.assertLess(state.opponent.get_active_pet().current_hp, 100)
        self.assertEqual(state.player.get_active_pet().current_energy, 9)

        copy_skill = make_skill("复写", energy=1)
        learnable = make_skill("可学技能", power=40, energy=3, element="水", category=SkillCategory.ATTACK)
        self.engine.data_loader.skills["可学技能"] = copy.deepcopy(learnable)
        player = make_pet("玩家", [copy_skill])
        player.template.learnable_skills = ["复写", "可学技能"]
        opponent = make_pet("对手", [make_skill("待机")])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=copy_skill),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().get_runtime_flag('_copied_skill_name'), "可学技能")
        self.assertLess(state.opponent.get_active_pet().current_hp, 100)
        self.assertEqual(state.player.get_active_pet().current_energy, 9)

        attack_normal = make_skill("普通攻击", power=40, energy=2, element="普通", category=SkillCategory.ATTACK)
        expensive_normal = make_skill("昂贵普通", power=60, energy=5, element="普通", category=SkillCategory.ATTACK)
        compendium = make_skill("荟萃", energy=0, element="普通", category=SkillCategory.STATUS)
        player = make_pet("玩家", [compendium, attack_normal, expensive_normal])
        player.current_energy = 4
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=compendium),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertLess(state.opponent.get_active_pet().current_hp, 100)
        self.assertEqual(state.player.get_active_pet().current_energy, 0)

    def test_generic_slot_condition_stat_modifiers(self):
        slot_one_magic = make_skill("槽位魔攻增益", energy=1, category=SkillCategory.STATUS)
        slot_one_magic.desc = "本技能位于1号位时额外获得魔攻+60%。"
        slot_three_speed = make_skill("槽位速度增益", energy=1, category=SkillCategory.STATUS)
        slot_three_speed.desc = "本技能位于3号位时额外获得速度+40。"
        slot_three_enemy_debuff = make_skill("槽位敌方减防", energy=1, category=SkillCategory.STATUS)
        slot_three_enemy_debuff.desc = "本技能位于3号位时敌方获得魔防-60%。"
        slot_one_magic.effects, _ = self.engine.data_loader._parse_desc_to_effects(
            slot_one_magic.desc, slot_one_magic.category
        )
        slot_three_speed.effects, _ = self.engine.data_loader._parse_desc_to_effects(
            slot_three_speed.desc, slot_three_speed.category
        )
        slot_three_enemy_debuff.effects, _ = self.engine.data_loader._parse_desc_to_effects(
            slot_three_enemy_debuff.desc, slot_three_enemy_debuff.category
        )

        player = make_pet("玩家", [slot_one_magic, make_skill("填充"), slot_three_speed, slot_three_enemy_debuff])
        opponent = make_pet("对手", [make_skill("待机")])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=slot_one_magic),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().stat_modifiers.magical_attack, 6)

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=slot_three_speed),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().stats["速度"], 140)

        player = make_pet("玩家", [make_skill("填充"), make_skill("填充2"), slot_three_enemy_debuff])
        opponent = make_pet("对手", [make_skill("待机")])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=slot_three_enemy_debuff),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.opponent.get_active_pet().stat_modifiers.magical_defense, -6)

    def test_data_loader_uses_battle_data_description_field(self):
        root = Path.cwd() / "_tmp_loader_description_test"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir()
        try:
            (root / "battle_data.json").write_text(
                json.dumps(
                    {
                        "skills": {
                            "描述字段技能": {
                                "element": "普通",
                                "category": "状态",
                                "power": 0,
                                "energy_cost": 1,
                                "effects": [],
                                "counters": [],
                                "description": "本技能位于1号位时额外获得魔攻+60%。",
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "skills.json").write_text("{}", encoding="utf-8")
            (root / "type_chart.json").write_text(
                json.dumps({"types": ["普通"], "chart": [[1.0]]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "pets.json").write_text("[]", encoding="utf-8")

            loader = DataLoader(root)
            loader.load_all()

            skill = loader.skills["描述字段技能"]
            self.assertEqual(skill.desc, "本技能位于1号位时额外获得魔攻+60%。")
            self.assertTrue(any(effect.desc == "slot_1:魔攻" for effect in skill.effects))
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_raiden_storm_mirror_reflect_and_gale_combo(self):
        burst_poison = make_skill(
            "迸发毒击",
            power=20,
            energy=2,
            category=SkillCategory.ATTACK,
            effects=[
                Effect(EffectType.BURST, "self", 1),
                Effect(EffectType.APPLY_STATUS, "opponent", 2, status_type='poison', stacks=2),
            ],
        )
        raiden = make_skill(
            "雷暴",
            power=30,
            energy=2,
            element="电",
            category=SkillCategory.ATTACK,
            effects=[Effect(EffectType.BURST, "self", 1)],
        )
        player = make_pet("玩家", [burst_poison, raiden])
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state.player.get_active_pet().burst_turns_remaining = 1
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=burst_poison),
            Action(type=ActionType.GATHER_ENERGY),
        )
        state.player.get_active_pet().burst_turns_remaining = 1
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=raiden),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertGreater(state.opponent.get_active_pet().get_status_stacks(StatusEffectType.POISON), 0)

        burst_hit = make_skill(
            "迸发重击",
            power=60,
            energy=2,
            category=SkillCategory.ATTACK,
            effects=[Effect(EffectType.BURST, "self", 1)],
        )
        burst_mark = make_skill(
            "迸发印记",
            energy=2,
            category=SkillCategory.STATUS,
            effects=[Effect(EffectType.BURST, "self", 1)],
        )
        self.engine.data_loader.skills["迸发重击"] = copy.deepcopy(burst_hit)
        self.engine.data_loader.skills["迸发印记"] = copy.deepcopy(burst_mark)

        damage_player = make_pet("伤害迸发方", [burst_hit, raiden])
        damage_opponent = make_pet("对手", [make_skill("待机")], hp=300)
        damage_opponent.max_hp = 300
        damage_state = BattleState(
            player=PlayerState(team=[damage_player], active_index=0),
            opponent=PlayerState(team=[damage_opponent], active_index=0),
        )
        damage_state.player.get_active_pet().burst_turns_remaining = 1
        damage_state = self.engine.apply_action(
            damage_state,
            Action(type=ActionType.USE_SKILL, skill=burst_hit),
            Action(type=ActionType.GATHER_ENERGY),
        )
        hp_before_damage_raiden = damage_state.opponent.get_active_pet().current_hp
        damage_state.player.get_active_pet().burst_turns_remaining = 1
        damage_state = self.engine.apply_action(
            damage_state,
            Action(type=ActionType.USE_SKILL, skill=raiden),
            Action(type=ActionType.GATHER_ENERGY),
        )
        damage_raiden_loss = hp_before_damage_raiden - damage_state.opponent.get_active_pet().current_hp

        utility_player = make_pet("功能迸发方", [burst_mark, raiden])
        utility_opponent = make_pet("对手", [make_skill("待机")], hp=300)
        utility_opponent.max_hp = 300
        utility_state = BattleState(
            player=PlayerState(team=[utility_player], active_index=0),
            opponent=PlayerState(team=[utility_opponent], active_index=0),
        )
        utility_state.player.get_active_pet().burst_turns_remaining = 1
        utility_state = self.engine.apply_action(
            utility_state,
            Action(type=ActionType.USE_SKILL, skill=burst_mark),
            Action(type=ActionType.GATHER_ENERGY),
        )
        hp_before_utility_raiden = utility_state.opponent.get_active_pet().current_hp
        utility_state.player.get_active_pet().burst_turns_remaining = 1
        utility_state = self.engine.apply_action(
            utility_state,
            Action(type=ActionType.USE_SKILL, skill=raiden),
            Action(type=ActionType.GATHER_ENERGY),
        )
        utility_raiden_loss = hp_before_utility_raiden - utility_state.opponent.get_active_pet().current_hp

        self.assertGreater(damage_raiden_loss, utility_raiden_loss)

        enemy_attack = make_skill("敌方斩击", power=40, energy=3, category=SkillCategory.ATTACK)
        self.engine.data_loader.skills["敌方斩击"] = copy.deepcopy(enemy_attack)
        mirror = make_skill(
            "镜像反射",
            energy=1,
            category=SkillCategory.DEFENSE,
            counters=["attack"],
            effects=[Effect(EffectType.COUNTER, "opponent", 0, desc="attack:本技能变为被应对的技能")],
        )
        player = make_pet("玩家", [mirror])
        opponent = make_pet("对手", [enemy_attack])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=mirror),
            Action(type=ActionType.USE_SKILL, skill=enemy_attack),
        )
        self.assertEqual(state.player.get_active_pet().skills[0].name, "敌方斩击")

        swift_a = make_skill("迅捷A", power=20, energy=2, category=SkillCategory.ATTACK, effects=[Effect(EffectType.SWIFT, "self", 0)])
        swift_b = make_skill("迅捷B", power=20, energy=4, category=SkillCategory.ATTACK, effects=[Effect(EffectType.SWIFT, "self", 0)])
        gale = make_skill("疾风连袭", energy=1)
        player = make_pet("玩家", [swift_a, gale, swift_b])
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=swift_b),
            Action(type=ActionType.GATHER_ENERGY),
        )
        state.player.get_active_pet().current_energy = 10
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=swift_a),
            Action(type=ActionType.GATHER_ENERGY),
        )
        hp_before = state.opponent.get_active_pet().current_hp
        state.player.get_active_pet().current_energy = 10
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=gale),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertLess(state.opponent.get_active_pet().current_hp, hp_before)
        self.assertEqual(state.player.get_active_pet().skills[1].energy_cost, 2)

    def test_overload_circuit_reenters_immediately_after_use(self):
        overload = make_skill("过载回路", energy=1)
        attack = make_skill("连发", power=30, energy=2, category=SkillCategory.ATTACK, hits=1)
        player = make_pet("玩家", [overload, attack])
        player.stats["速度"] = 200
        player.stat_modifiers.physical_attack = 3
        enemy_attack = make_skill("敌方攻击", power=20, energy=1, category=SkillCategory.ATTACK, hits=1)
        opponent = make_pet("对手", [enemy_attack])
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state.player.get_active_pet().stat_modifiers.physical_attack, 3)
        self.assertIsNone(state.player.get_active_pet().get_runtime_flag('_overload_circuit_bonus_turn'))

        state.player.get_active_pet().stat_modifiers.physical_attack = 3
        hp_before = state.player.get_active_pet().current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=overload),
            Action(type=ActionType.USE_SKILL, skill=enemy_attack),
        )
        refreshed_pet = state.player.get_active_pet()
        self.assertEqual(refreshed_pet.stat_modifiers.physical_attack, 0)
        self.assertLess(refreshed_pet.current_hp, hp_before)
        self.assertEqual(refreshed_pet.get_runtime_flag('_overload_circuit_bonus_turn'), state.turn)

        hp_before = state.opponent.get_active_pet().current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=attack),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertLess(state.opponent.get_active_pet().current_hp, hp_before)
        self.assertIsNone(state.player.get_active_pet().get_runtime_flag('_overload_circuit_bonus_turn'))

    def test_soft_hidden_needle_uses_any_damage_last_turn_not_only_skill_damage(self):
        needle = make_skill("绵里藏针", power=50, energy=2, element="龙", category=SkillCategory.ATTACK, damage_type=DamageType.MAGICAL)
        player = make_pet("玩家", [needle])
        opponent = make_pet("对手", [make_skill("待机")], hp=100)
        opponent.add_status(StatusEffectType.BURN, 2)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.GATHER_ENERGY),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertTrue(state.opponent.get_active_pet().get_runtime_flag('_took_any_damage_last_turn'))

        hp_before = state.opponent.get_active_pet().current_hp
        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=needle),
            Action(type=ActionType.GATHER_ENERGY),
        )
        damage = hp_before - state.opponent.get_active_pet().current_hp
        self.assertGreater(damage, 0)
        self.assertEqual(state.player.get_active_pet().skills[0].base_power, 50)

    def test_moist_mark_keeps_panel_actions_and_actual_spend_consistent(self):
        strike = make_skill(
            "TestStrike",
            power=60,
            energy=4,
            category=SkillCategory.ATTACK,
        )
        player = make_pet("Player", [strike], hp=100)
        player.current_energy = 3
        opponent = make_pet("Opponent", [make_skill("Wait")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
            player_positive_mark=FieldMark(
                type_key=StatusEffectType.MOIST_MARK.value,
                stacks=1,
                is_positive=True,
            ),
        )

        legal_actions = ActionGenerator.generate_actions(state, True)
        skill_names = [
            action.skill.name for action in legal_actions
            if action.type == ActionType.USE_SKILL and action.skill
        ]
        self.assertIn("TestStrike", skill_names)

        panel = _build_action_panel(state, True, legal_actions)
        self.assertEqual(panel["skills"][0]["current_energy_cost"], 3)

        new_state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=strike),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(new_state.player.get_active_pet().current_energy, 0)

    def test_refraction_reduced_cost_matches_panel_and_actual_spend(self):
        refraction = make_refraction_skill()
        bubble = make_skill("Bubble", element="水")
        player = make_pet("DiMo", [refraction, bubble], hp=100)
        opponent = make_pet("Opponent", [make_skill("Wait")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
            player_positive_mark=FieldMark(
                type_key=StatusEffectType.MOIST_MARK.value,
                stacks=1,
                is_positive=True,
            ),
        )

        state = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=refraction),
            Action(type=ActionType.GATHER_ENERGY),
        )
        attacker_after = state.player.get_active_pet()
        self.assertEqual(attacker_after.skills[0].energy_cost, 3)
        self.assertEqual(attacker_after.current_energy, 7)

        legal_actions = ActionGenerator.generate_actions(state, True)
        panel = _build_action_panel(state, True, legal_actions)
        self.assertEqual(panel["skills"][0]["current_energy_cost"], 2)

        attacker_after.current_energy = 2
        state_after_second_use = self.engine.apply_action(
            state,
            Action(type=ActionType.USE_SKILL, skill=attacker_after.skills[0]),
            Action(type=ActionType.GATHER_ENERGY),
        )
        self.assertEqual(state_after_second_use.player.get_active_pet().current_energy, 0)

    def test_strategy_uses_mark_adjusted_energy_costs(self):
        analysis_engine = GameAnalysisEngine()
        expensive = make_skill(
            "ExpensiveStrike",
            power=80,
            energy=4,
            element="普通",
            category=SkillCategory.ATTACK,
        )
        cheap = make_skill(
            "CheapStrike",
            power=10,
            energy=1,
            element="普通",
            category=SkillCategory.ATTACK,
        )
        player = make_pet("Player", [expensive, cheap], hp=100)
        player.current_energy = 3
        opponent = make_pet("Opponent", [make_skill("Wait")], hp=100)
        state = BattleState(
            player=PlayerState(team=[player], active_index=0),
            opponent=PlayerState(team=[opponent], active_index=0),
            player_positive_mark=FieldMark(
                type_key=StatusEffectType.MOIST_MARK.value,
                stacks=1,
                is_positive=True,
            ),
        )
        state.player.team_state.willpower_strike_uses = 0

        best_action, _ = analysis_engine.search_engine.find_best_action(state, depth=1, time_limit=1.0)
        self.assertIsNotNone(best_action)
        self.assertEqual(best_action.type, ActionType.USE_SKILL)
        self.assertEqual(best_action.skill.name, "ExpensiveStrike")

    def test_strategy_uses_dragon_bite_mark_damage_bonus(self):
        analysis_engine = GameAnalysisEngine()
        base_bite_skill = make_skill(
            "DragonFiveCost",
            power=70,
            energy=5,
            element="普通",
            category=SkillCategory.ATTACK,
        )
        marked_bite_skill = make_skill(
            "DragonFiveCost",
            power=70,
            energy=5,
            element="普通",
            category=SkillCategory.ATTACK,
        )

        base_state = BattleState(
            player=PlayerState(team=[make_pet("Player", [base_bite_skill], hp=100)], active_index=0),
            opponent=PlayerState(team=[make_pet("Opponent", [make_skill("Wait")], hp=100)], active_index=0),
        )
        marked_state = BattleState(
            player=PlayerState(team=[make_pet("Player", [marked_bite_skill], hp=100)], active_index=0),
            opponent=PlayerState(team=[make_pet("Opponent", [make_skill("Wait")], hp=100)], active_index=0),
            player_positive_mark=FieldMark(
                type_key=StatusEffectType.DRAGON_BITE_MARK.value,
                stacks=1,
                is_positive=True,
            ),
        )
        for state in (base_state, marked_state):
            state.player.team_state.willpower_strike_uses = 0

        base_player = base_state.player.get_active_pet()
        marked_player = marked_state.player.get_active_pet()

        base_dragon_state = analysis_engine.battle_engine.apply_action(
            base_state,
            Action(type=ActionType.USE_SKILL, skill=base_player.skills[0]),
            Action(type=ActionType.GATHER_ENERGY),
        )
        marked_dragon_state = analysis_engine.battle_engine.apply_action(
            marked_state,
            Action(type=ActionType.USE_SKILL, skill=marked_player.skills[0]),
            Action(type=ActionType.GATHER_ENERGY),
        )

        base_dragon_score = analysis_engine.evaluator.evaluate(base_dragon_state)
        marked_dragon_score = analysis_engine.evaluator.evaluate(marked_dragon_state)
        base_damage = 100 - base_dragon_state.opponent.get_active_pet().current_hp
        marked_damage = 100 - marked_dragon_state.opponent.get_active_pet().current_hp

        self.assertGreater(marked_damage, base_damage)
        self.assertGreater(marked_dragon_score, base_dragon_score)

    def test_dragon_bite_mark_uses_effective_energy_cost_threshold(self):
        base_attack = make_skill(
            "DragonThresholdStrike",
            power=70,
            energy=5,
            element="普通",
            category=SkillCategory.ATTACK,
        )
        reduced_attack = make_skill(
            "DragonThresholdStrike",
            power=70,
            energy=5,
            element="普通",
            category=SkillCategory.ATTACK,
        )
        reduced_attack.desc = "本技能被动额外-1能耗"
        base_state = BattleState(
            player=PlayerState(team=[make_pet("Player", [copy.deepcopy(base_attack)], hp=100)], active_index=0),
            opponent=PlayerState(team=[make_pet("Opponent", [make_skill("Wait")], hp=100)], active_index=0),
        )
        reduced_state = BattleState(
            player=PlayerState(team=[make_pet("Player", [copy.deepcopy(reduced_attack)], hp=100)], active_index=0),
            opponent=PlayerState(team=[make_pet("Opponent", [make_skill("Wait")], hp=100)], active_index=0),
            player_positive_mark=FieldMark(
                type_key=StatusEffectType.DRAGON_BITE_MARK.value,
                stacks=1,
                is_positive=True,
            ),
        )
        for state in (base_state, reduced_state):
            state.player.team_state.willpower_strike_uses = 0

        base_result = self.engine.apply_action(
            base_state,
            Action(type=ActionType.USE_SKILL, skill=base_state.player.get_active_pet().skills[0]),
            Action(type=ActionType.GATHER_ENERGY),
        )
        reduced_result = self.engine.apply_action(
            reduced_state,
            Action(type=ActionType.USE_SKILL, skill=reduced_state.player.get_active_pet().skills[0]),
            Action(type=ActionType.GATHER_ENERGY),
        )

        base_damage = 100 - base_result.opponent.get_active_pet().current_hp
        reduced_damage = 100 - reduced_result.opponent.get_active_pet().current_hp
        self.assertEqual(reduced_result.player.get_active_pet().current_energy, 6)
        self.assertEqual(reduced_damage, base_damage)

    def test_strategy_framework_adds_conservative_placeholder_trait_value(self):
        analysis_engine = GameAnalysisEngine()
        plain_pet = make_pet("Plain", [make_skill("Wait")], hp=100)
        trait_pet = make_pet("TraitPet", [make_skill("Wait")], hp=100)
        trait_pet.template.traits = [Trait(name="不朽", desc="placeholder")]
        opponent_plain = make_pet("Opponent", [make_skill("Wait")], hp=100)
        opponent_trait = make_pet("Opponent", [make_skill("Wait")], hp=100)

        plain_state = BattleState(
            player=PlayerState(team=[plain_pet], active_index=0),
            opponent=PlayerState(team=[opponent_plain], active_index=0),
        )
        trait_state = BattleState(
            player=PlayerState(team=[trait_pet], active_index=0),
            opponent=PlayerState(team=[opponent_trait], active_index=0),
        )

        self.assertGreater(
            analysis_engine.evaluator.evaluate(trait_state),
            analysis_engine.evaluator.evaluate(plain_state),
        )

if __name__ == "__main__":
    unittest.main()
