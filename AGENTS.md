# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 项目概述

洛克王国世界（6v6）对战分析引擎。给定局面，评估优劣并搜索最佳走步。包含一个 Flask REST API、一个 Web 工作台（前端 + 静态服务）、以及一个事件驱动的暗箱对战辅助子系统。

代码位于 `20260414/claude_workspace/` 下，核心引擎在 `LK_Engine/engine_core/`，前端在 `LK_Engine/legacy_workspace/Calculator/`。

## 常用命令

所有引擎命令需在 `LK_Engine/engine_core/` 目录下运行。

### 启动 Web 工作台（前端 + 引擎 API 合并服务）
```bash
cd LK_Engine/legacy_workspace/Calculator
python server.py          # http://localhost:5173
python server.py 8080     # 自定义端口
```

`server.py` 启动时会**同时自动启动** `engine_core/api.py` 独立引擎服务（端口 5000），并在退出时自动清理。日志示例：
```
[启动] 独立引擎服务已就绪  http://localhost:5000
==================================================
  地址:         http://localhost:5173
  独立引擎 API: http://localhost:5000  ✓ 运行中
==================================================
```

### 运行测试
```bash
cd LK_Engine/engine_core

# 集成测试（首选验证方式）
python test_integration.py

# 其他专项测试
python test_skill_effects.py
python test_slot_effects.py
python test_runtime_state_copy.py
python test_mark_effects.py
python test_trait_system.py
python test_hearts_system.py
python test_slot_traits.py
```

### CLI 演示
```bash
cd LK_Engine/engine_core
python cli.py --depth 2
```

### 独立 API 服务（通常不需要手动启动）
```bash
cd LK_Engine/engine_core
python api.py   # 端口 5000，server.py 已自动管理此进程
```

## 依赖

仅 `flask>=2.3.0`（Python 3，无其他第三方依赖）。`server.py` 启动时若缺 Flask 会自动 pip install。

## 架构

### 目录结构

```
LK_Engine/
├── engine_core/                ← 分析引擎（Python）
│   ├── game_analysis_engine.py ← 总入口：组装 DataLoader + Engine + Evaluator + Search
│   ├── core/
│   │   ├── models.py           ← 状态真源：PetInstance, BattleState, Action 等所有 dataclass
│   │   └── status_effects.py   ← StatusEffectType 枚举
│   ├── engine/
│   │   ├── extended_battle_engine.py ← 战斗推进（apply_action → 新状态）
│   │   ├── pre_action.py       ← 回合准备阶段
│   │   ├── action_phase.py     ← 技能阶段结算
│   │   ├── skill_damage.py     ← 伤害段计算
│   │   ├── end_turn.py         ← 回合结束处理
│   │   ├── action_generator.py ← 合法行动生成
│   │   ├── evaluator.py        ← 局面评分
│   │   ├── search_engine.py    ← 搜索最佳行动
│   │   ├── status_processor.py ← 状态效果处理
│   │   ├── trait_processor.py  ← 特性触发处理
│   │   ├── mark_effects.py     ← 印记效果处理
│   │   └── slot_effects.py     ← 槽位/传动效果
│   ├── api.py                  ← Flask Blueprint（engine_bp），所有 /api/* 路由
│   ├── data_loader.py          ← 从 JSON 加载游戏数据
│   ├── paths.py                ← 数据目录解析（多路径候选）
│   ├── agent_runtime/          ← 暗箱对战子系统（事件驱动，部分可观测）
│   └── docs/                   ← 机制参考文档
└── legacy_workspace/Calculator/ ← Web 工作台
    ├── server.py               ← 一键启动（Flask 静态服务 + 引擎蓝图）
    ├── index.html              ← 主界面
    └── Data/                   ← 游戏数据 JSON
```

### 战斗主链路

```
pre_action → action_phase → _execute_skill → skill_damage / _apply_skill_effects → end_turn
```

