# agent_runtime — 暗箱对战辅助子系统

> 仅在涉及暗箱模式 / 事件驱动 / 对手预测时阅读此文档。
> 合并自原 `agent_runtime/README.md`、`agent_runtime/docs/*.md`、`agent_design.md`。

---

## 定位

`agent_runtime/` 是对 `engine_core/` 完整信息引擎的独立封装，职责是：
1. 接收用户逐回合输入的对局事件
2. 维护 `ObservationState`（己方确定，敌方部分可观测）
3. 对未知信息做有限推断（IV、技能组）
4. 组装候选 `BattleState`
5. 调用搜索引擎给出推荐

设计原则：不重写战斗引擎，不破坏完整信息入口，事件日志为真源。

---

## 目录结构

```
agent_runtime/
├── core/
│   ├── events.py           # 事件类型定义
│   └── observation.py      # ObservationState
├── tracker/
│   ├── event_log.py        # 事件存储
│   ├── event_normalizer.py # 事件标准化
│   ├── event_validator.py  # 事件校验
│   └── session_manager.py  # 会话管理（含导入/回滚/清空）
├── engine/
│   ├── observation_reducer.py     # 观测到状态的归约
│   ├── stat_inferrer.py           # 属性区间反推
│   ├── state_assembler.py         # BattleState 候选装配
│   ├── opponent_model.py          # 对手技能组候选推断
│   ├── behavior_predictor.py      # 对手行为预测（三层模型 + 预读）
│   └── recommendation_service.py  # 推荐服务（集成预测 + 跨候选聚合）
```

---

## 主链路

```
SessionManager → ObservationReducer → StatInferrer → StateAssembler
                                                   → BehaviorPredictor → RecommendationService
```

---

## 事件式 API 端点

所有端点在 `api.py` 中注册，前缀 `/api/battle/`。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/battle/start` | POST | 创建会话，设定双方队伍 |
| `/api/battle/<id>/event` | POST | 追加事件 |
| `/api/battle/<id>/report` | GET | 会话概览 + 推荐 |
| `/api/battle/<id>/recommend` | GET | 当前推荐 |
| `/api/battle/<id>/events` | GET | 事件日志 |
| `/api/battle/<id>/undo` | POST | 撤销最后一条事件 |
| `/api/battle/<id>/replay` | POST | 从日志重放 |
| `/api/battle/<id>/correct` | POST | 追加修正事件 |
| `/api/battle/<id>/import_state` | POST | 导入战况快照 |
| `/api/battle/<id>/clear_events` | POST | 清空事件 |
| `/api/battle/<id>/imports` | GET | 导入批次列表 |
| `/api/battle/<id>/rollback_import/<batch>` | POST | 撤回导入批次 |
| `/runtime-console` | GET | Web 控制台 |

---

## 对手行为预测器

三层模型：
1. **先验层**：博弈常识（攻击默认最高分、换宠/聚能基础分）
2. **局面层**：根据 HP/能量/克制动态调整（残血→换宠×3、低能量→聚能×2.5）
3. **历史层**：基于已观察行为模式修正（需 ≥3 条记录）

预读分析：读切（预判换宠）、读攻（预判攻击）、读能（预判聚能），输出反制策略和风险。

---

## CLI 使用

```bash
cd engine_core
python -m agent_runtime.cli
```

交互命令：`start`、`event`、`observe`、`import`、`rollback`、`clear`、`report`、`recommend`、`undo`、`replay`、`quit`。

---

> 原始完整设计文档（1555 行）已归档至 `_archive/agent_design.md`。
