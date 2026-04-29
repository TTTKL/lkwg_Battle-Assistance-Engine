# 引擎表现 Bug 入口

只用于修“引擎表现和游戏实际不一致”的问题。

## 默认阅读

1. `engine_core/CLAUDE.md`
2. `engine_core/game_analysis_engine.py`
3. 按问题类型只读一个：
   - 合法行动不对：`engine/action_generator.py`
   - 技能/回合结算不对：`engine/extended_battle_engine.py`
   - 回合准备不对：`engine/pre_action.py`
   - 技能阶段不对：`engine/action_phase.py`
   - 伤害不对：`engine/skill_damage.py`
   - 回合结束不对：`engine/end_turn.py`
   - 状态不对：`engine/status_processor.py`
   - 特性不对：`engine/trait_processor.py`

## 默认不读

- 根 `README.md`
- `docs/implementation.md`
- `docs/game_mechanics.md`（除非要核对机制）
- `legacy_workspace/Calculator/index.html`（除非是前后端同步问题）
- `_archive/`、测试文件、大型 JSON

## 排查顺序

1. 先确认预期机制
2. 定位属于：行动生成 / 技能结算 / 状态处理 / 特性触发
3. 只做最小修复
4. 跑相关测试

## 提问模板

```text
按 engine_core/docs/bugfix_entry.md 处理，不要全项目阅读。

问题：
复现条件：
预期结果：
实际结果：

如能定位，做最小修复并运行相关测试。
```
