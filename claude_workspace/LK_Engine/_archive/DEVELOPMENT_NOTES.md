# 开发经验与陷阱记录

> 给未来自己（和协作 AI）看的避坑指南。记录在这个项目中**真实浪费过时间/算力/token 的模式**，以及应对方法。

更新日期：2026-04-12

---

## 一、反复重读大文件（最高频的 token 浪费）

### 问题描述

`extended_battle_engine.py`（1175 行）、`trait_processor.py`（1637 行）、`data_loader.py`（957 行）在多轮对话中被反复完整读取，每次读取消耗大量 context。

### 根因

- 修改一个函数时，为了"确认上下文"把整个文件读进来
- 没有用 `offset`+`limit` 做定点读取
- 每次新对话开始时不确定文件当前状态，习惯性再读一遍

### 解决方法

1. **定点读取**：用 `Grep` 先找行号，再用 `Read offset=N limit=30` 只读目标函数
2. **记住稳定的函数位置**：`_execute_skill` 在 ~283 行，`_end_turn_processing` 在 ~831 行，`_apply_skill_effects` 在 ~495 行
3. **修改前只读函数签名附近**，确认 diff 后再 Edit

---

## 二、动态字段泛滥（`getattr` 模式的技术债）

### 问题描述

特性系统实现中大量使用 `getattr(pet, '_xxx', default)` 动态附加字段到 `PetInstance`：

```python
pet._holy_knight_power = True
pet._crackle_first = True
pet._is_first_attacker = False
pet._immortal_death_mark = 3
# ... 共 18 个独特动态字段名
```

### 为什么有问题

1. **`copy()` 不会复制**：`PetInstance.copy()` 是显式字段复制，动态字段在搜索树 copy 时全部丢失
2. **搜索树状态不一致**：引擎依赖 `BattleState.copy()` 做 Minimax 展开，动态字段的丢失会导致特性效果在子节点中消失
3. **无法序列化**：JSON 化状态时动态字段不会出现
4. **调试困难**：IDE 和类型检查工具看不到这些字段

### 实际影响

以下特性在搜索深度 > 1 时效果**已经静默丢失**：
- 圣火骑士（`_holy_knight_power`）
- 涅槃（`_nirvana_used`）
- 不朽（`_immortal_used`）
- 化茧（`_cocooned`）
- 铃兰晚钟（`_lillybell_used`）
- 斗技（`_doji_power_bonus`）
- 所有 `_swift_*`、`_crackle_first`、`_takeoff_speed` 等

### 解决方法

**应该做的**：把所有有意义的运行时状态加到 `PetInstance` 的正式字段里，并同步到 `copy()`：

```python
@dataclass
class PetInstance:
    # ... 现有字段 ...
    # 特性运行时状态
    trait_flags: Dict[str, bool] = field(default_factory=dict)
    # 例如: {'nirvana_used': True, 'holy_knight': True, ...}
```

或者直接加具名字段：

```python
    nirvana_used: bool = False
    cocooned: bool = False
    holy_knight_power: bool = False
    first_attacker: bool = False
    doji_power_bonus: int = 0
    lifesteal_bonus: int = 0
```

**优先级**：影响搜索正确性的字段应优先修复（特别是一次性触发类：涅槃、化茧、不朽）。

### 2026-04-10 当前处理状态

已先做一层兼容式收口：

- `PetInstance` 新增 `runtime_flags`
- 旧的 `pet._xxx` 读写会自动转存到 `runtime_flags`
- `PetInstance.copy()` 现在会深拷贝 `runtime_flags`
- `trait_processor` / `extended_battle_engine` 中高风险路径已开始改用
  `get_runtime_flag()/set_runtime_flag()`
- 已继续清理一批高频访问：`_overload_burst`、`_lifesteal_bonus`、
  `_current_skill_name`、`_cocooned`、`_nirvana_used`、
  `_jiahuo_milestone`、`_holy_knight_power`、`_doji_power_bonus`

这一步的目标是先修复“搜索树 copy 时动态字段静默丢失”的框架级问题，避免在尚未重构 `trait_processor` 前继续扩大错误面。

仍未完成的部分：

- 还没有把所有 `_xxx` 状态彻底改成显式具名字段
- `trait_processor` / `extended_battle_engine` 还在沿用旧的 `pet._xxx` 写法
- 后续仍建议把高价值状态逐步迁移到正式字段或统一的类型化容器

---

## 三、技能/特性的"近似实现"未被标注（静默错误）

### 问题描述

实现过程中许多特性被"近似实现"（如先知、预警、哨兵），在 `trait_processor.py` 里用注释说明，但**引擎调用侧没有任何警告**。使用者无法知道某个特性是精确实现还是近似实现。

### 根因

