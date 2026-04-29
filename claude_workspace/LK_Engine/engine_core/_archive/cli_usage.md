# 交互式 CLI 使用说明

入口：

```bash
python cli_interactive.py
```

## 开局

```text
start 火花,喵喵 喵呜,水蓝蓝 hybrid
```

含义：

- 我方队伍：火花、喵喵
- 对手候选队伍：喵呜、水蓝蓝
- 聚合模式：`hybrid`

可选模式：

- `pessimistic`
- `expected`
- `hybrid`

## 常用命令

### 出战切换

```text
switch my 火花
switch opponent 喵呜
```

### 血量与能量

```text
hp my 火花 82
hp opponent 喵呜 64
energy my 火花 7
energy opponent 喵呜 5
```

### 技能观测

```text
skill my 火花 火焰切割
skill opponent 喵呜 防御
```

### 状态与印记

```text
status add opponent 喵呜 灼烧 2
status remove opponent 喵呜 灼烧
mark pet opponent 喵呜 星陨印记 2
mark field my 光合印记 1
```

### 心数

```text
hearts my 3
hearts opponent 2
```

### 敌方战况导入

```text
import opponent 喵呜 64 5
```

含义：

- 把敌方当前出战精灵校准为 `喵呜`
- 把 `喵呜` 当前血量校准为 `64%`
- 把 `喵呜` 当前能量校准为 `5`

这个命令适合在实战中发现记录失误、或者引擎状态与真实战况不符时快速拉齐。

注意：

1. 它不会清空已记录的技能、速度、伤害等证据
2. 它内部会写入一批 correction 事件，未来可以继续扩展为整批撤回/编辑

### 推荐与报告

```text
recommend
recommend 1
report
imports
imports imp_20260410_153000_ab12
events
```

`report` 现在会优先输出：

- 当前回合与事件数
- 双方当前出战
- 当前心数
- 最近一次导入批次
- 当前 active 宠物摘要
- 最近导入批次列表

### 修正与回放

```text
undo
replay
correct hp my 火花 66
correct energy opponent 喵呜 4
correct active opponent 喵呜
rollback-import imp_20260410_153000_ab12
```

`events` 输出中如果某条事件来自导入批次，会带 `batch=...` 标记。

当某次 `import` 导入错了时，可以直接使用：

```text
rollback-import <import_batch_id>
```

来整批撤回本次导入生成的 correction 事件，而不是逐条 `undo`。

### 清空事件信息

第一次输入：

```text
clear-events
```

CLI 会提示二次确认。确认后输入：

```text
clear-events CONFIRM
```

该操作会清空当前对局累计的事件、修正和推断结果，但保留会话配置。

## 当前限制

1. CLI 还没有“回合开始/回合结束”快捷命令
2. 当前 `current_turn` 仍是简化处理，尚未自动推进
3. 复杂 correction 类型还没有全部开放
4. 当前输出更偏调试风格，不是最终用户界面
