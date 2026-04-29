# 事件式 API 端点

## 浏览器控制台

`GET /runtime-console`

返回一个极简 Web 控制台，用于：

1. 开始事件式会话
2. 记录敌方技能 / 换宠 / 资源更新
3. 执行战况导入校准
4. 查看推荐、最近事件和最近导入批次
5. 撤销最后一步、撤回导入批次、清空事件信息

这个页面只是一层薄 UI，底层仍然调用下面这些 API 端点。

当前 `api.py` 已新增以下事件式端点：

## 1. 开始会话

`POST /api/battle/start`

请求体示例：

```json
{
  "session_id": "demo-1",
  "my_team": ["火花", "喵喵"],
  "opponent_team": ["喵呜", "水蓝蓝"],
  "search_depth": 2,
  "inference_mode": "hybrid"
}
```

## 2. 追加事件

`POST /api/battle/<session_id>/event`

请求体示例：

```json
{
  "turn": 1,
  "event_type": "PET_SWITCHED",
  "payload": {
    "side": "my",
    "new_pet": "火花"
  }
}
```

## 3. 获取报告

`GET /api/battle/<session_id>/report`

## 4. 获取推荐

`GET /api/battle/<session_id>/recommend?depth=1`

## 5. 获取事件日志

`GET /api/battle/<session_id>/events`

## 6. 撤销最后事件

`POST /api/battle/<session_id>/undo`

## 7. 重放日志

`POST /api/battle/<session_id>/replay`

## 8. 追加修正

`POST /api/battle/<session_id>/correct`

请求体示例：

```json
{
  "turn": 1,
  "correction_type": "pet_hp",
  "payload": {
    "side": "my",
    "pet_name": "火花",
    "hp_percent": 66
  }
}
```

## 9. 导入敌方当前战况

`POST /api/battle/<session_id>/import_state`

这个端点用于在手动记录失误或状态漂移后，直接把**敌方当前血量/能量**校准回真实战况。

注意：

1. 这不是“清空重建会话”
2. 这不会删除之前已记录的技能、速度、伤害等证据
3. 内部会展开为一批 `STATE_CORRECTED` 事件，并带上 `import_batch_id`

请求体示例：

```json
{
  "turn": 7,
  "side": "opponent",
  "active_pet_name": "喵呜",
  "pets": [
    {
      "pet_name": "喵呜",
      "hp_percent": 64,
      "energy": 5
    },
    {
      "pet_name": "水蓝蓝",
      "hp_percent": 78,
      "energy": 3
    }
  ],
  "note": "手动导入敌方当前战况"
}
```

返回体会包含：

- `import_batch_id`
- `applied_events`
- `report`
- `recommendation`

## 10. 清空事件信息

`POST /api/battle/<session_id>/clear_events`

这个端点会清空：

- 当前会话事件日志
- 由事件累积出的观测状态
- 手动修正和导入批次痕迹

它会保留：

- `session_id`
- 开局阵容配置
- 搜索深度和推断模式

请求体示例：

```json
{
  "confirm_text": "CLEAR"
}
```

如果没有提供 `confirm_text=CLEAR`，接口会拒绝执行。

## 11. 撤回指定导入批次

`POST /api/battle/<session_id>/rollback_import/<import_batch_id>`

这个端点只撤回某一次 `import_state` 产生的 correction 批次，不影响普通事件。

适用场景：

1. 战况导入填错了血量或能量
2. 想快速回退某次手动校准
3. 不想用 `undo` 一条条倒回

返回体会包含：

- `removed_events`
- 最新 `report`
- 最新 `recommendation`

## 12. 查看最近导入批次

`GET /api/battle/<session_id>/imports`

返回最近导入批次摘要，适合在 UI 中展示“最近几次战况校准”。

## 13. 查看某个导入批次明细

`GET /api/battle/<session_id>/imports/<import_batch_id>`

返回该导入批次展开后的 correction 事件明细。

## 当前限制

1. 会话暂存在进程内存中，服务重启会丢失
2. 当前错误分类仍较粗，主要返回 `error` 字段
3. 还没有提供 turn snapshot 或 diff 视图
## 2026-04-10 补充

- `start / event / report / undo / replay / correct` 现在都会直接返回 `recommendation`，用于常驻深度分析。
- `import_state` 会把导入快照拆成 correction 批次，适合在暗箱使用中快速校准敌方资源，不会清空已获取证据。
- `rollback_import/<import_batch_id>` 可整批撤回一次导入校准，便于处理导入时的录入错误。
- `clear_events` 是独立危险操作，必须二次确认文本 `CLEAR`，避免误删整局事件。
- `GET /api/battle/<session_id>/recommend` 仍保留，但现在是补拉接口，不再依赖显式“分析按钮”。
- `player_team` 和 `opponent_team` 的精灵条目支持可选字段 `bloodline`，例如 `"bloodline": "leader"`。
- `recommendation` 当前额外暴露：
  - `analysis_depth`：本次推荐使用的搜索深度
  - `inference_mode`：`pessimistic / expected / hybrid`
  - `confidence_breakdown.action_support`：该动作在各候选状态中保持最优的信念权重占比
  - `confidence_breakdown.score_span`：该动作在不同候选状态间的分数波动
  - `confidence_breakdown.dominant_skill_sets / dominant_profiles`：当前主要不确定性来源
  - `alternatives[*].action_support / score_span`：备选动作的稳定性信息
