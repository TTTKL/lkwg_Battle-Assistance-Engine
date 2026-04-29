# 实时对战辅助引擎事件架构设计

更新日期：2026-04-10

---

## 1. 设计目标

基于现有 `new_one/` 完全信息对战引擎，设计下一阶段的**事件驱动实时辅助架构**，使系统能够从用户可观测到的真实对局信息出发：

1. 管理对局会话
2. 逐步读取和记录对局事件
3. 将事件转化为可计算状态
4. 在信息不完整的前提下进行推断、评估和行动推荐

这份设计不替代现有 `BattleState` 战斗模拟主链路，而是在其外层增加一层“**用户观测 -> 事件日志 -> 推断状态 -> 搜索建议**”的管理与处理体系。

---

## 2. 用户视角下的问题定义

真实用户在对战中不会一次性提供完整 `BattleState`。用户通常只能做到：

- 在开局录入双方阵容或已知精灵
- 每回合录入自己做了什么
- 回合结束后补录对手做了什么
- 更新双方 HP 百分比、能量、状态、印记、换宠结果
- 在任意时点请求“下一步推荐”

因此系统不能要求用户先构造完整状态对象，而应提供一个**低负担、可纠错、可增量更新**的事件接口。

从用户角度看，系统应该像一个“对局记事本 + 分析器”：

1. 我上报事件
2. 系统自动整理成当前局面
3. 系统标出哪些信息是确定的，哪些是推断的
4. 系统给出推荐行动和风险提示

---

## 3. 总体架构

建议新增一条事件驱动主链路：

```text
User Input
  -> BattleSessionManager
  -> EventInbox / EventValidator
  -> BattleEventLog
  -> ObservationBuilder
  -> OpponentModel / StatInferrer
  -> StateAssembler
  -> UncertaintySearchFacade
  -> Recommendation / SituationReport
```

与当前代码的关系：

```text
事件层（新增）
  Session / Event / Observation / Tracker / Inference
      ↓
状态装配层（新增）
  ObservationState -> InferredBattleState
      ↓
现有分析层（复用/扩展）
  GameAnalysisEngine
  ExtendedBattleEngine
  Evaluator
  SearchEngine
  ActionGenerator
```

核心原则：

- 用户输入的是**事件**，不是完整状态
- 系统保存的是**事件日志 + 当前观测状态**
- 搜索使用的是**装配后的推断状态**
- 推荐结果必须附带**置信度和不确定来源**

---

## 4. 模块分层设计

## 4.1 会话管理层

职责：

- 管理一场对局的生命周期
- 为每场对局维护独立状态
- 支持恢复、撤销、纠错、重算

建议新增：

- `tracker/session_manager.py`
- `tracker/session_store.py`

建议核心对象：

```python
class BattleSession:
    session_id: str
    created_at: datetime
    updated_at: datetime
    status: str  # active / finished / aborted
    config: BattleSessionConfig
    event_log: BattleEventLog
    observation_state: ObservationState
    inferred_state: InferredBattleState | None
    last_recommendation: Recommendation | None
```

```python
class BattleSessionConfig:
    my_team: List[KnownPetConfig]
    opponent_team_candidates: List[KnownOpponentPet]
    ruleset_version: str
    search_depth: int
    inference_mode: str  # pessimistic / probabilistic / hybrid
```

会话管理层要解决的用户问题：

- 开一局
- 继续上一局
- 回退上一步录错的事件
- 查看本回合系统依据什么做出的推荐

---

## 4.2 事件模型层

职责：

- 统一定义用户可上报的事件
- 提供事件标准化和校验能力
- 保证事件可重放

建议新增：

- `core/events.py`

建议采用“事件信封 + 事件载荷”的结构：

```python
class BattleEvent:
    event_id: str
    session_id: str
    turn: int
    phase: str
    event_type: str
    actor_side: str | None
    timestamp: datetime
    payload: dict
    source: str  # user / api / replay / auto_infer
```

建议首批支持的事件类型：

1. `BATTLE_STARTED`
2. `TURN_STARTED`
3. `MY_ACTION_DECLARED`
4. `OPPONENT_ACTION_OBSERVED`
5. `PET_SWITCHED`
6. `SKILL_USED`
7. `DAMAGE_OBSERVED`
8. `HP_PERCENT_UPDATED`
9. `ENERGY_UPDATED`
10. `STATUS_APPLIED`
11. `STATUS_REMOVED`
12. `MARK_UPDATED`
13. `PET_FAINTED`
14. `HEARTS_UPDATED`
15. `TURN_ENDED`
16. `STATE_CORRECTED`

其中最关键的是以下 6 类：

- 行动声明：我方准备做什么
- 行动观测：对手实际做了什么
- 伤害结果：造成了多少伤害
- 百分比更新：当前双方血量情况
- 换宠事件：谁下场谁上场
- 状态修正：当用户发现系统推断错了时进行覆盖

---

## 4.3 事件接入层

职责：

- 接收 CLI / API / 前端 UI 的输入
- 将自由输入转换为结构化事件
- 在入库前做轻量校验

建议新增：

