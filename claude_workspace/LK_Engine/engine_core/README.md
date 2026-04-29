# engine_core — 引擎技术说明

更新时间：2026-04-14

只说明技术结构、数据来源和接口；改代码时优先看 `CLAUDE.md`。

## 当前结构

```text
engine_core/
├── core/models.py
├── engine/
│   ├── action_generator.py
│   ├── extended_battle_engine.py
│   ├── pre_action.py
│   ├── action_phase.py
│   ├── skill_damage.py
│   ├── end_turn.py
│   ├── status_processor.py
│   ├── trait_processor.py
│   ├── mark_effects.py
│   ├── slot_effects.py
│   ├── evaluator.py
│   └── search_engine.py
├── data_loader.py
├── game_analysis_engine.py
├── api.py
└── docs/
```

## 主链路

`GameAnalysisEngine → DataLoader → ExtendedBattleEngine → Evaluator → SearchEngine → ActionGenerator`

## 当前状态

- `BattleState` / `PetInstance` 是状态真源
- 战斗主流程已拆成：准备阶段、技能阶段、伤害段、回合结束
- 前端默认使用引擎返回状态，不再以本地 JS 结算为准
- 搜索和评估可直接用于 `/api/analyze` / `/api/resolve`

## 数据目录

- 默认通过 `paths.get_default_data_dir()` / `DataLoader()` 解析
- 当前优先路径：`../apps/calculator_web/Data/`
- 兼容历史路径，但不要在代码里硬编码旧目录

主数据文件：
- `battle_data.json`
- `pets.json`
- `skills.json`
- `type_chart.json`

## 常用命令

```bash
python cli.py --depth 2
python api.py
python test_integration.py
```

## 文档入口

- 改代码：`CLAUDE.md`
- 修表现 bug：`docs/bugfix_entry.md`
- 查机制：`docs/game_mechanics.md`
- 查实现边界：`docs/implementation.md`
- 做拆分：`docs/refactor_entry.md`
- 暗箱模式：`docs/agent_runtime.md`
