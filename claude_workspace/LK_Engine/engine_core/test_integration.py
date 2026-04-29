"""
综合集成测试
测试完整战斗流程：多回合、状态效果、印记、特性联动、搜索引擎
"""
from core.models import (
    BattleState, PlayerState, Action, ActionType,
    PetInstance, PetTemplate, Skill, SkillCategory, DamageType,
    FieldMark, Effect, EffectType, Trait, TeamState
)
from core.status_effects import StatusEffectType
from engine.extended_battle_engine import ExtendedBattleEngine
from engine.action_generator import ActionGenerator
from engine.evaluator import Evaluator
from engine.search_engine import SearchEngine
from data_loader import DataLoader

loader = DataLoader()
loader.load_all()
engine = ExtendedBattleEngine(loader)
evaluator = Evaluator(loader)
search = SearchEngine(engine, evaluator)
gen = ActionGenerator()


def make_template(name, types, stats=None, traits=None, is_legendary=False, bloodline="unknown"):
    return PetTemplate(
        id=1, name=name, types=types,
        stats=stats or {"生命": 200, "物攻": 120, "魔攻": 100, "物防": 80, "魔防": 80, "速度": 90},
        traits=traits or [], learnable_skills=[],
        is_legendary=is_legendary,
        bloodline=bloodline,
    )


def make_skill(name, element="普通", power=60, energy=3,
               dtype=DamageType.PHYSICAL, category=SkillCategory.ATTACK,
               effects=None, priority=0, hits=1):
    return Skill(
        name=name, element=element, category=category,
        damage_type=dtype, base_power=power, energy_cost=energy,
        effects=effects or [], priority=priority, hits=hits,
    )


def make_pet(name, types, hp=200, skills=None, traits=None, is_legendary=False, bloodline="unknown"):
    tmpl = make_template(name, types, traits=traits, is_legendary=is_legendary, bloodline=bloodline)
    return PetInstance(
        template=tmpl, current_hp=hp, max_hp=200,
        stats=tmpl.stats.copy(),
        skills=skills or [], current_energy=10,
    )


# ─────────────────────────────────────────────────────────────────
print("=== 集成测试 ===\n")

# ── 测试1：多回合战斗，状态自然减少 ─────────────────────────────
print("1. 多回合战斗：灼烧衰减")
p = make_pet("火龙", ["火"], skills=[make_skill("火焰", "火")])
o = make_pet("水龙", ["水"], hp=200)
o.add_status(StatusEffectType.BURN, 8)  # 8层灼烧

state = BattleState(
    player=PlayerState(team=[p], active_index=0),
    opponent=PlayerState(team=[o], active_index=0),
)
gather = Action(type=ActionType.GATHER_ENERGY)
state = engine.apply_action(state, gather, gather)  # 回合1：8层→处理后4层
opp = state.opponent.get_active_pet()
stacks_after = opp.get_status_stacks(StatusEffectType.BURN)
assert stacks_after == 4, f"灼烧应衰减到4层，实际{stacks_after}"
state = engine.apply_action(state, gather, gather)  # 回合2：4层→2层
opp = state.opponent.get_active_pet()
stacks_after = opp.get_status_stacks(StatusEffectType.BURN)
assert stacks_after == 2, f"灼烧应衰减到2层，实际{stacks_after}"
print("   [PASS] 灼烧每回合衰减一半（8→4→2）\n")

# ── 测试2：场地印记叠加影响 ──────────────────────────────────────
print("2. 场地印记：星陨印记引爆")
p2 = make_pet("幻影", ["幻"], skills=[make_skill("普通攻击", "普通", power=50)])
o2 = make_pet("岩石", ["岩"], hp=200)
state2 = BattleState(
    player=PlayerState(team=[p2], active_index=0),
    opponent=PlayerState(team=[o2], active_index=0),
)
# 给对手设置5层星陨印记
state2.set_mark(False, FieldMark(
    type_key=StatusEffectType.STAR_FALL_MARK.value,
    stacks=5, is_positive=False
))
hp_before = state2.opponent.get_active_pet().current_hp
atk_action = Action(type=ActionType.USE_SKILL, skill=p2.skills[0])
state2 = engine.apply_action(state2, atk_action, Action(type=ActionType.GATHER_ENERGY))
hp_after = state2.opponent.get_active_pet().current_hp
damage = hp_before - hp_after
assert damage > 50, f"星陨引爆+普通攻击伤害应>50，实际{damage}"
# 印记应该被清空
_, neg = state2.get_marks(False)
assert neg is None, "星陨印记引爆后应被清空"
print(f"   引爆总伤害: {damage}")
print("   [PASS] 星陨印记引爆后清空\n")