赶进度时倾向于"先有效果再说"，没有同步建立"实现质量标记"机制。

### 解决方法

在 `TRAIT_TRIGGERS` 或单独的字典中标记实现质量：

```python
TRAIT_QUALITY = {
    "先知": "approximate",    # 条件判断近似
    "预警": "approximate",
    "哨兵": "approximate",
    "不朽": "approximate",    # 无3回合延迟
    "陨落": "approximate",    # 触发次数减少的近似
    "吟游之弦": "stub",       # 注册但无效果
    "双向光速": "stub",
    "威吓": "exact",
    # ...
}
```

---

## 四、`_parse_desc_to_effects` 过度膨胀

### 问题描述

`data_loader.py` 中的 `_parse_desc_to_effects` 函数用正则逐条解析中文技能描述，膨胀到约 400 行，包含 31 处 `re.search` 调用，40+ 个 `if/elif` 分支。

### 为什么浪费时间

- 每次新增技能效果类型，都要在这个函数里加新的正则分支
- 调试一个新效果时要在 400 行里找对应分支
- 相似模式（"自己回复N能量"、"敌方失去N能量"等）被重复编写而不是提取成通用函数

### 解决方法

**下次应该做的**：用数据驱动替代代码分支：

```python
PATTERN_TABLE = [
    # (正则, 效果类型, target, value_group, 额外参数)
    (r'自己回复(\d+)能量',  EffectType.ENERGY_RESTORE, 'self',     1, {}),
    (r'敌方失去(\d+)能量',  EffectType.ENERGY_RESTORE, 'opponent', 1, {'drain': True}),
    (r'自己获得物攻\+(\d+)%', EffectType.STAT_BUFF,    'self',     1, {'stat': '物攻'}),
    # ...
]
```

把 400 行的 if/elif 链压缩成一个遍历 `PATTERN_TABLE` 的循环。

---

## 五、`trait_processor._apply()` 的 140 个 elif 分支

### 问题描述

`_apply()` 方法用 140 个 `elif trait_name == "xxx" and context == "yyy"` 实现所有特性，是一个 1600+ 行的超大方法。

### 问题

1. 找一个特性的实现需要 Ctrl+F 搜索
2. 同一个特性有多个触发时机时（如全神贯注在 enter 和 skill_use 各一段），代码分散不易看到全貌
3. 新增特性只能追加到末尾，导致相关逻辑分散

### 解决方法

**重构方向**：按特性名分组，每个特性一个方法或一个 handler 类：

```python
class TraitHandlerRegistry:
    handlers: Dict[str, Dict[str, Callable]] = {}
    
    def register(self, name, context):
        def decorator(fn):
            self.handlers.setdefault(name, {})[context] = fn
            return fn
        return decorator

registry = TraitHandlerRegistry()

@registry.register("威吓", "enter")
def handle_威吓_enter(pet, target, is_player, state, value, skill):
    target.stat_modifiers.physical_attack -= 1
```

---

## 六、多轮对话中的重复分析

### 问题描述

在"实现特性"这个任务里，分了三轮对话（第一轮79种→第二轮116种→第三轮170种），每轮都先运行脚本统计"哪些未实现"，再读数据文件，再决定分类。实际上第一轮就可以一次性完成全部分析和分类，分批实现而不需要重新分析。

### 浪费的模式

每轮对话开始时"重新发现"上一轮已知的事实：
- 重新统计未实现特性数量
- 重新读取 `pets.json` 拉取特性列表
- 重新读取 `trait_processor.py` 确认已注册列表

### 解决方法

1. **在第一轮彻底分类**，将结果写入 `docs/unimplementable_traits.md`（已做，但晚了两轮）
2. **每次完成一批任务后立即更新 docs**，让下一个对话从 docs 读取已知状态而非重新运行脚本
3. **利用 memory 记录关键统计数字**（如"特性总数155，已实现X，剩余Y"）

---

## 七、修改 models.py 时漏同步 copy()

### 问题描述

在给 `TeamState` 添加新字段（`earth_skill_count`、`next_pet_gifts` 等）时，需要同步到 `copy()` 方法。这个同步步骤容易被遗漏，导致搜索树状态复制时字段丢失。

`next_pet_gifts` 的自动检测脚本（用正则匹配 `(\w+)=self\.`）将 `next_pet_gifts=set(self.next_pet_gifts)` 误判为"未同步"，实际上已同步。说明**检测脚本本身也不够可靠**。

### 解决方法

在 `copy()` 末尾加一个运行时断言（开发阶段启用）：

```python
def copy(self) -> 'TeamState':
    result = TeamState(...)
    # 开发期断言：确保 copy 不遗漏字段
    import dataclasses
    for f in dataclasses.fields(self):
        assert hasattr(result, f.name), f"copy() missing field: {f.name}"
    return result
```