- `tracker/event_ingest.py`
- `tracker/event_validator.py`
- `tracker/event_normalizer.py`

处理流程：

```text
Raw User Input
  -> normalize()
  -> validate()
  -> append_to_log()
  -> apply_to_observation()
```

建议校验规则：

- 事件必须属于某个已存在的 `session_id`
- 回合号不能倒退，除非是显式修正事件
- 出战精灵必须是当前可上场对象
- 技能名必须存在于我方已知技能集，或作为对手观测技能首次注册
- HP 百分比必须在 `0~100`
- 同一时刻不能同时出现两个当前出战精灵

---

## 4.4 事件日志层

职责：

- 作为单一事实来源保存所有事件
- 支持重放、回滚、审计
- 为调试和错误恢复提供依据

建议新增：

- `tracker/event_log.py`

建议对象：

```python
class BattleEventLog:
    events: List[BattleEvent]

    def append(self, event: BattleEvent) -> None: ...
    def replay(self) -> ObservationState: ...
    def rollback_to(self, event_id: str) -> None: ...
    def list_turn_events(self, turn: int) -> List[BattleEvent]: ...
```

设计建议：

- 系统内部**不直接修改最终状态作为唯一真源**
- 真源应是 `BattleEventLog`
- `ObservationState` 和 `InferredBattleState` 都应可由日志重建

这样做的价值：

- 用户录错一个事件，可以回滚后重放
- 算法升级后，可以用旧日志重建新结果
- 便于未来支持“导入对战回放”

---

## 5. 观测状态设计

## 5.1 ObservationState 的角色

`ObservationState` 不等于 `BattleState`。它描述的是：

- 用户已经确认看见的事实
- 当前仍然未知的信息
- 系统已经做出的推断

建议新增：

- `core/observation.py`

建议结构：

```python
class ObservedPetState:
    pet_name: str
    side: str
    revealed: bool
    is_active: bool
    hp_percent: float | None
    energy: int | None
    status_effects: dict
    marks: dict
    buffs: dict
    debuffs: dict
    observed_skills: list[str]
    inferred_skills: list[str]
    stat_ranges: dict[str, tuple[float, float]]
    confidence: float
```

```python
class ObservationState:
    turn: int
    weather: str | None
    field_marks: dict
    my_side: ObservedSideState
    opponent_side: ObservedSideState
    event_cursor: int
    uncertainty_notes: list[str]
```

```python
class ObservedSideState:
    active_pet: str | None
    hearts: int | None
    pets: dict[str, ObservedPetState]
    team_resources: dict
```

设计边界：

- 我方信息尽量按真实已知值保存
- 对手信息按“已观测值 + 推断值”分开保存
- 不允许用推断值覆盖观测值

---

## 5.2 观测状态更新方式

`ObservationState` 应由事件驱动更新，而不是让上层直接改字段。

建议新增：

- `tracker/observation_reducer.py`

核心接口：

```python
class ObservationReducer:
    def apply(self, obs: ObservationState, event: BattleEvent) -> ObservationState:
        ...
```

建议按 reducer 模式实现的原因：

- 事件 -> 状态变化逻辑集中
- 易测
- 易回放
- 方便未来插入中间调试点

---

## 6. 对手推断层设计

## 6.1 技能推断

建议新增：

- `engine/opponent_model.py`

职责：

- 根据 `learnable_skills`、已观测技能、能量曲线、属性适配度生成候选技能组
- 输出候选技能组合及概率或排序分数

建议接口：

```python
class OpponentModel:
    def infer_skill_sets(
        self,
        pet_name: str,
        observed_skills: list[str],
        observation: ObservationState,
        top_k: int = 5
    ) -> list[SkillSetCandidate]:
        ...
```

```python
class SkillSetCandidate:
    skills: list[str]
    score: float
    rationale: list[str]
```

建议初版规则：

- 已观测技能必须保留
- 候选技能从 `learnable_skills` 补全到 4 个
- 优先选择与系别匹配、能量曲线合理、覆盖面更强的技能
- 若用户指定“保守模式”，优先补全对我方威胁最高的技能

---

## 6.2 属性推断

建议新增：

- `engine/stat_inferrer.py`

职责：

- 基于观测伤害、技能属性、已知防御值，反推对手攻击范围
- 随事件积累不断缩窄区间

建议接口：

```python
class StatInferrer:
    def record_damage_event(self, event: DamageEvent) -> None: ...
    def infer_ranges(self, pet_name: str) -> StatInferenceResult: ...
```

```python
class DamageEvent:
    attacker: str
    defender: str
    skill_name: str
    observed_damage: int | None
    observed_hp_drop_percent: float | None
    category: str
    stab: bool | None
    type_effectiveness: float | None
```

---

## 6.3 不确定性管理

推断层输出不应只有一个答案，而应包含“置信度”。

建议新增：

- `engine/uncertainty.py`

建议统一对象：

```python
class ConfidenceBundle:
    overall_confidence: float
    skill_confidence: dict[str, float]
    stat_confidence: dict[str, float]
    notes: list[str]
```

用途：

- 搜索时决定是走“期望值”还是“最坏情况”
- 展示给用户当前推荐的可信程度

