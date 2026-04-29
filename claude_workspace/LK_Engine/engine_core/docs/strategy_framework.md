# 策略层机制框架

更新日期：2026-04-20

## 目标

为“引擎机制已实现，但策略估值尚未细化”以及“机制本身仍不完整”的印记、特性提供统一的策略接入口。

当前策略层不再把这类近似逻辑散落在 `evaluator.py` 主体里，而是统一收口到：

- `engine/strategy_mechanics.py`

## 当前结构

### 入口

- `evaluate_strategy_mechanics(ctx) -> StrategyMechanicResult`
- `Evaluator._strategy_mechanic_value(...)` 只负责构造上下文并取总分

### 上下文

- `StrategyMechanicContext`
  - `state`
  - `is_player`
  - `active_pet`
  - `enemy_active_pet`

### 输出

- `StrategyMechanicResult`
  - `score`
  - `breakdown`
  - `pending`

后续如果要做调试面板、策略 explain 或日志埋点，可以直接复用 `breakdown` / `pending`。

## 当前已接入的策略钩子

### 印记

- `moist_mark`
- `dragon_bite_mark`
- `wind_mark`
- `slow_mark`
- `charge_mark`
- `photosynthesis_mark`
- `frost_mark`
- `descent_mark`
- `thorn`

说明：
- 这些钩子当前属于“策略近似值”，不是战斗结算真源
- 战斗真源仍然在 `extended_battle_engine.py` / `mark_effects.py` / `status_processor.py`
- 未注册的印记仍走保底规则：`层数 * 50`

### 特性

当前先给一批“机制未完全实现或需要后续细化”的特性预留了保守占位钩子：

- `不朽`
- `先知`
- `预警`
- `哨兵`
- `威慑`
- `吟游之风`

说明：
- 这些钩子当前只提供保守策略分，不代表机制已经完整实现
- 真正补机制时，应优先补引擎结算，再决定是否要同步调整策略权重

## 待完善标记

`StrategyMechanicResult.pending` 用来记录“已经进入策略框架，但规则仍不完整”的机制。

当前主要包括：

- `momentum_mark`
- `photosynthesis_mark`
- `frost_mark`
- `不朽`
- `先知`
- `预警`
- `哨兵`
- `威慑`
- `吟游之风`

## 后续扩展方式

### 新增印记策略钩子

1. 在 `engine/strategy_mechanics.py` 中新增 `_hook_xxx_mark`
2. 使用 `register_mark_hook(...)` 注册
3. 如果该机制仍不完整，把说明加入 `PENDING_MARK_NOTES`
4. 补测试：至少覆盖“评分变化”或“最佳行动变化”

### 新增特性策略钩子

1. 在 `engine/strategy_mechanics.py` 中新增 `_hook_xxx_trait`
2. 使用 `register_trait_hook(...)` 注册
3. 如果只是占位，把说明加入 `PENDING_TRAIT_NOTES`
4. 如果该特性依赖复杂时序，优先先补战斗层，再补策略层

## 当前边界

1. 当前框架是“策略近似层”，不是战斗结算层
2. `pending` 目前只在代码内保留，尚未对外暴露
3. 特性占位分是保守值，目的是避免策略完全忽略该机制，不代表最终平衡
4. 同一种机制是否应该影响浅层静态评估、还是只该通过搜索展开体现，后续仍需逐项校正