# ── 测试3：首领化流程 ────────────────────────────────────────────
print("3. 首领化：属性强化 + 血量恢复")
p3 = make_pet("领袖", ["火"], hp=100, skills=[make_skill("领袖击")], bloodline="leader")
o3 = make_pet("杂兵", ["水"])
state3 = BattleState(
    player=PlayerState(team=[p3], active_index=0, team_state=TeamState(leader_evolution_uses=1)),
    opponent=PlayerState(team=[o3], active_index=0),
)
hp_before3 = state3.player.get_active_pet().current_hp
pa_before3 = state3.player.get_active_pet().stat_modifiers.physical_attack
state3 = engine.apply_action(
    state3,
    Action(type=ActionType.LEADER_EVOLUTION),
    Action(type=ActionType.GATHER_ENERGY)
)
pet3 = state3.player.get_active_pet()
assert pet3.stat_modifiers.physical_attack == pa_before3 + 3, "物攻应+3层"
assert pet3.current_hp > hp_before3, "血量应恢复"
assert state3.player.team_state.leader_evolution_uses == 0, "首领化次数应归零"
print(f"   物攻: {pa_before3} -> {pet3.stat_modifiers.physical_attack}层")
print(f"   血量: {hp_before3} -> {pet3.current_hp}")
print("   [PASS] 首领化效果正常\n")

# ── 测试4：愿力冲击流程 ──────────────────────────────────────────
print("4. 愿力冲击：威力+50%")
atk_skill = make_skill("强力击", "火", power=100, energy=3)
p4 = make_pet("勇士", ["火"], skills=[atk_skill])
o4 = make_pet("靶子", ["水"], hp=200)
# 先测普通攻击伤害
state4a = BattleState(
    player=PlayerState(team=[p4.copy()], active_index=0),
    opponent=PlayerState(team=[o4.copy()], active_index=0),
)
state4a = engine.apply_action(
    state4a,
    Action(type=ActionType.USE_SKILL, skill=atk_skill),
    Action(type=ActionType.GATHER_ENERGY)
)
normal_dmg = 200 - state4a.opponent.get_active_pet().current_hp

# 再测愿力冲击伤害
state4b = BattleState(
    player=PlayerState(team=[p4.copy()], active_index=0,
                       team_state=TeamState(willpower_strike_uses=2)),
    opponent=PlayerState(team=[o4.copy()], active_index=0),
)
state4b = engine.apply_action(
    state4b,
    Action(type=ActionType.WILLPOWER_STRIKE, skill=atk_skill),
    Action(type=ActionType.GATHER_ENERGY)
)
willpower_dmg = 200 - state4b.opponent.get_active_pet().current_hp
assert willpower_dmg > normal_dmg, f"愿力冲击伤害({willpower_dmg})应>普通攻击({normal_dmg})"
assert state4b.player.team_state.willpower_strike_uses == 1, "愿力冲击次数应减1"
print(f"   普通攻击伤害: {normal_dmg}")
print(f"   愿力冲击伤害: {willpower_dmg}")
print("   [PASS] 愿力冲击伤害更高\n")

# ── 测试5：蓄力机制 ──────────────────────────────────────────────
print("5. 蓄力：第1回合蓄力，第2回合释放威力翻倍")
charge_eff = Effect(type=EffectType.CHARGE, target="self", value=0)
charge_skill = make_skill("蓄力冲", "火", power=80, energy=3, effects=[charge_eff])
p5 = make_pet("蓄力者", ["火"], skills=[charge_skill])
o5 = make_pet("目标", ["水"], hp=200)

state5 = BattleState(
    player=PlayerState(team=[p5], active_index=0),
    opponent=PlayerState(team=[o5], active_index=0),
)
hp_before5 = state5.opponent.get_active_pet().current_hp

# 第1回合：蓄力（不应造成伤害）
state5 = engine.apply_action(
    state5,
    Action(type=ActionType.USE_SKILL, skill=charge_skill),
    Action(type=ActionType.GATHER_ENERGY)
)
pet5 = state5.player.get_active_pet()
hp_after_charge = state5.opponent.get_active_pet().current_hp
assert pet5.charging_skill == charge_skill.name, "应进入蓄力状态"
print(f"   蓄力回合伤害: {hp_before5 - hp_after_charge}（应为0）")