---

## 7. 状态装配层设计

## 7.1 为什么需要装配层

现有引擎需要较完整的 `BattleState`。而用户输入经过事件和推断处理后，得到的是 `ObservationState`。

因此需要一个中间层，把：

- 观测事实
- 推断技能组
- 推断属性范围
- 当前资源状态

装配成**可供搜索的候选状态集合**。

建议新增：

- `engine/state_assembler.py`

---

## 7.2 装配产物

建议定义：

```python
class InferredBattleState:
    battle_state: BattleState
    assumptions: list[str]
    confidence: float
```

```python
class StateAssembler:
    def build_candidates(
        self,
        observation: ObservationState,
        top_k_skill_sets: int = 3
    ) -> list[InferredBattleState]:
        ...
```

初版建议：

- 对手每只活着的精灵只展开少量候选技能组
- 当前出战精灵优先精细推断
- 场下精灵可以使用更粗糙的默认配置，控制状态爆炸

---

## 8. 搜索与推荐层设计

## 8.1 外层推荐门面

建议新增：

- `engine/recommendation_service.py`

职责：

- 接收 `ObservationState`
- 调用 `OpponentModel` 和 `StateAssembler`
- 统一调度搜索引擎
- 生成用户可读的推荐结果

建议接口：

```python
class RecommendationService:
    def recommend(
        self,
        session: BattleSession,
        depth: int = 2
    ) -> Recommendation:
        ...
```

```python
class Recommendation:
    best_action: dict
    score: float
    confidence: float
    alternatives: list[dict]
    risk_notes: list[str]
    based_on_assumptions: list[str]
```

---

## 8.2 搜索策略演进

建议分阶段落地：

### 阶段 A：悲观 Minimax

- 对每个候选对手技能组求值
- 取我方动作在最坏情况中的最优值

适合首版上线，理由：

- 与当前 `SearchEngine` 最接近
- 工程复杂度最低
- 能先跑起来

### 阶段 B：期望搜索

- 按候选技能组概率加权
- 输出期望收益更高的行动

### 阶段 C：混合策略

- 高风险资源动作使用悲观估值
- 普通资源动作使用期望估值

这是更贴近真实用户决策的方式。

---

## 9. 用户交互设计

## 9.1 事件输入方式

从用户视角，建议提供三种模式：

1. **极简模式**
   只录关键事件：对手用了什么、谁换宠了、双方血量百分比是多少

2. **标准模式**
   每回合录：我方行动、对手行动、伤害、状态、换宠、血量

3. **校正模式**
   当系统推断偏差较大时，用户手动覆盖当前状态

推荐默认提供标准模式，极简模式作为快速使用方式。

---

## 9.2 CLI 交互命令建议

建议新增：

- `cli_interactive.py`

建议命令：

```text
start
team my <宠物列表>
team opp <宠物列表>
turn start
my use <技能名>
opp use <技能名>
switch my <旧宠> <新宠>
switch opp <旧宠> <新宠>
hp my <宠物> <百分比>
hp opp <宠物> <百分比>
energy my <宠物> <数值>
energy opp <宠物> <数值>
status add <side> <pet> <status> <stacks>
mark set <side> <mark> <stacks>
recommend
report
undo
correct
```

CLI 设计原则：

- 命令短
- 允许不完整输入
- 用户输错后可撤销
- `recommend` 随时可调用

---

## 9.3 API 设计建议

建议保留现有 `api.py` 分析接口，同时新增事件式接口。

建议新增端点：

- `POST /api/battle/start`
- `POST /api/battle/{session_id}/event`
- `GET /api/battle/{session_id}/state`
- `GET /api/battle/{session_id}/report`
- `GET /api/battle/{session_id}/recommend`
- `POST /api/battle/{session_id}/undo`
- `POST /api/battle/{session_id}/correct`

建议 `/event` 请求体：

```json
{
  "turn": 3,
  "event_type": "OPPONENT_ACTION_OBSERVED",
  "payload": {
    "pet_name": "xxx",
    "action_type": "USE_SKILL",
    "skill_name": "烈焰冲锋"
  }
}
```

建议 `/report` 返回：

```json
{
  "turn": 3,
  "active_pets": {
    "my": "xxx",
    "opp": "yyy"
  },
  "confidence": 0.78,
  "unknowns": [
    "对手剩余3个技能未完全确定",
    "对手物攻范围仍较宽"
  ],
  "recommendation": {
    "action": "USE_SKILL",
    "skill_name": "防守反击",
    "score": 1460.0
  }
}
```

---

## 10. 事件处理时序

建议每回合内部采用如下处理顺序：

```text
1. TURN_STARTED
2. MY_ACTION_DECLARED
3. OPPONENT_ACTION_OBSERVED
4. DAMAGE_OBSERVED / STATUS_APPLIED / MARK_UPDATED
5. PET_SWITCHED / PET_FAINTED
6. HP_PERCENT_UPDATED / ENERGY_UPDATED
7. HEARTS_UPDATED
8. TURN_ENDED
9. recompute_observation()
10. infer_unknowns()
11. build_candidate_states()
12. recommend()
```

