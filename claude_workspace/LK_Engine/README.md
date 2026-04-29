# LK_Engine — 洛克王国世界对战分析引擎

更新日期：2026-04-14

---

## 快速启动

```bash
cd LK_Engine/legacy_workspace/Calculator
python server.py          # 默认端口 5173
```

浏览器访问 `http://localhost:5173`。自定义端口：`python server.py 8080`。

---

## 目录结构

```
LK_Engine/
├── engine_core/               ← 分析引擎（Python）
│   ├── CLAUDE.md              ← 🔑 引擎开发指南（修改引擎时必读）
│   ├── game_analysis_engine.py
│   ├── core/models.py
│   ├── engine/                ← 行动生成、战斗推进、评估、搜索
│   ├── api.py                 ← Flask REST API
│   ├── data_loader.py
│   ├── docs/
│   │   ├── game_mechanics.md  ← 游戏/引擎机制参考
│   │   ├── implementation.md  ← 实现状态总览
│   │   ├── bugfix_entry.md    ← 表现 bug 入口
│   │   ├── refactor_entry.md  ← 拆分入口
│   │   └── agent_runtime.md   ← 暗箱对战子系统
│   └── agent_runtime/         ← 事件驱动运行时
├── legacy_workspace/Calculator/ ← Web 工作台（HTML + JS）
│   ├── server.py              ← 一键启动（静态文件 + API）
│   ├── index.html             ← 主界面
│   └── Data/                  ← 游戏数据 JSON
└── README.md                  ← 本文件
```

兼容别名：`battle_analyzer/` → `engine_core/`、`new_one/` → `engine_core/`

---

## 当前状态

项目已进入**"可持续验证和修正的对战分析工作台"**阶段：

- Web 工作台可完成：编队导入、首发选择、引擎态回合执行、明箱/暗箱分析
- 引擎分析区显示：推荐动作、相对评分、胜率、搜索统计
- 前端默认以引擎返回状态为准：`/api/analyze` / `/api/resolve` 返回完整 `state`、合法行动和 action panel，前端回写技能顺序、能耗、冷却、队伍资源

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/analyze` | 最佳行动分析 |
| `POST /api/eval` | 快速局面评估 |
| `POST /api/simulate` | 完整对战模拟 |
| `GET /api/pets` / `GET /api/skills` | 数据查询 |
| `GET /runtime-console` | 事件运行时控制台 |
| `/api/battle/*` | 事件驱动会话 API |

---

## 下一步方向

**高优先级**：搜索可信度校准、agent_runtime 回放闭环、规则尾项收口

**中优先级**：状态底盘加固、前端残余静态读取点清理、特性尾项补完

**暂缓**：大规模搜索替换、OCR、UI 重写

---

## 文档索引

默认规则：修“引擎表现和游戏实际不一致”的问题时，先看 `engine_core/docs/bugfix_entry.md`，不要全项目阅读。

| 文档 | 路径 | 何时读 |
|------|------|--------|
| **引擎开发指南** | `engine_core/CLAUDE.md` | **修改引擎代码时必读** |
| 引擎技术说明 | `engine_core/README.md` | 查结构、数据、接口时 |
| 表现 Bug 入口 | `engine_core/docs/bugfix_entry.md` | 修引擎表现 bug 时 |
| Bug 提问模板 | `engine_core/docs/bugfix_prompt.md` | 直接复制提问时 |
| 拆分入口 | `engine_core/docs/refactor_entry.md` | 拆大文件时 |
| 游戏机制参考 | `engine_core/docs/game_mechanics.md` | 查阅具体机制时 |
| 实现状态总览 | `engine_core/docs/implementation.md` | 查阅已/未实现清单时 |
| 暗箱子系统 | `engine_core/docs/agent_runtime.md` | 涉及暗箱模式时 |