`ExtendedBattleEngine.apply_action(state, p_action, o_action) → BattleState` 是核心接口，输入当前状态和双方行动，返回新状态（原状态不变，搜索树安全）。

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/analyze` | 给定局面，返回最佳行动 + 全行动评分 + 胜率 |
| `POST /api/eval` | 快速局面评估 |
| `POST /api/simulate` | 完整对战模拟 |
| `GET /api/pets` / `GET /api/skills` | 数据查询 |
| `GET /runtime-console` | 暗箱事件运行时控制台 |
| `/api/battle/*` | 事件驱动会话 API（暗箱模式） |

### 暗箱对战子系统 (`agent_runtime/`)

独立封装，用于部分可观测的实际对战辅助。接收逐回合事件 → 维护 ObservationState（己方确定，敌方部分可观测） → 推断未知信息（IV、技能组） → 组装候选 BattleState → 调用搜索引擎推荐。涉及暗箱模式时参考 `docs/agent_runtime.md`。

### 数据流

- `DataLoader` 通过 `paths.get_default_data_dir()` 自动解析数据目录（多路径候选，优先 `legacy_workspace/Calculator/Data/`）
- 主数据文件：`pets.json`, `skills.json`, `battle_data.json`, `type_chart.json`, `common.json`
- `battle_data.json` 优先于 `skills.json` 加载技能数据，`energy_cost` 以 `battle_data.json` 为权威值
- `bloodline_overrides.json` 在 `docs/` 下，手动维护精灵血脉分类
- 前端 `my_teams.json` 存储队伍快照，技能 energy 字段为历史快照，**引擎不使用此值**（始终以 `battle_data.json` 为准）

## 必守约束

1. **不要重新引入旧的 `ExtendedPetState` / `ExtendedBattleState`** — 已合并进 `PetInstance` / `BattleState`
2. **修改 `PetInstance` / `BattleState` / `TeamState` 字段时，必须同步 `copy()` 方法** — 搜索树依赖正确的深拷贝
3. **`runtime_flags` 需保持可深拷贝** — `PetInstance` 通过 `__getattr__`/`__setattr__` 将 `_xxx` 字段统一托管到 `runtime_flags`
4. **首领化仅限 `bloodline == "leader"`，愿力冲击仅限 `bloodline != "leader"`**，两者互斥，由 `team_state` 控制
5. 机制修复优先局部修复，不做大重写
6. 前端新增状态时需检查同步链：`buildApiPayloadFromB()` → `_build_team()` → `_format_state()` → `/api/resolve` → `_syncEngineStateToFrontend()`
7. **`_build_team()` 只接受 `energy_cost_override` 字段覆盖技能能量**，普通的 `energy`/`energy_cost` 快照字段被忽略，防止旧数据覆盖引擎权威值
8. **`score_all_actions` 和 `_score_action_worst` 必须捕获 `_TimeoutSignal`**，超时时退化为静态评估而非抛出异常
9. **不要修改对局信息的 JSON 导出格式** — 后续将部署 MAA 做事件侦测回传，导出格式需保持稳定兼容

## 已知修复（本期）

| 问题 | 修复位置 |
|------|---------|
| `server.py` 启动不自动带起 `api.py` | `server.py` — `_start_engine_subprocess()` + PID 文件 + 进程树清理 |
| 停止 `server.py` 后 `api.py` 残留 | `server.py` — `atexit` + `signal` + `finally` + `taskkill /T` |
| `/api/analyze` 返回 400 无错误详情 | `api.py` — `request.get_json(force=True, silent=True)`；全局 `@app.errorhandler(400)` 返回 JSON |
| 搜索超时导致 400（`_TimeoutSignal` 逃逸） | `search_engine.py` — `score_all_actions` 和 `_score_action_worst` 捕获 `_TimeoutSignal` |
| 前端技能快照 energy 覆盖引擎权威值 | `api.py _build_team()` — 改为仅接受 `energy_cost_override` |
| `GET /favicon.ico` 404 噪音 | `server.py` — 新增路由返回空白图标 |
| 400 响应体为 HTML 而非 JSON | `server.py` — `@app.errorhandler(400)` 全局覆盖 |

## 文档索引

| 场景 | 文档 |
|------|------|
| 修改引擎代码 | `engine_core/AGENTS.md` |
| 修引擎表现 bug | `engine_core/docs/bugfix_entry.md`（优先按此流程，不要全项目阅读） |
| 查阅游戏机制 | `engine_core/docs/game_mechanics.md` |
| 查实现边界 | `engine_core/docs/implementation.md` |
| 暗箱模式 | `engine_core/docs/agent_runtime.md` |
| 拆分重构 | `engine_core/docs/refactor_entry.md` |

**默认不读**：`_archive/` 目录、`__pycache__/`、测试文件、大型 JSON 数据文件。

## 排查定位

- **结果不对**：`ActionGenerator` → `ExtendedBattleEngine` → `Status/Trait/Mark` → `Evaluator` → `Search`
- **合法行动不对**：`engine/action_generator.py`
- **伤害不对**：`engine/skill_damage.py`
- **状态不对**：`engine/status_processor.py`
- **特性不对**：`engine/trait_processor.py`
- **评分/推荐异常**：`engine/evaluator.py` → `engine/search_engine.py`
- **API 返回 400**：先看服务器终端日志（`[WARNING] api: [analyze] 400 error:`），再看浏览器 F12 控制台（`[Engine] API 400 response:`）
- **搜索超时**：`search_engine.py` — 检查 `_TimeoutSignal` 是否被正确捕获；`score_all_actions` 和 `_score_action_worst` 均需捕获
- **技能能量不一致**：以 `battle_data.json` 为权威，前端 `my_teams.json` 快照值不传给引擎

## 源文件阅读顺序（仅在必要时）

1. `game_analysis_engine.py` — 总入口
2. `core/models.py` — 状态真源
3. `engine/action_generator.py` — 行动生成
4. `engine/extended_battle_engine.py` — 战斗推进
5. `engine/evaluator.py` — 局面评分
6. `engine/search_engine.py` — 搜索
7. `data_loader.py` — 数据加载
8. 按需读：`status_processor.py`、`trait_processor.py`、`mark_effects.py`、`slot_effects.py`