设计重点：

- 先记日志，再改观测状态
- 推荐计算在回合事件稳定后触发
- 任何时刻都允许用户强制触发 `recommend`

---

## 11. 撤销与纠错机制

真实用户录入一定会出错，所以必须把这部分当成正式能力而不是补丁。

建议支持：

1. `undo_last_event`
2. `rollback_to_turn`
3. `apply_correction_event`
4. `replay_from_log`

推荐方式：

- 不直接删日志
- 用 `STATE_CORRECTED` 事件覆盖当前观测值
- 在报告中保留“这是用户修正值”标记

---

## 12. 与现有代码的对接方式

建议尽量少动现有完整信息引擎，优先采用“外层封装”。

### 应复用的现有模块

- `new_one/game_analysis_engine.py`
- `new_one/engine/extended_battle_engine.py`
- `new_one/engine/evaluator.py`
- `new_one/engine/search_engine.py`
- `new_one/engine/action_generator.py`
- `new_one/data_loader.py`

### 建议新增而非重写的模块

- `new_one/core/events.py`
- `new_one/core/observation.py`
- `new_one/tracker/session_manager.py`
- `new_one/tracker/event_log.py`
- `new_one/tracker/event_ingest.py`
- `new_one/tracker/observation_reducer.py`
- `new_one/engine/opponent_model.py`
- `new_one/engine/stat_inferrer.py`
- `new_one/engine/state_assembler.py`
- `new_one/engine/recommendation_service.py`

### 现有模块的最小改动点

1. `game_analysis_engine.py`
   增加基于 `ObservationState` 的新入口，而不是替换旧入口

2. `search_engine.py`
   增加对多候选 `BattleState` 的外层调度支持

3. `evaluator.py`
   支持不确定性惩罚项

4. `api.py`
   新增事件式接口，不破坏当前已有分析接口

---

## 13. 建议的数据流对象

建议在整个架构中明确区分这 5 类对象：

1. `BattleEvent`
   用户上报或系统生成的事实事件

2. `ObservationState`
   当前可观测事实 + 未知信息 + 推断结果

3. `SkillSetCandidate`
   对手技能组合候选

4. `InferredBattleState`
   可用于搜索的候选完整状态

5. `Recommendation`
   返回给用户的最终建议

这能避免未来把“事件”“事实”“推断”“搜索输入”“用户输出”混在同一个数据类里。

---

## 14. 开发阶段建议

建议按以下顺序推进：

### 第一阶段：先把事件闭环做出来

- `core/events.py`
- `core/observation.py`
- `tracker/event_log.py`
- `tracker/observation_reducer.py`
- `tracker/session_manager.py`

目标：

- 能创建会话
- 能持续录入事件
- 能稳定得到当前 `ObservationState`

### 第二阶段：接入最简推断

- `engine/opponent_model.py`
- `engine/state_assembler.py`

目标：

- 即使不知道对手全技能，也能组出少量候选状态

### 第三阶段：推荐跑通

- `engine/recommendation_service.py`
- `api.py` 新接口
- `cli_interactive.py`

目标：

- 用户可以一边录入事件，一边拿到推荐

### 第四阶段：增强推断质量

- `engine/stat_inferrer.py`
- `engine/uncertainty.py`
- `evaluator.py` 不确定性修正

---

## 15. 首版可交付范围建议

为了避免设计过大，首版建议只做以下能力：

1. 支持单场会话管理
2. 支持事件日志记录与回放
3. 支持基础 `ObservationState`
4. 支持对手已观测技能 + learnable_skills 补全
5. 支持悲观搜索推荐
6. 支持 CLI 交互录入

首版先不做：

- 完整概率图模型
- 复杂行为风格学习
- 自动 OCR 或屏幕识别
- 全量历史回放导入

---

## 16. 风险与设计注意事项

### 16.1 最大风险

- 事件太细，用户录入负担过高
- 事件太粗，系统状态恢复不稳定
- 推断结果直接写回状态，造成“观测事实”和“假设”混淆
- 候选状态过多，搜索爆炸

### 16.2 设计约束

- 永远保留“观测事实”和“推断事实”的边界
- 所有推断必须可解释
- 搜索层不直接消费原始事件，应消费装配后的状态
- 所有关键对象都应支持重建和调试输出

---

## 17. 最终建议

下一步的核心不是继续扩大战斗规则，而是把现有引擎外面补上一层**事件驱动的实时观测架构**。

最合理的实现方式是：

1. 以 `BattleEventLog` 作为真源
2. 以 `ObservationState` 作为用户视角状态
3. 以 `OpponentModel + StateAssembler` 生成候选完整状态
4. 以 `RecommendationService` 对接现有搜索引擎

这样可以在不推翻 `new_one/` 现有战斗模拟能力的前提下，把项目从“完全信息分析器”平滑升级成“真实对战中的辅助 agent”。

---

## 18. 当前落地决策

经过评估，这一部分与现有 `new_one/core`、`new_one/engine` 的战斗规则主链路**相对独立**，适合先作为独立子系统落地，再逐步接入旧引擎。

