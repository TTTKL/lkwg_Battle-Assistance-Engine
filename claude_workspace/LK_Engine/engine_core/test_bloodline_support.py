from core.models import (
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
from engine.action_generator import ActionGenerator
from engine.trait_processor import TraitProcessor


def make_template(name: str, bloodline: str = "unknown", traits=None) -> PetTemplate:
    return PetTemplate(
        id=1,
        name=name,
        types=["光"],
        stats={"生命": 200, "物攻": 100, "魔攻": 100, "物防": 100, "魔防": 100, "速度": 100},
        traits=traits or [],
        learnable_skills=[],
        bloodline=bloodline,
    )


def make_pet(name: str, bloodline: str = "unknown", traits=None, energy: int = 10) -> PetInstance:
    template = make_template(name, bloodline=bloodline, traits=traits)
    return PetInstance(
        template=template,
        current_hp=200,
        max_hp=200,
        stats=template.stats.copy(),
        skills=[
            Skill(
                name="测试攻击",
                element="光",
                category=SkillCategory.ATTACK,
                damage_type=DamageType.MAGICAL,
                base_power=100,
                energy_cost=2,
            )
        ],
        current_energy=energy,
    )


def test_leader_bloodline_gates_leader_evolution() -> None:
    generator = ActionGenerator()

    leader_pet = make_pet("首领宠", bloodline="leader")
    state = BattleState(
        player=PlayerState(team=[leader_pet], active_index=0, team_state=TeamState(leader_evolution_uses=1)),
        opponent=PlayerState(team=[make_pet("对手")], active_index=0),
    )
    action_types = {action.type for action in generator.generate_actions(state, True)}
    assert ActionType.LEADER_EVOLUTION in action_types

    normal_pet = make_pet("普通宠", bloodline="element:光")
    normal_state = BattleState(
        player=PlayerState(team=[normal_pet], active_index=0, team_state=TeamState(leader_evolution_uses=1)),
        opponent=PlayerState(team=[make_pet("对手")], active_index=0),
    )
    normal_action_types = {action.type for action in generator.generate_actions(normal_state, True)}
    assert ActionType.LEADER_EVOLUTION not in normal_action_types


def test_full_hp_still_can_gather_energy() -> None:
    generator = ActionGenerator()
    pet = make_pet("满血宠", bloodline="leader", energy=10)
    state = BattleState(
        player=PlayerState(team=[pet], active_index=0, team_state=TeamState(leader_evolution_uses=1)),
        opponent=PlayerState(team=[make_pet("对手")], active_index=0),
    )
    action_types = {action.type for action in generator.generate_actions(state, True)}
    assert ActionType.GATHER_ENERGY in action_types


def test_moonlight_judgement_uses_leader_bloodline() -> None:
    trait_processor = TraitProcessor()
    attacker = make_pet("月光审判宠", traits=[Trait(name="月光审判", desc="")])
    defender = make_pet("首领对手", bloodline="leader")
    skill = attacker.skills[0]

    boosted = trait_processor.modify_skill_power(attacker, defender, skill, skill.base_power, True, None)
    assert boosted == 200


def test_heavenly_clarity_uses_polluted_bloodline() -> None:
    trait_processor = TraitProcessor()
    attacker = make_pet("天通地明宠", traits=[Trait(name="天通地明", desc="")])
    defender = make_pet("污染对手", bloodline="polluted")
    skill = attacker.skills[0]

    boosted = trait_processor.modify_skill_power(attacker, defender, skill, skill.base_power, True, None)
    assert boosted == 200


def test_pink_starlight_uses_foreign_element_bloodline() -> None:
    trait_processor = TraitProcessor()
    attacker = make_pet(
        "绒粉星光宠",
        bloodline="element:光",
        traits=[Trait(name="绒粉星光", desc="")],
    )
    attacker.template.types = ["光"]
    defender = make_pet("异系血脉对手", bloodline="element:火")
    skill = attacker.skills[0]

    boosted = trait_processor.modify_skill_power(attacker, defender, skill, skill.base_power, True, None)
    assert boosted == 200


if __name__ == "__main__":
    test_leader_bloodline_gates_leader_evolution()
    test_full_hp_still_can_gather_energy()
    test_moonlight_judgement_uses_leader_bloodline()
    test_heavenly_clarity_uses_polluted_bloodline()
    test_pink_starlight_uses_foreign_element_bloodline()
    print("bloodline support tests passed")
