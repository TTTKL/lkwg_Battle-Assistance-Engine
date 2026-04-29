# 大文件拆分入口

目标：降上下文成本，不改行为。

## 已完成

- `extended_battle_engine.py` 已拆出：
  - `pre_action.py`
  - `action_phase.py`
  - `skill_damage.py`
  - `end_turn.py`

## 下一步优先级

1. 继续拆 `_execute_skill` 前置准备段
2. 再拆 `_apply_skill_effects`
3. 最后拆 `trait_processor.py`

## 原则

1. 不改外部接口
2. 一次只拆一块
3. 每步后跑测试

## 验证

```bash
python test_integration.py
python test_skill_effects.py
python test_runtime_state_copy.py
```