---

## 八、技能描述解析的"误匹配"问题

### 曾经发生的具体 bug

1. **腐化**：`STAT_PATTERNS` 匹配到"敌方获得双攻-30%"产生额外效果，导致状态叠加
2. **逆向演化**：`'给敌方赋予'` 的关键词没匹配到"赋予一层萌化"的变体描述
3. **焚烧烙印**：`STATUS_PATTERNS` 把描述里的"5层灼烧"误匹配为施加灼烧效果
4. **赤子之心**：`能耗永久-3` 同时命中通用规则和全技能规则，效果叠加两次

### 根因

**正则匹配缺乏优先级和互斥控制**：多个模式可能同时命中同一段文字，没有"一旦匹配就跳过其他"的机制。

### 解决方法

解析时维护"已消费文本区间"，命中一个模式后标记相应文字段，后续模式跳过已消费区间。或者使用更结构化的解析器（PEG/递归下降）替代平铺 regex。

---

## 九、"暂不实现"变成永久搁置

### 问题描述

最初文档（`unimplementable_mechanics.md`）中很多标注"暂不实现"的技能（如隐藏条款、过载回路）实际上是可以实现的，只是当时没有花时间分析。

用户后来问"为什么隐藏条款无法实现"，证明这个分类是错误的。最终隐藏条款被正确实现（交换双方技能列表）。

### 浪费

错误分类导致可行的功能被遗漏；用户需要主动质疑才能修正。

### 解决方法

初始分类时要求对每个"暂不实现"给出**具体的技术阻碍**，而不是"描述复杂"。凡是没有明确技术阻碍的，视为"未分析完毕"而非"不可实现"。

---

## 十、应该建立的工作流（给下一阶段参考）

### 新功能开发前

1. 先读 `docs/` 里的状态文档，确认当前基线
2. 用 `Grep` 定位相关代码，不全文读取大文件
3. 对影响 `BattleState` 的改动，明确列出需要同步 `copy()` 的字段

### 实现阶段

1. 每实现一批功能，立即用 `python -c` 运行验证脚本（语法检查 + 统计数量）
2. "近似实现"要在代码注释里标 `# APPROXIMATE`，并记录偏差
3. 动态字段（`_xxx`）一旦超过 3 个，就计划迁移到正式字段

### 完成后

1. 更新对应的 `docs/` 文件（已实现数量、新增的限制）
2. 如果修改了 `models.py`，运行 copy 完整性检查
3. 在 `memory/` 中更新项目状态数字（避免下轮对话重新统计）

---

## 技术债优先级总览

| 问题 | 影响 | 修复工作量 | 优先级 |
|------|------|------|------|
| ~~前端不传递 specialAbility 选择给引擎~~ | ~~引擎推荐不可用的首领化/愿力冲击~~ | 小 | **已修复 (2026-04-12)** |
| ~~`/api/analyze` 不返回引擎处理后的 state~~ | ~~特性改耗等效果不同步到前端~~ | 小 | **已修复 (2026-04-12)** |
| ~~前端 JS 回合执行与 Python 引擎双轨并存~~ | ~~特性效果不触发、状态不一致~~ | ~~大（统一执行层）~~ | **已缓解 (2026-04-13)** |
| 动态字段不被 `copy()` 复制 | 搜索树状态静默错误 | 中（逐一迁移到正式字段） | **高** |
| `_apply()` 140 个 elif | 维护困难 | 大（重构为 handler 注册表） | 中 |
| 近似实现无标记 | 调试时误以为精确实现 | 小（加 `TRAIT_QUALITY` 字典） | 中 |
| `_parse_desc_to_effects` 过长 | 新增技能效果困难 | 大（重构为数据驱动） | 中 |
| regex 误匹配无互斥 | 描述解析偶发双重效果 | 中（加已消费区间追踪） | 中 |
| copy() 字段漏同步 | 状态复制不完整 | 小（加 dataclass 断言） | **高** |

---

## 十一、前端↔引擎状态同步问题（2026-04-12 专项记录）

### 问题描述

此前前端（`index.html` JS）和引擎（Python `engine_core/`）存在**双轨执行**，现状已调整为“引擎权威状态 + 兼容壳保留”：

1. **引擎分析**（`/api/analyze`）：Python 引擎完整处理特性、改耗、槽位效果后搜索最优行动，并返回完整 `state` / 合法行动 / `action_panels`
2. **引擎回合推进**（`/api/resolve`）：网页端提交双方动作，由 Python 引擎直接推进一回合并返回下一状态
3. **前端兼容壳**：旧 `execAction` / `execSwap` / `resolveOrder` 等函数仍在文件中，但默认会被 `_legacyLocalBattleBlocked()` 直接短路

