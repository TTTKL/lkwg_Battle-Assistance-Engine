# 目录结构说明

更新日期：2026-04-11

## 当前分层

- `engine_core/`
  主分析引擎目录。完整信息搜索、战斗模拟、`agent_runtime` 原型、CLI/API 入口都在这里。
- `battle_analyzer/`
  兼容别名，指向 `engine_core/`。
- `new_one/`
  兼容别名，指向 `engine_core/`。保留它是为了不打断旧命令、旧脚本和历史路径引用。
- `legacy_workspace/Calculator/`
  正式命名的历史工作台入口。
- `calculator_workspace/Calculator/`
  兼容别名，指向历史工作台目录。
- `20260402114626/Calculator/`
  历史兼容路径，暂时保留。
- 根目录文档
  `PROJECT_SUMMARY.md`、`TODO.md`、`USER_GUIDE.md`、`DEVELOPMENT_NOTES.md` 负责记录阶段状态、下一步计划和使用方式。

## engine_core 内部分层

- `core/`
  核心数据结构与状态定义。
- `engine/`
  行动生成、战斗推进、状态处理、评估、搜索。
  - `evaluator.py` — 局面评估器 v3（HP/速度/克制/状态/心数非线性估值 + 胜率映射）
  - `search_engine.py` — 搜索引擎 v5（同时博弈 Maximin + Expectimax 混合，带迭代加深与宽度控制）
- `agent_runtime/`
  面向暗箱/事件式输入的运行时子系统。
  - `engine/behavior_predictor.py` — 对手行为预测器（三层模型 + 预读分析）
  - `engine/recommendation_service.py` — 推荐服务（集成预测 + 跨候选聚合）
  - `engine/opponent_model.py` — 对手技能组候选推断
  - `engine/stat_inferrer.py` — 属性区间反推引擎
  - `engine/state_assembler.py` — BattleState 候选装配器
- `docs/reference/`
  机制参考文档。
- `docs/status/`
  进度、里程碑和实现状态文档。

## 本次整理的目标

- 把对外项目根统一到 `LK_Engine`
- 把真实引擎目录统一为 `engine_core/`
- 把旧网页入口统一到 `legacy_workspace/Calculator/`
- 清理 `new_one/new_one/docs` 这类重复嵌套结构
- 逐步把历史日期目录替换成带语义的目录名，并保留兼容别名
- 保留旧路径兼容层，尽量不改现有运行方式
