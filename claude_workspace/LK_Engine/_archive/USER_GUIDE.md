# 用户手册

更新日期：2026-04-11

## 一键启动

```bash
cd E:\claude_workspace\LK_Engine\legacy_workspace\Calculator
python server.py
```

打开 `http://localhost:5173` — 静态文件和 Python 引擎 API 由同一服务提供。

> 旧的 `apps/calculator_web` 符号链接已失效。请使用上面的真实路径。

用途：

- 当前主要工作台
- 编队配置
- 明箱 / 暗箱分析（搜索 v5 + 评估器 v3）
- 首发选择与回合执行
- 右侧引擎分析边栏（调用 Python 引擎 `/api/analyze`）
- 运行时控制台在 `/runtime-console`

### 引擎 API 端点（同端口）

| 端点 | 说明 |
|------|------|
| `/api/analyze` | 最佳行动分析 |
| `/api/eval` | 快速局面评估 |
| `/api/simulate` | 完整对战模拟 |
| `/api/pets` | 精灵列表 |
| `/api/skills` | 技能列表 |
| `/api/save-teams` | 队伍存档 |
| `/runtime-console` | 事件运行时控制台 |
| `/api/battle/*` | 事件驱动会话 API |

### 仅引擎 API（不需要前端时）

```bash
cd E:\claude_workspace\LK_Engine\engine_core
python api.py
```

独立运行在 `http://127.0.0.1:5000`。

## 旧网页当前默认行为

### 默认编队

- `默认编队1`
  - 我方默认编队
  - 不可删除
- `默认编队2`
  - 敌方默认编队
  - 明箱模式自动导入
  - 不可删除

### 自动导入规则

- 暗箱模式
  - 自动导入我方 `默认编队1`
  - 敌方默认不导入
- 明箱模式
  - 自动导入我方 `默认编队1`
  - 自动导入敌方 `默认编队2`

### 战斗启动流程

旧网页当前不是“导入后直接第一回合”，而是：

1. 导入双方队伍
2. 点击 `准备首发`
3. 在第 0 回合分别为双方选择首发
4. 进入第 1 回合待执行，并立即启动引擎分析

### 当前已实现的若干规则

- 聚能在满能量时仍允许选择。
- 聚能按状态类行动处理，可被 `应对状态` 应对。
- 推荐换宠会直接显示目标精灵名。
- 推荐技能与手动选中技能使用不同高亮，不会重叠。

## 推荐启动方式

```bash
cd E:\claude_workspace\LK_Engine\legacy_workspace\Calculator
python server.py
```

一条命令即可，浏览器访问 `http://localhost:5173`。

自定义端口：`python server.py 8080`

## 建议回归检查

### 旧网页

先测：

1. 页面打开后默认编队是否按模式自动导入
2. `准备首发 -> 选择首发 -> 进入第1回合` 是否正常
3. 首发确认后右侧分析区是否立即出现推荐
4. 满能量时是否仍然可以选 `聚能`
5. `应对状态` 是否能正确应对 `聚能`
6. 推荐换宠是否明确显示换哪一只
7. 推荐高亮与选中高亮是否区分清楚

### 新网页

再测：

1. `start`
2. `import_state`
3. `rollback_import`
4. `clear_events`
5. `report / imports`

## 参考文档

- 当前状态总览：
  - [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)
- 下一步方向：
  - [TODO.md](./TODO.md)
- 开发注意事项：
  - [DEVELOPMENT_NOTES.md](./DEVELOPMENT_NOTES.md)
