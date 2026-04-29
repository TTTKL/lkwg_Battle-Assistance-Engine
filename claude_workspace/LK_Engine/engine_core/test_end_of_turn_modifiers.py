from core.models import (
    Action,
    ActionType,
    BattleState,
    DamageType,
    PetInstance,
    PetTemplate,
    PlayerState,
    Skill,
    SkillCategory,
    TeamState,
    Trait,
)
from core.status_effects import StatusEffectType
from data_loader import DataLoader
from engine.extended_battle_engine import ExtendedBattleEngine
from engine.status_processor import StatusProcessor


def make_pet(name: str, traits=None, hp: int = 100) -> PetInstance:
    template = PetTemplate(
        id=1,
        name=name,
        types=["普通"],
        stats={"生命": 100, "物攻": 100, "魔攻": 100, "物防": 100, "魔防": 100, "速度": 100},
        traits=traits or [],
        learnable_skills=[],
    )
    return PetInstance(
        template=template,
        current_hp=hp,
        max_hp=100,
        stats=template.stats.copy(),
        skills=[
            Skill(
                name="测试攻击",
                element="普通",
                category=SkillCategory.ATTACK,
                damage_type=DamageType.PHYSICAL,
                base_power=10,
                energy_cost=1,
            )
        ],
        current_energy=10,
    )


def run_end_turn(state: BattleState) -> BattleState:
    engine = ExtendedBattleEngine(DataLoader())
    gather = Action(type=ActionType.GATHER_ENERGY)
    return engine.apply_action(state, gather, gather)


def test_dual_lightspeed_doubles_status_end_of_turn() -> None:
    player = make_pet("光速方", traits=[Trait(name="双向光速", desc="")])
    opponent = make_pet("中毒方")
    player.add_status(StatusEffectType.POISON, 1)
    opponent.add_status(StatusEffectType.POISON, 1)

    state = BattleState(
        player=PlayerState(team=[player], active_index=0, team_state=TeamState()),
        opponent=PlayerState(team=[opponent], active_index=0, team_state=TeamState()),
    )
    new_state = run_end_turn(state)

    assert new_state.player.get_active_pet().current_hp == 94
    assert new_state.opponent.get_active_pet().current_hp == 94


def test_fall_reduces_end_of_turn_to_zero() -> None:
    player = make_pet("陨落方", traits=[Trait(name="陨落", desc="")])
    opponent = make_pet("中毒方")
    player.add_status(StatusEffectType.POISON, 1)
    opponent.add_status(StatusEffectType.POISON, 1)

    state = BattleState(
        player=PlayerState(team=[player], active_index=0, team_state=TeamState()),
        opponent=PlayerState(team=[opponent], active_index=0, team_state=TeamState()),
    )
    new_state = run_end_turn(state)

    assert new_state.player.get_active_pet().current_hp == 100
    assert new_state.opponent.get_active_pet().current_hp == 100


def test_dual_lightspeed_doubles_trait_end_of_turn() -> None:
    player = make_pet(
        "光速花灵",
        traits=[Trait(name="双向光速", desc=""), Trait(name="花精灵", desc="")],
    )
    opponent = make_pet("对手")

    state = BattleState(
        player=PlayerState(team=[player], active_index=0, team_state=TeamState()),
        opponent=PlayerState(team=[opponent], active_index=0, team_state=TeamState()),
    )
    new_state = run_end_turn(state)

    impact_count = StatusProcessor(DataLoader()).get_devotion_impact_count(new_state.player.team_state)
    assert impact_count == 2


if __name__ == "__main__":
    test_dual_lightspeed_doubles_status_end_of_turn()
    test_fall_reduces_end_of_turn_to_zero()
    test_dual_lightspeed_doubles_trait_end_of_turn()
    print("end of turn modifier tests passed")