已采用的目录策略：

```text
new_one/
└── agent_runtime/
    ├── core/
    ├── tracker/
    ├── engine/
    └── docs/
```

这样做的原因：

1. 避免在早期设计阶段直接污染现有完整信息引擎
2. 方便单独推进“事件管理 / 观测状态 / 推荐编排”这条链路
3. 后续接入时可以通过组合方式对接 `game_analysis_engine.py` 和 `search_engine.py`

当前已建立的设计骨架包括：

- `agent_runtime/core/events.py`
- `agent_runtime/core/observation.py`
- `agent_runtime/tracker/event_log.py`
- `agent_runtime/tracker/observation_reducer.py`
- `agent_runtime/tracker/session_manager.py`
- `agent_runtime/engine/opponent_model.py`
- `agent_runtime/engine/state_assembler.py`
- `agent_runtime/engine/recommendation_service.py`
- `agent_runtime/docs/implementation_plan.md`

这些文件目前的定位是：

- 先固定模块边界和数据契约
- 先跑通“事件 -> 观测状态”的最小闭环
- 再逐步把推断和搜索接上

下一步最值得继续推进的是：

1. 用 `data_loader.py` 接入真实 `learnable_skills`
2. 设计 `ObservationState -> BattleState` 的精确映射规则
3. 接入 `SearchEngine`
4. 增加 undo / replay 工具

---

## 19. 当前实现进展补充

独立子系统的“最小事件闭环”已经进一步落地，新增了两个关键模块：

- `agent_runtime/tracker/event_normalizer.py`
- `agent_runtime/tracker/event_validator.py`

并把 `ObservationReducer` 扩展到了更接近真实对局录入的事件集合。

### 当前已经支持的事件处理能力

1. `BattleStarted`
   初始化开局阵容和天气

2. `HPPercentUpdated` / `EnergyUpdated`
   同步双方可观测资源值

3. `OpponentActionObserved` / `SkillUsed`
   记录对手已暴露技能与当前行动

4. `StatusApplied` / `StatusRemoved`
   更新宠物状态效果

5. `MarkUpdated`
   更新宠物印记或场地印记

6. `PetSwitched` / `PetFainted`
   更新出战精灵和死亡状态

7. `HeartsUpdated`
   更新心数

8. `StateCorrected`
   允许用户对关键观测值做覆盖修正

### 这一阶段的结论

当前 `agent_runtime` 已经不只是纯文档设计，而是具备了一个明确的实现方向：

- 外部输入先归一化
- 再进行校验
- 再落入事件日志
- 再更新 `ObservationState`

也就是说，下一步可以直接开始接 `learnable_skills` 和 `BattleState` 装配，而不需要再反复讨论事件层的基本结构。

---

## 20. 推断层与装配层补充设计

在当前这一轮设计中，`agent_runtime` 又向前推进了一步：

### 20.1 对手技能组推断已从“占位”升级为“数据驱动”

`agent_runtime/engine/opponent_model.py` 现在的定位已经明确为：

- 可接入现有 `data_loader.py`
- 读取 `PetTemplate.learnable_skills`
- 结合本系、技能类别、能量可达性、先手、多段等因素做粗排序
- 输出少量可解释的技能组候选

当前默认生成三种候选：

1. 平衡型技能组
2. 进攻型技能组
3. 功能型技能组

这一步的意义是：

- 搜索层之后不必面对“对手技能完全未知”的空状态
- 可以先用少量候选状态跑通悲观搜索

### 20.2 状态装配层已经有明确的字段映射文档

新增文档：

- `agent_runtime/docs/state_assembly_design.md`

它明确了：

- `ObservationState.turn -> BattleState.turn`
- `ObservationState.weather -> BattleState.weather`
- `ObservedPetState.hp_percent -> PetInstance.current_hp`
- `ObservedPetState.energy -> PetInstance.current_energy`
- 我方技能与对手技能候选的装配来源

当前还保留为未决的问题主要有：

1. 宠物印记如何准确映射到现有正负印记槽位
2. `team_resources -> TeamState` 的字段映射
3. 字符串状态名到 `StatusEffectType` 的统一转换
4. 未出场精灵应装配到什么粒度

### 20.3 当前阶段的结论

到这一轮为止，`agent_runtime` 的结构已经分成了三层明确边界：

1. 事件与会话层
2. 对手推断层
3. 状态装配与推荐编排层

因此下一步的工作重点已经可以从“继续补设计骨架”转成：

1. 用现有 `SearchEngine` 跑出候选推荐
2. 再补回放与纠错工具
3. 逐步补齐 `TeamState` 与复杂印记装配

---

## 21. 当前装配层实现状态

这一轮已经把 `StateAssembler` 从“只输出装配计划”推进到“可生成候选 BattleState”。

### 已完成

1. 我方与对手已揭示精灵可被装配为 `PetInstance`
2. `hp_percent` 可映射到 `current_hp`
3. `energy` 可映射到 `current_energy`
4. `status_effects` / `marks` 可映射到 `PetInstance.status_effects`
5. 对手当前出战精灵可使用 `OpponentModel` 生成的候选技能组
6. `RecommendationService` 已能感知装配是否成功，并返回候选数量与 assumptions

