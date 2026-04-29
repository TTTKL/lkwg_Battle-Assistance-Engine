# 洛克王国世界 6v6 对战辅助引擎

这是一个面向《洛克王国世界》6v6 对战的分析与辅助项目。它可以在给定局面下评估双方优劣、搜索推荐行动，并提供 Web 工作台、Flask REST API，以及一个事件驱动的暗箱对战辅助子系统。

项目主体代码位于 `claude_workspace/LK_Engine/`：

- `engine_core/`：Python 分析引擎、搜索、评估、API 与测试
- `legacy_workspace/Calculator/`：Web 工作台与静态资源
- `engine_core/agent_runtime/`：部分可观测对战的事件驱动运行时

## 功能概览

- 6v6 对战局面评估：血量、能量、状态、特性、印记、槽位效果等
- 最佳行动搜索：生成合法行动并对候选动作评分
- Web 工作台：队伍编辑、首发选择、局面同步、推荐结果展示
- Flask API：提供分析、评估、模拟和数据查询接口
- 暗箱对战辅助：根据逐回合事件维护观察状态，推断敌方未知信息并调用搜索引擎推荐
- 游戏数据加载：从 JSON 数据文件加载精灵、技能、属性克制和通用配置

## 快速启动

从仓库根目录进入 Web 工作台：

```bash
cd claude_workspace/LK_Engine/legacy_workspace/Calculator
python server.py
```

默认访问地址：

```text
http://localhost:5173
```

自定义端口：

```bash
python server.py 8080
```

`server.py` 会同时启动独立引擎服务 `engine_core/api.py`，默认端口为 `5000`。退出 Web 服务时会自动清理引擎子进程。

## 运行测试

所有引擎测试建议在 `engine_core/` 目录下运行：

```bash
cd claude_workspace/LK_Engine/engine_core
python test_integration.py
```

常用专项测试：

```bash
python test_skill_effects.py
python test_slot_effects.py
python test_runtime_state_copy.py
python test_mark_effects.py
python test_trait_system.py
python test_hearts_system.py
python test_slot_traits.py
```

## CLI 演示

```bash
cd claude_workspace/LK_Engine/engine_core
python cli.py --depth 2
```

## 独立 API 服务

通常不需要手动启动，因为 Web 工作台会自动管理该服务。需要单独调试时可运行：

```bash
cd claude_workspace/LK_Engine/engine_core
python api.py
```

默认端口为 `5000`。

## 依赖

项目依赖较轻：

- Python 3
- `flask>=2.3.0`

`legacy_workspace/Calculator/server.py` 启动时如果检测到缺少 Flask，会尝试自动安装。

## 目录结构

```text
claude_workspace/LK_Engine/
|-- engine_core/
|   |-- game_analysis_engine.py      # 总入口：组装 DataLoader、Engine、Evaluator、Search
|   |-- api.py                       # Flask Blueprint 与 /api/* 路由
|   |-- data_loader.py               # JSON 数据加载
|   |-- paths.py                     # 数据目录解析
|   |-- core/
|   |   |-- models.py                # 状态真源：PetInstance、BattleState、Action 等
|   |   `-- status_effects.py        # 状态效果枚举
|   |-- engine/
|   |   |-- extended_battle_engine.py # 战斗推进核心
|   |   |-- action_generator.py       # 合法行动生成
|   |   |-- evaluator.py              # 局面评分
|   |   |-- search_engine.py          # 搜索最佳行动
|   |   |-- pre_action.py             # 回合准备阶段
|   |   |-- action_phase.py           # 技能阶段结算
|   |   |-- skill_damage.py           # 伤害计算
|   |   |-- end_turn.py               # 回合结束处理
|   |   |-- status_processor.py       # 状态效果处理
|   |   |-- trait_processor.py        # 特性触发处理
|   |   |-- mark_effects.py           # 印记效果处理
|   |   `-- slot_effects.py           # 槽位/传动效果处理
|   |-- agent_runtime/               # 暗箱对战辅助子系统
|   `-- docs/                        # 机制与开发文档
`-- legacy_workspace/Calculator/
    |-- server.py                    # 一键启动 Web 工作台与引擎 API
    |-- index.html                   # 主界面
    `-- Data/                        # 游戏数据 JSON/JS
