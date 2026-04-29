# agent_runtime 实施计划

## 当前定位

`agent_runtime/` 是对现有 `engine_core/` 完整信息分析引擎的一层独立封装。

它负责：

- 用户事件接入
- 对局状态追踪
- 不完整信息管理
- 候选状态装配
- 推荐服务编排

它暂不负责：

- 具体伤害/状态/特性结算
- 完整规则模拟
- 直接替代现有 `ExtendedBattleEngine`

## 已建立的结构边界

### core

- `events.py`
  统一事件模型
- `observation.py`
  统一观测状态模型

### tracker

- `event_log.py`
  保存事件真源
- `event_normalizer.py`
  将外部输入标准化为统一 BattleEvent
- `event_validator.py`
  校验事件结构和会话一致性
- `observation_reducer.py`
  事件到观测状态的 reducer
- `session_manager.py`
  单场会话管理

### engine

- `opponent_model.py`
  对手技能组推断入口
- `state_assembler.py`
  观测状态到搜索状态的装配入口
- `recommendation_service.py`
  对外推荐服务门面

## 推荐的下一批实现顺序

1. 继续提高属性推断的数值质量
2. 引入 team_resources -> TeamState 的映射
3. 增加回合级快照与调试输出
4. 为 API 端点增加更细的错误分类与调试输出
5. 扩充事件类型，覆盖更多高信息量证据

## 关键约束

- 观测事实不得被推断值静默覆盖
- 事件日志必须可回放
- 推荐结果必须能解释其依赖的假设
- 新子系统尽量通过组合接入旧引擎，而不是修改旧引擎内部流程

## 当前已完成的最小闭环

当前已经具备：

1. 事件标准化
2. 事件基础校验
3. 事件落日志
4. 事件驱动更新 `ObservationState`

当前 `ObservationReducer` 已支持：

- `BATTLE_STARTED`
- `TURN_STARTED`
- `OPPONENT_ACTION_OBSERVED`
- `SKILL_USED`
- `DAMAGE_OBSERVED`
- `HP_PERCENT_UPDATED`
- `ENERGY_UPDATED`
- `STATUS_APPLIED`
- `STATUS_REMOVED`
- `MARK_UPDATED`
- `PET_SWITCHED`
- `PET_FAINTED`
- `HEARTS_UPDATED`
- `STATE_CORRECTED`

当前仍未完成：

- 回放接口封装
- 复杂 correction 粒度
- `DamageEvent` 到属性推断的自动连接
- `SearchEngine` 的真实推荐接入
- `TeamState` 与多印记机制的完整装配

当前已补充的稳健性处理：

- 若 `ObservationState` 中出现数据文件里不存在的精灵名，`StateAssembler` 会返回带 assumptions 的失败候选，而不是直接抛异常
- `learnable_skills` 会先归一化为技能名列表，兼容字符串或字典两种数据形态
- `BattleSessionManager` 已支持 replay / undo / rollback / correction
- `RecommendationService` 已支持 pessimistic / expected / hybrid 三种聚合
- `OpponentModel` 已为候选技能组输出归一化 probability
- `ObservationState` / `StatInferrer` 已支持高信息量证据模型
- `ObservationReducer` 已通过 `EvidenceCollector` 自动采集证据
- `BattleSessionManager` 已在事件追加/回放后自动回写粗粒度推断结果
- `OpponentModel` 已开始消费推断结果与特殊证据，动态调整技能候选权重
- `StateAssembler` 已开始消费推断结果与后排资源观测，构造更贴近当前推断的候选状态
- `StateAssembler` 已开始展开属性剖面候选，让搜索看到同技能组下的数值不确定性

当前已提供的用户入口：

- `cli_interactive.py`
  允许用户直接录入事件并请求推荐
- `api.py`
  已支持事件式会话端点：start / event / report / recommend / events / undo / replay / correct

## 新增设计产物

- `state_assembly_design.md`
  记录 `ObservationState -> BattleState` 的字段映射策略

- `opponent_model.py`
  当前已接入 `DataLoader`，支持基于 `learnable_skills` 生成平衡型/进攻型/功能型候选技能组，输出归一化 probability，并消费推断结果与特殊证据

- `state_assembler.py`
  当前已能构造最小可用的候选 `BattleState`，并开始消费 `stat_ranges / inferred_trait_flags / bench resources / team_resources`，同时展开属性剖面候选

- `recommendation_service.py`
  当前已能对候选状态调用现有 `GameAnalysisEngine`，并支持 pessimistic / expected / hybrid 三种聚合

- `stat_inferrer.py`
  当前已建立速度/伤害/复制技能/后排资源/迅捷等证据的统一推断入口，并能把粗粒度推断结果回写到 `ObservedPetState`

- `evidence_collector.py`
  当前已能从技能、伤害、资源同步、修正事件中抽取高信息量证据
## 新增进展：belief 权重拆分

当前推荐链新增了一个更清楚的中间层：

1. `OpponentModel` 负责给技能组候选概率
2. `StateAssembler` 负责给属性剖面权重
3. `RecommendationService` 使用 `belief_weight` 进行聚合

当前实现里：
- `belief_weight = skill_probability * profile_probability`
- `expected` 使用 belief 权重求加权均值
- `hybrid` 仍为 `0.7 * worst + 0.3 * expected`

当前仍未完成的部分：
- 技能组概率和属性剖面概率的联合归一化
- 按“技能组簇 / 属性剖面簇”输出更细粒度风险摘要
- 更正式的 belief-state 搜索
## 当前里程碑记录

### 本阶段已完成

1. 独立事件层与会话层骨架已完成。
2. `ObservationState` 已能持续消费高信息量事件。
3. `StatInferrer` 已能把证据回写为粗粒度属性/性格/努力/特性推断结果。
4. `OpponentModel` 已能消费这些推断结果，调整技能候选概率。
5. `StateAssembler` 已能展开：
   - 技能组候选
   - 属性剖面候选
6. `RecommendationService` 已能按 belief 权重聚合动作价值。

### 稍后继续的实现点

1. 技能组概率与属性剖面概率的联合归一化。
2. belief 聚合的风险摘要分层输出：
   - 技能组层
   - 属性剖面层
   - 最终动作层
3. 更贴近真实公式的速度/伤害反推。
4. 把更多特殊事件纳入数值推断，而不只纳入文本证据。
5. 为 CLI/API 增加更完整的可回归验证样例。