### 当前实现采用的简化规则

1. 我方技能不足时回退到模板 `learnable_skills`
2. 对手场下精灵优先用已观测技能，不足时回退到 `learnable_skills`
3. 印记槽位仅精确映射当前出战宠的单正单负槽位
4. 未知 `hp_percent` / `energy` 分别回退到 `100%` 和 `10`

### 仍未解决

1. `TeamState` 共享资源装配
2. 多印记共存的表达
3. 更高质量的 stats 推断写回
4. 候选状态间如何做严格的一致动作比较

---

## 22. 当前推荐层实现状态

这一轮继续推进后，`agent_runtime` 已经能够把候选状态送入现有分析引擎。

### 已完成

1. `RecommendationService` 可对每个候选 `BattleState` 调用 `GameAnalysisEngine.analyze_state()`
2. 返回结果会保留：
   - 推荐动作
   - 评估值
   - 候选状态假设
   - 候选数量

### 当前采用的保守策略

当前已经实现了“同一动作在多个候选状态中的统一价值比较”的第一版：

1. 先建立多个候选状态之间的共享动作集合
2. 对每个共享动作，分别计算其在各候选状态下的得分
3. 取该动作在所有候选里的最坏得分
4. 最终选择“最坏得分最高”的动作

这个策略的优点是：

- 可解释
- 与当前已有 `GameAnalysisEngine` 接口兼容
- 对真实对局辅助场景更保守

缺点也很明确：

- 目前只实现了 pessimistic 聚合
- 还没有引入候选概率，因此不能输出真正的 expected value
- 共享动作集合若为空，目前会回退到首个候选动作集

这一阶段已经补上了第一版多策略聚合：

1. `pessimistic`
   以动作的最坏得分作为决策依据

2. `expected`
   以候选状态置信度加权后的期望得分作为决策依据

3. `hybrid`
   以 `0.7 * worst + 0.3 * expected` 进行折中

因此下一阶段真正需要补的是：

1. 继续改进候选状态置信度的来源，不只依赖当前技能组粗评分
2. 把更多观测证据接入 probability，例如已知能量、已观测技能时序、伤害记录
3. 将模式选择暴露到 API / CLI 的更完整配置里

---

## 26. 候选概率实现状态

这一轮开始把“候选状态置信度”从占位值推进成真正的可归一化分布。

### 已完成

1. `OpponentModel.SkillSetCandidate`
   新增 `probability` 字段

2. 候选技能组
   现在不再只给出固定分数，而是：
   - 根据技能排序得分生成候选 score
   - 再在候选集合内部归一化为 probability

3. `StateAssembler`
   当前会把 `SkillSetCandidate.probability` 直接写入 `InferredBattleState.confidence`

### 当前意义

这意味着：

- `expected / hybrid` 不再完全依赖任意常数
- 虽然概率模型仍然粗糙，但至少已经形成“候选生成 -> 候选归一化 -> 候选状态置信度 -> 推荐聚合”的完整链条

---

## 27. 高信息量事件建模方向

根据当前补充的需求，事件层的设计已经不能只围绕：

- 技能
- 血量
- 换宠

而必须显式覆盖以下高信息量证据：

1. 出手顺序
   用于反推速度、性格、特质加点，以及迅捷类效果

2. 伤害与剩余生命百分比
   用于反推双攻、双防、生命、性格和加点

3. 技能复制类信息
   如果我方随机复制到对方技能，这本身就是对对方技能池的证据

4. 后排资源变化
   某些特性会影响未上场精灵的血量和能量

5. 迅捷/优先类效果
   这会直接污染速度推断，必须单独记录

### 当前已落地的设计动作

1. `ObservationState`
   已加入：
   - `speed_evidence`
   - `damage_evidence`
   - `skill_evidence`
   - `copy_skill_evidence`
   - `bench_resource_evidence`
   - `quick_effect_evidence`

2. `ObservedPetState`
   已加入：
   - `inferred_natures`
   - `inferred_ev_spreads`
   - `inferred_trait_flags`

3. `StatInferrer`
   已新增独立文件，作为这类证据的统一推断入口

4. `EvidenceCollector`
   已新增并接入 reducer，用于从现有事件流中自动提取这些证据

### 当前阶段结论

这一步的重点不是马上把所有推断公式写完，而是先保证：

- 证据不会丢
- 特殊事件不会被普通事件模型吞掉
- 未来可以把真实游戏里的更多可观测信息逐步接进来

---

## 29. 当前公式化推断状态

这一轮实现后，`StatInferrer` 已开始参考现有引擎中的具体机制，而不只是做经验式缩窄。

### 当前已接入的近似公式来源

1. 出手顺序
   参考：
   - 技能优先级
   - `priority_bonus`
   - 出手先后

2. 伤害公式
   参考：
   - 技能威力
   - STAB
   - 属性克制
   - 天气
   - 实际伤害
   - 剩余生命百分比

### 当前结论

它还不是最终精确实现，但当前推断层已经从“纯结构预留”进入了“围绕真实对战公式做区间反推”的阶段。

