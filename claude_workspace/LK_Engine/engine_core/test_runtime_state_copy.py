import unittest
from dataclasses import fields

from core.models import (
    BattleState,
    DamageType,
    FieldMark,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
    TeamState,
    Trait,
)


def make_skill(name: str) -> Skill:
    return Skill(
        name=name,
        element="普通",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=60,
        energy_cost=3,
    )


def make_pet(name: str) -> PetInstance:
    template = PetTemplate(
        id=1,
        name=name,
        types=["普通"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 100, "魔防": 100, "速度": 100},
        traits=[Trait(name="测试特性", desc="")],
        learnable_skills=[],
    )
    return PetInstance(
        template=template,
        current_hp=100,
        max_hp=100,
        stats=template.stats.copy(),
        skills=[make_skill("撞击")],
    )


class RuntimeStateCopyTest(unittest.TestCase):
    def _assert_dataclass_field_values_equal(self, left, right):
        for field_info in fields(left):
            self.assertEqual(
                getattr(left, field_info.name),
                getattr(right, field_info.name),
                f"field mismatch: {field_info.name}",
            )

    def test_pet_runtime_flags_preserved_on_copy(self):
        pet = make_pet("火花")
        pet._holy_knight_power = True
        pet._doji_power_bonus = 20
        pet._immortal_death_mark = 3
        pet._current_skill_name = "撞击"

        copied = pet.copy()

        self.assertTrue(copied._holy_knight_power)
        self.assertEqual(copied._doji_power_bonus, 20)
        self.assertEqual(copied._immortal_death_mark, 3)
        self.assertEqual(copied._current_skill_name, "撞击")
        self.assertIsNot(copied.runtime_flags, pet.runtime_flags)

    def test_runtime_flag_helpers_and_legacy_dynamic_access_are_compatible(self):
        pet = make_pet("火花")
        pet.set_runtime_flag("_flag_a", True)
        self.assertTrue(pet._flag_a)
        pet._flag_b = 7
        self.assertEqual(pet.get_runtime_flag("_flag_b"), 7)
        self.assertEqual(pet.pop_runtime_flag("_flag_b"), 7)
        self.assertFalse("_flag_b" in pet.runtime_flags)

    def test_battle_state_copy_preserves_runtime_flags(self):
        player_pet = make_pet("火花")
        opponent_pet = make_pet("喵呜")
        player_pet._swift_low_cost = True
        opponent_pet._cocooned = True

        state = BattleState(
            player=PlayerState(team=[player_pet], active_index=0),
            opponent=PlayerState(team=[opponent_pet], active_index=0),
        )

        copied = state.copy()

        self.assertTrue(copied.player.get_active_pet()._swift_low_cost)
        self.assertTrue(copied.opponent.get_active_pet()._cocooned)
        copied.player.get_active_pet()._swift_low_cost = False
        self.assertTrue(state.player.get_active_pet()._swift_low_cost)

    def test_team_state_copy_keeps_all_declared_fields(self):
        team_state = TeamState(
            devotion_poison=2,
            devotion_lifesteal=30,
            devotion_combo=1,
            devotion_power=50,
            devotion_energy=2,
            leader_evolution_uses=0,
            willpower_strike_uses=1,
            earth_skill_count=3,
            ice_skill_count=4,
            fire_skill_count=5,
            water_skill_count=6,
            status_skill_count=7,
            counter_success_count=8,
            defense_skill_count=9,
            gather_energy_count=10,
            switch_count=11,
            next_pet_gifts={"免疫冻结", "回复20%生命"},
        )

        copied = team_state.copy()

        self._assert_dataclass_field_values_equal(team_state, copied)
        self.assertIsNot(team_state.next_pet_gifts, copied.next_pet_gifts)

    def test_battle_state_copy_keeps_all_declared_fields_and_mutables_independent(self):
        player_pet = make_pet("火花")
        opponent_pet = make_pet("喵呜")
        state = BattleState(
            player=PlayerState(team=[player_pet], active_index=0),
            opponent=PlayerState(team=[opponent_pet], active_index=0),
            turn=7,
            weather="晴天",
            field_effects={"迷雾": 2},
            player_positive_mark=FieldMark(type_key="光合印记", stacks=1, is_positive=True),
            opponent_negative_mark=FieldMark(type_key="星陨印记", stacks=3, is_positive=False),
            player_hearts=3,
            opponent_hearts=2,
            max_turns=60,
        )

        copied = state.copy()

        self.assertEqual(state.turn, copied.turn)
        self.assertEqual(state.weather, copied.weather)
        self.assertEqual(state.field_effects, copied.field_effects)
        self.assertEqual(state.player_hearts, copied.player_hearts)
        self.assertEqual(state.opponent_hearts, copied.opponent_hearts)
        self.assertEqual(state.max_turns, copied.max_turns)
        self.assertEqual(state.player_positive_mark.type_key, copied.player_positive_mark.type_key)
        self.assertEqual(state.opponent_negative_mark.stacks, copied.opponent_negative_mark.stacks)

        copied.field_effects["迷雾"] = 99
        copied.player_positive_mark.stacks = 5
        copied.player.team_state.switch_count = 42

        self.assertEqual(state.field_effects["迷雾"], 2)
        self.assertEqual(state.player_positive_mark.stacks, 1)
        self.assertEqual(state.player.team_state.switch_count, 0)


if __name__ == "__main__":
    unittest.main()