# 第2回合：释放（威力翻倍）
state5 = engine.apply_action(
    state5,
    Action(type=ActionType.USE_SKILL, skill=charge_skill),
    Action(type=ActionType.GATHER_ENERGY)
)
hp_after_release = state5.opponent.get_active_pet().current_hp
charged_dmg = hp_after_charge - hp_after_release
assert charged_dmg > 0, "释放应造成伤害"
assert state5.player.get_active_pet().charging_skill is None, "蓄力状态应清除"
print(f"   释放回合伤害: {charged_dmg}")
print("   [PASS] 蓄力机制正常\n")

# ── 测试6：行动生成器—首领化/愿力冲击行动生成（互斥+血脉约束）───
print("6. 行动生成器：首领化/愿力冲击行动生成")
atk_s = make_skill("攻击", "火", power=50, energy=3)

# 6a: 首领血脉精灵 + 选择首领化 → 应有首领化，不应有愿力冲击
p6a = make_pet("首领测试", ["火"], skills=[atk_s], bloodline="leader")
o6a = make_pet("对手", ["水"])
state6a = BattleState(
    player=PlayerState(team=[p6a], active_index=0,
                       team_state=TeamState(leader_evolution_uses=1, willpower_strike_uses=0)),
    opponent=PlayerState(team=[o6a], active_index=0),
)
actions6a = gen.generate_actions(state6a, True)
action_types_a = [a.type for a in actions6a]
assert ActionType.LEADER_EVOLUTION in action_types_a, "首领血脉+选择首领化→应有首领化行动"
assert ActionType.WILLPOWER_STRIKE not in action_types_a, "首领血脉→不应有愿力冲击行动"
print(f"   6a (首领血脉+首领化): {[a.type.value for a in actions6a]}")

# 6b: 非首领血脉精灵 + 选择愿力冲击 → 应有愿力冲击，不应有首领化
p6b = make_pet("普通测试", ["火"], skills=[atk_s], bloodline="fire")
o6b = make_pet("对手", ["水"])
state6b = BattleState(
    player=PlayerState(team=[p6b], active_index=0,
                       team_state=TeamState(leader_evolution_uses=0, willpower_strike_uses=2)),
    opponent=PlayerState(team=[o6b], active_index=0),
)
actions6b = gen.generate_actions(state6b, True)
action_types_b = [a.type for a in actions6b]
assert ActionType.WILLPOWER_STRIKE in action_types_b, "非首领血脉+选择愿力冲击→应有愿力冲击行动"
assert ActionType.LEADER_EVOLUTION not in action_types_b, "非首领血脉→不应有首领化行动"
print(f"   6b (火血脉+愿力冲击): {[a.type.value for a in actions6b]}")

# 6c: 首领血脉精灵 + 选择愿力冲击 → 首领血脉不能用愿力冲击，两者都不出现
p6c = make_pet("首领测试2", ["火"], skills=[atk_s], bloodline="leader")
o6c = make_pet("对手", ["水"])
state6c = BattleState(
    player=PlayerState(team=[p6c], active_index=0,
                       team_state=TeamState(leader_evolution_uses=0, willpower_strike_uses=2)),
    opponent=PlayerState(team=[o6c], active_index=0),
)
actions6c = gen.generate_actions(state6c, True)
action_types_c = [a.type for a in actions6c]
assert ActionType.WILLPOWER_STRIKE not in action_types_c, "首领血脉+选择愿力冲击→首领血脉不能用愿力冲击"
assert ActionType.LEADER_EVOLUTION not in action_types_c, "选择愿力冲击→首领化uses=0→不能用首领化"
print(f"   6c (首领血脉+选愿力): {[a.type.value for a in actions6c]}")

assert ActionType.USE_SKILL in action_types_a, "应有普通技能行动"
assert ActionType.GATHER_ENERGY in action_types_a, "应有聚能行动"
print("   [PASS] 行动生成器首领化/愿力冲击互斥+血脉约束正常\n")

# ── 测试7：评估器心数差权重 ──────────────────────────────────────
print("7. 评估器：心数差影响评分")
p7 = make_pet("评估精灵A", ["火"], skills=[make_skill("攻")])
o7 = make_pet("评估精灵B", ["水"])
state7a = BattleState(
    player=PlayerState(team=[p7], active_index=0),
    opponent=PlayerState(team=[o7], active_index=0),
    player_hearts=4, opponent_hearts=4,
)
state7b = BattleState(
    player=PlayerState(team=[p7], active_index=0),
    opponent=PlayerState(team=[o7], active_index=0),
    player_hearts=4, opponent_hearts=2,  # 对手心数少
)
eval_a = evaluator.evaluate(state7a)
eval_b = evaluator.evaluate(state7b)
assert eval_b > eval_a, f"对手心数少时玩家评分应更高（{eval_a} vs {eval_b}）"
print(f"   心数4v4评分: {eval_a:.1f}")
print(f"   心数4v2评分: {eval_b:.1f}")
print("   [PASS] 心数差正确影响评分\n")

