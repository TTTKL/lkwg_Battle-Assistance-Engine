from core.models import (
    Action,
    ActionType,
    BattleState,
    DamageType,
    Effect,
    EffectType,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
    TeamState,
    Trait,
)
from data_loader import DataLoader
from engine.action_generator import ActionGenerator
from engine.extended_battle_engine import ExtendedBattleEngine
from engine.slot_effects import SlotEffectsProcessor


def make_pet(name: str, trait_names: list[str], skills: list[Skill], energy: int = 10) -> PetInstance:
    template = PetTemplate(
        id=1,
        name=name,
        types=["普通"],
        stats={"生命": 200, "物攻": 100, "魔攻": 100, "物防": 100, "魔防": 100, "速度": 100},
        traits=[Trait(name=t, desc=t) for t in trait_names],
        learnable_skills=[],
    )
    return PetInstance(
        template=template,
        current_hp=200,
        max_hp=200,
        stats=template.stats.copy(),
        skills=skills,
        current_energy=energy,
    )


def make_attack(name: str, energy: int = 3, effects=None) -> Skill:
    return Skill(
        name=name,
        element="普通",
        category=SkillCategory.ATTACK,
        damage_type=DamageType.PHYSICAL,
        base_power=40,
        energy_cost=energy,
        effects=effects or [],
    )


def run_turn(player_pet: PetInstance, opponent_pet: PetInstance, player_action: Action, opponent_action: Action) -> BattleState:
    engine = ExtendedBattleEngine(DataLoader())
    state = BattleState(
        player=PlayerState(team=[player_pet], active_index=0, team_state=TeamState()),
        opponent=PlayerState(team=[opponent_pet], active_index=0, team_state=TeamState()),
    )
    return engine.apply_action(state, player_action, opponent_action)


def test_convection_reverses_permanent_cost_reduction() -> None:
    buff_skill = make_attack(
        "反转改耗",
        effects=[Effect(type=EffectType.ENERGY_RESTORE, target="self", value=-1, desc="energy_cost_permanent")],
    )
    ally_skill = make_attack("普通技", energy=3)
    player = make_pet("对流宠", ["对流"], [buff_skill, ally_skill])
    opponent = make_pet("对手", [], [make_attack("挨打")])

    result = run_turn(
        player,
        opponent,
        Action(type=ActionType.USE_SKILL, skill=buff_skill),
        Action(type=ActionType.GATHER_ENERGY),
    )
    costs = [sk.energy_cost for sk in result.player.get_active_pet().skills]
    assert costs == [4, 4], costs


def test_convection_reverses_next_skill_discount_in_action_generator() -> None:
    player = make_pet(
        "对流宠",
        ["对流"],
        [make_attack("高耗技", energy=3), make_attack("备用技", energy=1)],
        energy=3,
    )
    player.next_skill_energy_discount = 6
    opponent = make_pet("对手", [], [make_attack("挨打")])
    state = BattleState(
        player=PlayerState(team=[player], active_index=0, team_state=TeamState()),
        opponent=PlayerState(team=[opponent], active_index=0, team_state=TeamState()),
    )

    actions = ActionGenerator().generate_actions(state, True)
    skill_names = [a.skill.name for a in actions if a.type == ActionType.USE_SKILL]
    effective_cost = SlotEffectsProcessor.get_effective_energy_cost(player, player.skills[0])

    assert effective_cost == 9, effective_cost
    assert "高耗技" not in skill_names, skill_names
    assert "备用技" not in skill_names, skill_names


def test_convection_reverses_enemy_cost_increase() -> None:
    noisy_skill = make_attack(
        "reverse-cost-up",
        effects=[Effect(type=EffectType.ENERGY_RESTORE, target="opponent", value=1, desc="energy_cost_permanent")],
    )
    player = make_pet("caster", [], [noisy_skill])
    opponent_skill = make_attack("target-skill", energy=3)
    opponent = make_pet("convection-target", ["对流"], [opponent_skill])

    result = run_turn(
        player,
        opponent,
        Action(type=ActionType.USE_SKILL, skill=noisy_skill),
        Action(type=ActionType.GATHER_ENERGY),
    )
    assert result.opponent.get_active_pet().skills[0].energy_cost == 2


if __name__ == "__main__":
    test_convection_reverses_permanent_cost_reduction()
    test_convection_reverses_next_skill_discount_in_action_generator()
    test_convection_reverses_enemy_cost_increase()
    print("convection trait tests passed")
