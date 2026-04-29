# agent_runtime

事件驱动的实时对战辅助子系统。

这一层与现有完整信息引擎相对独立，职责是：

1. 接收用户逐回合输入的对局事件
2. 维护 `ObservationState`
3. 对未知信息做有限推断
4. 组装候选完整状态
5. 调用现有搜索引擎给出推荐

设计原则：

- 不重写 `engine_core/engine/extended_battle_engine.py`
- 不破坏现有 `game_analysis_engine.py` 的完整信息入口
- 以事件日志为真源
- 显式区分观测事实与推断结果

目录说明：

```text
agent_runtime/
├── core/
│   ├── events.py
│   └── observation.py
├── tracker/
│   ├── event_log.py
│   ├── event_normalizer.py
│   ├── event_validator.py
│   ├── evidence_collector.py
│   ├── observation_reducer.py
│   └── session_manager.py
├── engine/
│   ├── opponent_model.py
│   ├── recommendation_service.py
│   ├── stat_inferrer.py
│   └── state_assembler.py
└── docs/
    ├── implementation_plan.md
    ├── state_assembly_design.md
    └── evidence_inference_design.md
```

用户入口：

- `../cli_interactive.py`
  基于 `agent_runtime` 的交互式事件录入 CLI

首阶段目标：

- 建立稳定的数据结构边界
- 形成“事件 -> 观测状态 -> 候选状态 -> 推荐”的主链路
- 为后续 CLI/API 接入留出明确接口

当前已补齐的最小事件链路：

1. 松散输入先通过 `EventNormalizer` 归一化为 `BattleEvent`
2. 再通过 `EventValidator` 做结构与会话校验
3. 校验通过后写入 `BattleEventLog`
4. `ObservationReducer` 将事件应用到 `ObservationState`

当前会话工具能力：

1. `replay_session(session_id)`
   从事件日志重建 `ObservationState`
2. `undo_last_event(session_id)`
   撤销最后一条事件并自动重放
3. `rollback_to_event(session_id, event_id)`
   回退到指定事件
4. `apply_correction(...)`
   以 `STATE_CORRECTED` 事件写入用户修正
5. `apply_import_snapshot(...)`
   把敌方当前战况快照展开为一批 correction 事件，不清空既有证据
6. `clear_events(session_id)`
   清空当前会话事件和推断状态，但保留会话配置
7. `get_session_report(session_id)`
   输出简要会话概览

当前已提供的用户入口：

- `python cli_interactive.py`
  进入交互模式，支持 `start / switch / hp / energy / skill / status / mark / hearts / import / recommend / report / undo / replay / clear-events / correct / events`
- `GET /runtime-console`
  极简浏览器控制台，适合真实对战时用按钮和表单做快速录入与校准
- `api.py`
  已新增事件式端点，可通过 HTTP 驱动会话、事件、推荐、撤销、校准导入和修正

当前 reducer 已覆盖的事件包括：

- 开局初始化
- 回合开始
- 技能观测/技能使用
- 血量同步
- 能量同步
- 状态施加/移除
- 印记更新
- 换宠
- 死亡
- 心数更新
- 修正事件

当前“状态漂移修正”方案：

1. 普通小偏差继续使用 `correct`
2. 发现暗箱记录失误时，优先使用 `import_state` / `import opponent ...`
3. `import` 只校准敌方当前资源，不会清空已记录技能和证据
4. 如果导入本身填错了，可以按 `import_batch_id` 整批撤回
5. 真正需要从头重记整局时，再使用 `clear_events`

当前用户侧辅助查看能力：

1. `report`
   输出更偏实战使用的当前局面摘要
2. `imports`
   查看最近导入批次列表
3. `imports <import_batch_id>`
   查看某次导入校准展开出的 correction 明细

当前对手推断层的设计进展：

1. `OpponentModel` 已能接入 `DataLoader`
2. 已支持读取 `PetTemplate.learnable_skills`
3. 已支持按本系、技能类别、能量可达性、先手、多段等因素做粗评分
4. 当前会生成三类候选技能组：
   - 平衡型
   - 进攻型
   - 功能型