---

## 30. 推断结果对技能候选的反向影响

这一轮开始，推断层的结果已经不再只是展示信息，而是会反向影响 `OpponentModel`。

### 当前已接入的反向影响链

1. `inferred_natures`
   会影响物理/魔法技能候选倾向

2. `inferred_ev_spreads`
   会影响先手/高速技能候选倾向

3. `inferred_trait_flags`
   会影响迅捷/功能类技能候选倾向

4. `copy_skill_evidence`
   会显著提高被复制到的技能在对手技能池中的权重

5. `bench_resource_evidence`
   会提高高能耗技能的候选概率

6. `quick_effect_evidence`
   会增强先手类技能的候选概率

### 这一阶段的意义

到这里为止，链路已经形成闭环：

1. 事件进入
2. 证据被采集
3. 推断结果写回 `ObservedPetState`
4. `OpponentModel` 再消费这些推断结果
5. 最终影响候选状态与推荐

---

## 28. 推断结果回写状态

这一轮已经把“证据存在 ObservationState 里”进一步推进到“推断结果会自动回写到宠物观测状态”。

### 已完成

1. `BattleSessionManager`
   在：
   - `append_event()`
   - `replay_session()`

   后都会触发 `StatInferrer.apply_to_observation()`

2. `StatInferrer`
   当前已能根据：
   - 出手顺序证据
   - 伤害证据
   - 复制技能证据
   - 后排资源证据
   - 迅捷证据

   生成粗粒度推断摘要

3. `ObservedPetState`
   当前会被自动回写：
   - `stat_ranges`
   - `inferred_natures`
   - `inferred_ev_spreads`
   - `inferred_trait_flags`

### 当前采用的方法

目前仍然是保守的粗粒度方案：

1. 先以模板种族值作为中心
2. 再用证据对区间做缩窄
3. 再生成“速度强化性格 / 物攻投入 / 后排资源恢复特性”等软推断标签

这不是最终的精确反推公式，但已经把“证据 -> 推断结果 -> 状态回写”这条链跑通了。

---

## 23. 事件工具链实现状态

这一轮把事件层补成了真正可操作的工具链，而不只是“能追加事件”。

### 已完成

1. `BattleEventLog`
   支持：
   - `last_event()`
   - `get_event_index(event_id)`
   - `rollback_last()`
   - `rollback_to_event(event_id)`

2. `BattleSessionManager`
   支持：
   - `replay_session(session_id)`
   - `undo_last_event(session_id)`
   - `rollback_to_event(session_id, event_id)`
   - `apply_correction(...)`
   - `get_session_report(session_id)`

### 这一步的意义

从用户角度，这意味着系统现在已经具备了“录错了还能修”的基础能力：

1. 输错一条事件，可以撤销
2. 发现某一步开始全错了，可以回退到某个事件
3. 不想删历史时，可以追加 correction 事件覆盖当前观测值
4. 随时可以重新回放日志，重建当前观测状态

### 当前还没做的部分

1. 回合级快照缓存
2. correction 事件的更细粒度类型体系
3. API 侧更细的错误分类和调试输出

---

## 25. API 入口实现状态

这一轮已经把 `agent_runtime` 的核心能力暴露到了现有 `api.py` 中。

### 当前新增的事件式端点

1. `POST /api/battle/start`
2. `POST /api/battle/<session_id>/event`
3. `GET /api/battle/<session_id>/report`
4. `GET /api/battle/<session_id>/recommend`
5. `GET /api/battle/<session_id>/events`
6. `POST /api/battle/<session_id>/undo`
7. `POST /api/battle/<session_id>/replay`
8. `POST /api/battle/<session_id>/correct`

### 这一阶段的意义

到这里为止，这个独立子系统已经不再只是“内部设计”：

- CLI 可以人工录入事件
- API 可以程序化驱动会话
- 推荐链路可以在不完整信息下工作

也就是说，`agent_runtime` 已经形成了一个完整的最小闭环原型。

---

## 24. 用户入口实现状态

这一轮已经补上了第一个真实用户入口：

- `new_one/cli_interactive.py`

它的作用不是替代最终产品形态，而是验证这套事件架构是否真正“能被人输入使用”。

### 当前 CLI 已支持的核心命令

1. 开局与阵容初始化
2. 出战切换
3. 血量与能量同步
4. 技能观测
5. 状态与印记录入
6. 心数更新
7. 推荐请求
8. 报告查看
9. 撤销、回放、修正
10. 事件日志查看

### 这一阶段的价值

它把当前 `agent_runtime` 的各层真正串起来了：

1. 用户命令
2. 事件标准化
3. 事件校验
4. 事件落日志
5. ObservationState 更新
6. 候选 BattleState 装配
7. 推荐聚合

这意味着当前系统已经具备了一个最小可运行的“命令行实时辅助原型”。

---

## 32. 推断结果对候选状态的反向影响

这一轮继续往前推进后，推断结果已经不只影响技能候选，还开始影响 `BattleState` 装配本身。

### 当前已接入 `StateAssembler` 的推断/观测结果

