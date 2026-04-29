# ObservationState 到 BattleState 的装配设计

## 目标

将 `agent_runtime` 中的 `ObservationState` 转换为可供现有搜索引擎使用的 `BattleState`。

这一层的重点不是“完美还原真实状态”，而是：

1. 尽量不丢失用户已观测事实
2. 对未知字段给出稳定的默认装配策略
3. 为每个候选状态保留 assumptions

## 映射原则

### 1. 已观测事实优先

- `hp_percent`
- `energy`
- `active_pet`
- `hearts`
- `status_effects`
- `marks`

这些字段如果存在，应优先进入候选 `BattleState`。

### 2. 推断值只能填补空缺

对手的：

- 技能组
- 属性范围
- 部分资源状态

只能在缺失时补入，不能覆盖观测事实。

### 3. 无法确定时优先采用保守默认值

初版建议：

- 未知 `hearts` 使用当前引擎默认值
- 未知 `energy` 使用最近一次观测值，没有则使用开局默认值
- 未知技能由 `OpponentModel` 生成少量候选技能组

## 字段映射表

### BattleState

- `turn`
  来源：`ObservationState.turn`

- `weather`
  来源：`ObservationState.weather`

- `field_effects`
  来源：`ObservationState.field_marks`

- `player_hearts`
  来源：`ObservationState.my_side.hearts`

- `opponent_hearts`
  来源：`ObservationState.opponent_side.hearts`

### PlayerState / OpponentState

- `active_index`
  来源：`ObservedSideState.active_pet`

- `team`
  来源：各自 side 下的 `pets`

- `team_state`
  来源：`ObservedSideState.team_resources`
  当前状态：尚未接入

### PetInstance

- `template`
  来源：`DataLoader.pets[pet_name]`

- `max_hp`
  来源：模板 `stats["生命"]`

- `current_hp`
  计算：`int(max_hp * hp_percent / 100)`

- `stats`
  初版来源：模板种族值
  后续可由属性推断修正

- `skills`
  我方：直接使用已知技能
  对手：`observed_skills + inferred_skills`

- `current_energy`
  来源：`ObservedPetState.energy`

- `status_effects`
  来源：`ObservedPetState.status_effects`

## 当前未解决问题

1. `marks` 如何精确映射到现有引擎中的正负印记槽位
2. 字符串状态名与 `StatusEffectType` 的统一转换
3. `team_resources` 到 `TeamState` 的字段映射
4. 对手未出场宠物是否应提前装配完整 `PetInstance`
5. `hp_percent` 缺失时是否允许装配“估算 HP”

## 当前建议

首版只做：

1. 出战精灵和已揭示精灵的装配
2. 能量、心数、血量百分比的直接映射
3. 对手技能组的候选补全
4. `assumptions` 明确保留

暂不做：

- 所有场下精灵的高精度状态还原
- 复杂 team_state 共享资源还原
- 属性范围驱动的真实 stats 修正

## 当前已落地的简化实现

当前 `StateAssembler` 已采用如下最小实现策略：

1. 我方队伍
   使用 `observed_skills + inferred_skills`，不足时回退模板 `learnable_skills`

2. 对手队伍
   当前出战精灵使用 `OpponentModel` 给出的候选技能组
   场下已揭示精灵优先使用已观测技能，不足时回退 `learnable_skills`

3. HP / Energy
   `hp_percent -> current_hp`
   `energy -> current_energy`
   缺失时回退到 `100%` 和 `10`

4. 状态效果
   `status_effects` 和 `marks` 会先映射到 `PetInstance.status_effects`

5. 正负印记槽位
   仅对当前出战宠物执行“单正单负槽位”映射
   超出当前引擎结构的多印记信息保留在 assumptions 中视为未完全表达

这意味着当前装配结果已经可以作为“候选 BattleState”进入后续搜索接入阶段，但仍然是一个**保守、简化、可解释**的版本。
- 属性范围驱动的 stats 微调

## 当前新增的装配接入

这一轮之后，`StateAssembler` 已开始把部分推断结果直接写入候选状态：

1. `stat_ranges`
   当前按区间中心值写回 `PetInstance.stats`

2. `inferred_trait_flags`
   当前会把迅捷类推断映射为 `priority_bonus`

3. `bench_hp_percent / bench_energy`
   当前会直接用于场下精灵的 HP / 能量装配

4. `team_resources`
   当前会映射到 `TeamState` 的同名字段

这意味着候选 `BattleState` 已经不再只是“模板值 + 可见技能”，而开始消费推断层的结果。

## 当前新增的属性剖面展开

为了让搜索真正感知“同一技能组下的属性不确定性”，当前会对对手当前出战精灵额外展开属性剖面：

1. `center`
   使用 `stat_ranges` 的区间中心值

2. `threat_high`
   对速度、双攻、双防、生命采用区间高端值

当前 profile 权重为：

- `center`: 0.7
- `threat_high`: 0.3

这个设计的目的不是断言对手一定取高端值，而是让推荐层开始真正比较：

- 同一技能组
- 不同数值画像

会如何改变动作价值。
