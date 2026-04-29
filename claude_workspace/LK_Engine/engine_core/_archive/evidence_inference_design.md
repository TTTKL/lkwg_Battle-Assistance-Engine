# 高信息量事件与推断设计

## 背景

真实对局中可观测的信息远多于：

- 谁用了什么技能
- 谁掉了多少血
- 谁换了谁

实际上还包括：

1. 出手顺序
   可用于反推速度、性格、特质加点，以及迅捷类效果

2. 伤害与剩余生命
   可用于反推双攻、双防、生命、性格和加点

3. 对手后排资源变化
   某些特性会恢复未上场精灵的血量或能量

4. 技能复制类信息
   如果我方技能“随机复制敌方一个技能且费用-2”，那这本身就是对敌方技能池的证据

5. 迅捷/优先效果
   既影响行动顺序，也影响后续推断

因此，`agent_runtime` 不能只做“事件记录器”，而需要逐步升级成“证据管理器 + 推断器”。

## 当前设计方向

### 1. ObservationState 新增证据层

当前已加入：

- `speed_evidence`
- `damage_evidence`
- `skill_evidence`
- `copy_skill_evidence`
- `bench_resource_evidence`
- `quick_effect_evidence`

### 2. ObservedPetState 新增推断字段

当前已加入：

- `inferred_natures`
- `inferred_ev_spreads`
- `inferred_trait_flags`

### 3. StatInferrer

新增：

- `engine/stat_inferrer.py`

当前定位：

- 统一承接速度、伤害、复制技能、后排资源、迅捷等证据
- 输出 `PetInferenceSummary`
- 当前先固定接口和证据容器，后续逐步填入真实推断公式

### 4. EvidenceCollector

新增：

- `tracker/evidence_collector.py`

当前定位：

- 从现有事件流中自动抽取高信息量证据
- 避免以后每加一个推断点都回头改 CLI / API
- 让回放与实时录入走同一套证据采集逻辑

### 5. 推断结果回写

当前已实现：

- `BattleSessionManager.append_event()`
- `BattleSessionManager.replay_session()`

都会在 reducer 完成后调用 `StatInferrer.apply_to_observation()`。

当前回写字段包括：

- `ObservedPetState.stat_ranges`
- `ObservedPetState.inferred_natures`
- `ObservedPetState.inferred_ev_spreads`
- `ObservedPetState.inferred_trait_flags`

## 当前数值推断方法

当前 `StatInferrer` 已开始参考现有引擎的两类核心规则：

### 1. 出手顺序 -> 速度区间

依据：

- 技能优先级
- `priority_bonus`
- 双方出手先后

在未检测到迅捷类干扰时，会以我方速度模板为锚点，缩窄对手速度区间。

### 2. 伤害公式 -> 双攻 / 双防 / 生命区间

当前近似参考现有引擎公式：

```text
damage = (attack / defense) * 0.9 * power * stab * type_effectiveness * weather_bonus
```

并结合：

- 技能威力
- 伤害类型（物理/魔法）
- STAB
- 属性克制
- 天气
- 实际伤害
- 剩余生命百分比

生成对：

- 物攻 / 魔攻
- 物防 / 魔防
- 生命

的近似区间估计。

## 关键设计原则

### 原则 1：证据先于结论

不要一上来把“推断值”直接写死进状态。

应该先保留：

- 我看到了什么
- 我根据什么做出的推断
- 当前推断置信度是多少

### 原则 2：特殊技能/特性证据必须显式建模

例如：

- 随机复制敌方技能
- 恢复后排血量/能量
- 迅捷导致的额外先手

这些都不能简单并入普通伤害事件，否则后续推断会被污染。

### 原则 3：推断结果不能覆盖观测事实

例如：

- 我直接看到对方后排能量是 6
- 那就不能再让旧推断把它覆盖回 4

## 下一步建议

1. 继续让 `OpponentModel` 和 `StatInferrer` 更深地共享这些证据
2. 提高数值推断精度，减少当前“模板中心 + 证据缩窄”的粗粒度方法
3. 扩充事件 schema，让速度顺序、复制技能、后排资源变化、迅捷来源更明确

## 当前已接入 OpponentModel 的证据

当前 `OpponentModel` 已开始利用以下信息调整技能候选分数：

1. `inferred_natures`
   例如：物攻强化性格更偏向物理技能

2. `inferred_ev_spreads`
   例如：速度投入更偏向先手技能

3. `inferred_trait_flags`
   例如：迅捷证据会提高先手技能权重

4. `copy_skill_evidence`
   若复制到某技能，会显著提高该技能在对手技能池中的概率

5. `bench_resource_evidence`
   若检测到后排能量恢复，会提高高能耗技能的候选权重

6. `quick_effect_evidence`
   用于增强先手/迅捷相关技能的概率