1. `stat_ranges`
   当前按区间中心值写回 `PetInstance.stats`

2. `inferred_trait_flags`
   当前会把迅捷类信号映射为 `priority_bonus`

3. `bench_hp_percent / bench_energy`
   当前会直接用于场下精灵的 HP / 能量装配

4. `team_resources`
   当前会映射到 `TeamState` 的同名字段

### 当前阶段结论

到这里为止，链路已经从：

- 事件影响推断

推进到了：

- 事件影响推断
- 推断影响技能候选
- 推断影响候选状态构造

这使得推荐层开始真正消费“我对对局的理解”，而不只是消费“我当前看见的表面状态”。
---

## 33. belief 拆分与推荐聚合

这一轮把候选状态上的单一 `confidence` 拆成了三部分：

1. `skill_probability`
   表示当前对手技能组候选的概率。
2. `profile_probability`
   表示当前属性剖面候选的概率，例如 `center` / `threat_high`。
3. `belief_weight`
   作为推荐层实际使用的候选权重，当前定义为：
   `skill_probability * profile_probability`

### 设计动机

之前推荐层虽然已经同时消费“技能候选”和“属性剖面候选”，但两者在装配阶段会被压扁成一个普通 `confidence`。这样会带来两个问题：

1. 无法区分“技能不确定”还是“属性不确定”。
2. `expected / hybrid` 的解释性不够，用户看不到权重来源。

### 当前实现

1. `InferredBattleState`
   新增：
   - `skill_probability`
   - `profile_probability`
   - `profile_label`
   - `belief_weight`

2. `StateAssembler`
   在展开候选状态时：
   - 保留 `OpponentModel` 输出的技能组概率
   - 保留属性剖面的独立权重
   - 不再在装配阶段提前把两者混成唯一字段

3. `RecommendationService`
   在聚合动作时：
   - 使用 `belief_weight` 作为 `expected / hybrid` 的候选权重
   - 在 `per_candidate` 中显式返回技能组概率和属性剖面概率
   - 在最终推荐中新增 `confidence_breakdown`

### 当前输出语义

推荐结果现在区分：

- `confidence`
  当前主导候选的总 belief 权重
- `confidence_breakdown.skill_probability`
  主导候选的技能组概率
- `confidence_breakdown.profile_probability`
  主导候选的属性剖面概率
- `confidence_breakdown.profile_label`
  主导候选对应的属性剖面标签

这让后续继续扩展为更正式的 belief-state 搜索时，不需要再回头拆已有接口。
## 补充记录：当前已完成 / 稍后继续

### 已完成

1. 已建立独立的 `agent_runtime/` 子系统，负责事件接入、观测状态维护、推断、候选状态装配与推荐编排。
2. 已完成事件主链：
   `EventNormalizer -> EventValidator -> BattleEventLog -> ObservationReducer -> ObservationState`
3. 已完成会话工具链：
   - `replay`
   - `undo`
   - `rollback`
   - `correction`
   - `session report`
4. 已完成证据采集与回写：
   - 速度证据
   - 伤害证据
   - 技能证据
   - 复制技能证据
   - 后排资源证据
   - 迅捷/优先效果证据
5. 已完成粗粒度数值推断，并把结果回写到 `ObservedPetState`：
   - `stat_ranges`
   - `inferred_natures`
   - `inferred_ev_spreads`
   - `inferred_trait_flags`
6. 已完成 `OpponentModel` 与 `StateAssembler` 的联动：
   - 技能候选会消费推断结果和特殊证据
   - 候选 `BattleState` 会消费属性区间、迅捷信号、后排资源、队伍共享资源
7. 已完成多策略推荐聚合：
   - `pessimistic`
   - `expected`
   - `hybrid`
8. 已把候选状态上的单一 `confidence` 拆成：
   - `skill_probability`
   - `profile_probability`
   - `belief_weight`
   当前推荐层已按 `belief_weight` 聚合，并返回 `confidence_breakdown`。

### 稍后继续

1. 技能组概率与属性剖面概率的联合归一化。
2. 推荐结果按“技能组簇 / 属性剖面簇”输出更细的风险摘要，而不只返回单候选说明。
3. 继续提高速度反推、伤害反推、双攻双防生命反推的公式质量。
4. 把更多特殊机制正式接入推断链：
   - buff / debuff
   - 特性修正
   - 更复杂的迅捷来源
   - 更多后排资源变化来源
5. 继续完善 API/CLI 的运行时验证与错误分类。
## 2026-04-10 补充

- 事件式接口现在按“常驻深度分析”模式设计：会话 `start / event / report / undo / replay / correct` 都应返回当前推荐，不再把深度分析依赖成单独按钮流程。
- 全信息局面构造接口补充了 `bloodline` 输入位，现阶段至少支持 `leader / polluted / element:<属性> / 中文血脉名` 的归一化。
- `leader` 血脉已进入规则层：首领化合法性与 `月光审判 / 天通地明 / 绒粉星光` 这类血脉判定特性开始消费该字段。
- “聚能”继续保持为常驻可选行动，不因当前 HP 是否已满而隐藏；新增回归测试覆盖“满血仍可聚能”。