```

## 战斗主链路

```text
pre_action -> action_phase -> _execute_skill -> skill_damage / _apply_skill_effects -> end_turn
```

核心接口：

```python
ExtendedBattleEngine.apply_action(state, p_action, o_action) -> BattleState
```

该接口输入当前状态和双方行动，返回一个新的 `BattleState`。原状态保持不变，以保证搜索树展开时状态隔离。

## API 端点

| 端点 | 说明 |
| --- | --- |
| `POST /api/analyze` | 给定局面，返回最佳行动、全行动评分和胜率 |
| `POST /api/eval` | 快速局面评估 |
| `POST /api/simulate` | 完整对战模拟 |
| `GET /api/pets` | 精灵数据查询 |
| `GET /api/skills` | 技能数据查询 |
| `GET /runtime-console` | 暗箱事件运行时控制台 |
| `/api/battle/*` | 事件驱动会话 API，用于暗箱模式 |

## 数据说明

数据目录由 `paths.get_default_data_dir()` 自动解析，优先使用：

```text
claude_workspace/LK_Engine/legacy_workspace/Calculator/Data/
```

主要数据文件：

- `pets.json`
- `skills.json`
- `battle_data.json`
- `type_chart.json`
- `common.json`

注意事项：

- `battle_data.json` 的技能数据优先级高于 `skills.json`
- 技能 `energy_cost` 以 `battle_data.json` 为权威值
- `my_teams.json` 中的技能能量字段属于历史快照，引擎不使用该值
- `bloodline_overrides.json` 位于 `engine_core/docs/`，用于维护精灵血脉分类

## 暗箱对战子系统

`agent_runtime/` 用于部分可观测的实际对战辅助。它通过逐回合事件维护 `ObservationState`：

```text
事件输入 -> 观察状态 -> 未知信息推断 -> 候选 BattleState -> 搜索推荐
```

涉及暗箱模式时，优先参考：

```text
claude_workspace/LK_Engine/engine_core/docs/agent_runtime.md
```

## 开发注意事项

- 不要重新引入旧的 `ExtendedPetState` / `ExtendedBattleState`，状态已经合并进 `PetInstance` / `BattleState`
- 修改 `PetInstance`、`BattleState`、`TeamState` 字段时，必须同步对应 `copy()` 方法
- `runtime_flags` 需要保持可深拷贝，搜索树依赖状态复制正确
- 首领化仅限 `bloodline == "leader"`，愿力冲击仅限 `bloodline != "leader"`，两者互斥
- 机制修复优先局部修复，避免不必要的大重写
- 前端新增状态时需要检查同步链：`buildApiPayloadFromB()` -> `_build_team()` -> `_format_state()` -> `/api/resolve` -> `_syncEngineStateToFrontend()`
- `_build_team()` 只接受 `energy_cost_override` 覆盖技能能量，普通 `energy` / `energy_cost` 快照字段会被忽略
- 搜索超时逻辑中，`score_all_actions` 和 `_score_action_worst` 必须捕获 `_TimeoutSignal`
- 不要修改对局信息 JSON 导出格式，后续事件侦测回传依赖其稳定兼容

## 排查入口

| 问题类型 | 优先查看 |
| --- | --- |
| 推荐或结果不符合预期 | `engine/action_generator.py` -> `extended_battle_engine.py` -> `evaluator.py` -> `search_engine.py` |
| 合法行动不对 | `engine/action_generator.py` |
| 伤害不对 | `engine/skill_damage.py` |
| 状态效果不对 | `engine/status_processor.py` |
| 特性不对 | `engine/trait_processor.py` |
| 评分异常 | `engine/evaluator.py`、`engine/search_engine.py` |
| API 返回 400 | 先看服务器终端日志，再看浏览器 F12 控制台 |
| 技能能量不一致 | 以 `battle_data.json` 为准 |

## 文档索引

| 场景 | 文档 |
| --- | --- |
| 修改引擎代码 | `claude_workspace/LK_Engine/engine_core/AGENTS.md` |
| 修引擎表现 bug | `claude_workspace/LK_Engine/engine_core/docs/bugfix_entry.md` |
| 查阅游戏机制 | `claude_workspace/LK_Engine/engine_core/docs/game_mechanics.md` |
| 查实现边界 | `claude_workspace/LK_Engine/engine_core/docs/implementation.md` |
| 暗箱模式 | `claude_workspace/LK_Engine/engine_core/docs/agent_runtime.md` |
| 拆分重构 | `claude_workspace/LK_Engine/engine_core/docs/refactor_entry.md` |

## 当前状态

项目已经包含可运行的 Web 工作台、REST API、核心搜索评估链路和多组机制测试。后续开发建议优先围绕搜索可信度校准、暗箱运行时回放闭环、机制边界补全和前端状态同步稳定性展开。