因此，原先“双轨执行导致状态漂移”的主风险已显著下降；当前更现实的问题是展示层残余读取点是否仍绕开引擎态。

### 已修复的同步断裂点

#### 1. 首领化/愿力冲击选择不同步

- **根因**：`buildApiPayloadFromB()` 只传递 `player_team / opponent_team`，不传递 `B.teamState`（含 `leaderEvolutionUses / willpowerStrikeUses`）。引擎端 `create_battle_state()` 总是用默认值 `leader=1, willpower=2`。
- **表现**：选了愿力冲击（`leaderEvolutionUses=0`），引擎仍推荐首领化。
- **修复**：
  - 前端 `buildApiPayloadFromB()` 增加 `player_team_state / opponent_team_state` 字段
  - API `_parse_team_state()` 解析并传入 `create_battle_state()`
  - `game_analysis_engine.create_battle_state()` 新增 `player_team_state / opponent_team_state` 可选参数
  - 前端 `_buildPetPayload()` 增加 `bloodline` 字段传递给引擎

#### 1b. 首领化/愿力冲击血脉约束不生效

- **根因**：引擎 `_can_use_leader_evolution` 允许 `bloodline in ("unknown", "leader")`，没有做严格血脉限制。`_can_use_willpower_strike` 缺失，不检查血脉。
- **表现**：非首领血脉精灵仍能被推荐首领化；首领血脉精灵仍能被推荐愿力冲击。
- **规则**：
  - 准备阶段二选一锁死（互斥），一局只能 1次首领化 或 2次愿力冲击（全队共享）
  - 首领血脉精灵只能使用首领化，不能使用愿力冲击
  - 非首领血脉精灵只能使用愿力冲击，不能使用首领化
- **修复**：
  - `action_generator.py`：`_can_use_leader_evolution` 改为 `bloodline == "leader"`，新增 `_can_use_willpower_strike` 检查 `bloodline != "leader"`
  - `extended_battle_engine.py`：`_apply_leader_evolution` 和 `_apply_willpower_strike` 增加血脉校验
  - `index.html`：`selectBattleAction`、`openWillpowerPicker`、`execLeaderEvolution`、`execWillpowerStrike` 增加血脉检查
  - `updateSpecialAbilityUI` 根据当前出战精灵血脉禁用/启用对应按钮

#### 2. 引擎分析后状态不回传前端

- **根因**：`/api/analyze` 只返回 `best_action / evaluation / action_scores`，不返回引擎处理特性后的 `state`。引擎在 `prepare_state_for_turn` 中处理了传动、槽位能耗等，但前端看不到。
- **表现**：特性造成的槽位被动减耗、传动后技能位变化等不显示在前端技能栏。
- **修复**：
  - `/api/analyze` 返回新增 `state` 字段（含所有 pet 的 skills 能耗信息）
  - 前端新增 `_syncEngineStateToFrontend()` 函数，从引擎返回的 state 同步 `skill.energy_cost` 和 `team_state` 回 `B.*`
  - 分析结果返回后自动刷新 `updateSpecialAbilityUI()` 和 `renderBSkills()`
  - `/api/resolve` 接管网页端回合推进，执行后直接采用引擎返回的下一状态
  - `ENGINE_AUTHORITY=true` 且 `LEGACY_LOCAL_BATTLE_ENABLED=false` 时，旧本地结算函数默认禁用

### 仍存在的架构性问题

#### 3. 前端展示层仍有少量残余静态读取

- **本质**：主回合推进已走引擎，但 `index.html` 体量较大，仍有少量展示或交互分支可能先读静态技能/本地快照，再被引擎态覆盖。
- **影响**：主要风险已从“规则结算错误”下降为“按钮可见性、描述展示、局部提示文案或瞬时显示与引擎态短暂不一致”。
- **当前措施**：`/api/analyze` 和 `/api/resolve` 都返回完整 `state`、合法行动和 `action_panels`，前端通过 `_applyEngineStateToBattle()` 与 `_syncEngineStateToFrontend()` 持续回写权威状态。
- **后续方向**：继续排查残余静态读取点，能直接读 `B.engineState` / `action_panels` 的地方就不要再回退到旧本地字段。

### 同步检查清单（给未来的修改者）

新增任何前端可见的战斗状态时，务必检查：

1. `buildApiPayloadFromB()` 是否传递了该状态？
2. `_parse_team_state()` / `_build_team()` 是否解析了该字段？
3. `create_battle_state()` 是否使用了该参数？
4. `_format_state()` 是否返回了该字段？
5. `_syncEngineStateToFrontend()` 是否同步了该字段？
6. `/api/resolve` 返回后，前端是否已经从引擎返回状态和 `action_panels` 中消费该字段？