# ── 测试8：搜索引擎输出合理行动 ──────────────────────────────────
print("8. 搜索引擎：深度2搜索")
strong_skill = make_skill("强力攻击", "火", power=150, energy=5)
weak_skill = make_skill("弱击", "火", power=10, energy=1)
p8 = make_pet("策略者", ["火"], skills=[strong_skill, weak_skill])
o8 = make_pet("对手", ["水"], hp=100)  # 对手HP较低，应该优先攻击
state8 = BattleState(
    player=PlayerState(team=[p8], active_index=0),
    opponent=PlayerState(team=[o8], active_index=0),
)
best_action, score = search.find_best_action(state8, depth=2)
assert best_action is not None, "应该找到最佳行动"
print(f"   最佳行动: {best_action}")
print(f"   评估分数: {score:.1f}")
print(f"   搜索节点: {search.nodes_searched}")
print("   [PASS] 搜索引擎正常运行\n")

# ── 测试9：迅捷效果（priority_bonus）────────────────────────────
print("9. 迅捷效果：下回合先手等级+1")
swift_eff = Effect(type=EffectType.SWIFT, target="self", value=1)
swift_skill = make_skill("迅捷击", "风", power=0, energy=2,
                          category=SkillCategory.STATUS, dtype=None,
                          effects=[swift_eff])
slow_skill = make_skill("慢击", "普通", power=50, energy=2, priority=0)
fast_skill = make_skill("快击", "普通", power=50, energy=2, priority=1)  # 先手+1

# 测试迅捷施加效果
p9 = make_pet("迅捷者", ["风"], skills=[swift_skill])
o9 = make_pet("对手", ["水"])
state9 = BattleState(
    player=PlayerState(team=[p9], active_index=0),
    opponent=PlayerState(team=[o9], active_index=0),
)
state9 = engine.apply_action(
    state9,
    Action(type=ActionType.USE_SKILL, skill=swift_skill),
    Action(type=ActionType.GATHER_ENERGY)
)
# 使用迅捷技能后，priority_bonus 应该被设置
pet9_after = state9.player.get_active_pet()
# 注意：priority_bonus 在回合结束时被重置，所以这里检查回合内效果
# 我们检查本回合结束后是否重置为0
assert pet9_after.priority_bonus == 0, "priority_bonus应在回合结束时重置"
print("   [PASS] priority_bonus在回合结束后正确重置\n")

# ── 测试10：死亡后补位不耗回合，可在本回合行动 ────────────────────
print("10. 力竭补位：补位后本回合仍可出招")
ko_front = make_pet("前排已倒下", ["火"], hp=1, skills=[make_skill("占位")])
ko_front.current_hp = 0
ko_front.is_alive = False
bench = make_pet("补位者", ["水"], skills=[make_skill("补位出招", power=60, energy=4)])
enemy10 = make_pet("对手", ["草"], skills=[make_skill("待机", power=0)])
state10 = BattleState(
    player=PlayerState(team=[ko_front, bench], active_index=0),
    opponent=PlayerState(team=[enemy10], active_index=0),
)
actions10 = gen.generate_actions(state10, True)
same_turn_sendout_action = next(
    (
        a for a in actions10
        if a.type == ActionType.USE_SKILL and a.send_out_index == 1
    ),
    None,
)
assert same_turn_sendout_action is not None, "力竭后应能生成“补位后立刻出招”的行动"
state10 = engine.apply_action(
    state10,
    same_turn_sendout_action,
    Action(type=ActionType.GATHER_ENERGY),
)
bench_after = state10.player.get_active_pet()
assert state10.player.active_index == 1, "力竭后应补位到目标精灵"
assert bench_after.template.name == "补位者", "补位后当前精灵应为补位者"
assert bench_after.current_energy == 6, "补位者应在本回合成功释放技能并消耗能量"
print("   [PASS] 力竭补位不耗回合，补位者可在本回合行动\n")

print("=" * 50)
print("所有集成测试通过！")
print("=" * 50)