5. 候选技能组现在会归一化出 `probability`
6. `OpponentModel` 已开始消费：
   - `inferred_natures`
   - `inferred_ev_spreads`
   - `inferred_trait_flags`
   - `copy_skill_evidence`
   - `bench_resource_evidence`
   - `quick_effect_evidence`

当前证据推断层的设计进展：

1. `ObservationState` 已加入速度、伤害、复制技能、后排资源、迅捷等证据容器
2. `EvidenceCollector` 已接入 reducer，会从现有事件流中提取证据对象
3. 已新增 `stat_inferrer.py`，用于承接高信息量事件的推断接口
4. `BattleSessionManager` 已在 append/replay 后自动触发 `StatInferrer.apply_to_observation()`
5. 当前这层已能把粗粒度推断结果回写到：
   - `stat_ranges`
   - `inferred_natures`
   - `inferred_ev_spreads`
   - `inferred_trait_flags`
6. 当前速度与攻防生命推断已开始参考现有引擎的出手顺序/伤害公式做近似反推

当前状态装配层的设计进展：

1. `StateAssembler.describe_plan()` 已能输出字段映射预览
2. `state_assembly_design.md` 已明确 `ObservationState -> BattleState` 的字段来源和未决问题
3. `StateAssembler.build_candidates()` 已能产出最小可用候选 `BattleState`
4. `RecommendationService` 已能识别候选状态是否装配成功
5. 候选 `BattleState.confidence` 当前直接来自 `SkillSetCandidate.probability`
6. `StateAssembler` 已开始消费：
   - `stat_ranges`
   - `inferred_trait_flags`
   - `bench_hp_percent`
   - `bench_energy`
   - `team_resources`
7. 当前会针对对手当前出战精灵展开多个属性剖面候选：
   - `center`
   - `threat_high`

当前推荐层的设计进展：

1. `RecommendationService` 已能对每个候选 `BattleState` 调用现有 `GameAnalysisEngine.analyze_state()`
2. 当前已支持三种聚合策略：
   - `pessimistic`
   - `expected`
   - `hybrid`
3. `hybrid` 为默认模式，按 `0.7 * worst + 0.3 * expected` 聚合
4. 这已经比“每个候选各自推荐”更接近真实不确定性决策
## belief 权重拆分

当前候选状态不再只暴露单一 `confidence`。

`InferredBattleState` 现在区分：
- `skill_probability`
- `profile_probability`
- `profile_label`
- `belief_weight`

其中 `belief_weight = skill_probability * profile_probability`，是推荐层在 `expected / hybrid` 聚合时实际使用的权重。

`RecommendationService` 当前新增：
- `confidence_breakdown`
- `per_candidate` 中的技能组概率 / 属性剖面概率明细
- 基于 belief 的聚合说明

这一步的目的，是把“技能组不确定性”和“属性剖面不确定性”从接口层显式分开，避免后续继续扩展 belief-state 搜索时还要回头拆字段。
## 当前状态

### 已完成

1. 事件层闭环已经打通：
   `normalize -> validate -> log -> reduce -> infer -> assemble -> recommend`
2. 已支持会话级 `undo / replay / rollback / correction`。
3. 已支持证据采集、属性推断、技能候选推断、候选状态装配。
4. 已支持 `CLI` 与事件式 `API` 入口。
5. 推荐层已支持：
   - `pessimistic`
   - `expected`
   - `hybrid`
6. 候选状态权重已拆分为：
   - `skill_probability`
   - `profile_probability`
   - `belief_weight`
7. 已支持“敌方战况导入”和“清空事件信息（二次确认）”

### 待继续

1. 对技能组概率和属性剖面概率做更严格的联合归一化。
2. 输出按“技能组簇 / 属性剖面簇”聚合的风险说明。
3. 继续细化速度、伤害、双攻、双防、生命的反推公式。
4. 纳入更多特性、buff/debuff、后排资源变化的数值影响。
5. 做更完整的 CLI/API 端到端运行时验证。
